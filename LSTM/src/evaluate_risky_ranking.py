"""
이 스크립트는:

    DB에서 actual_trains를 읽어 segment(구간)별 버킷 시계열 생성

    학습 때 저장된 artifacts/model.pt, segment_map.json, scaler.json 로 모델 로드

    무작위로 여러 시점(ts)을 뽑아서 후보 구간들에 대해

        입력 윈도우(lookback, 5피처) 구성

        P(delay ≤ slack) (deadline 이전 도착확률) 계산

        랭킹

        
        
출력에서 봐야 할 것

    SAFE mean이 RISKY mean보다 높아야 정상

    RISKY avg rank가 후보 수의 절반보다 큰 쪽(예: pool=30이면 평균 rank가 15 이상)에 가까워질수록 “하단 배치”가 잘 되고 있다는 뜻

    RISKY bottom-half rate가 0.5보다 크면(예: 0.65) “대부분 하단”임        
        
"""
import math
import random
from dataclasses import dataclass
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd
import torch

from .config import load_config
from .db import get_engine
from .data import load_raw, make_bucket_series, load_artifacts
from .model import LSTMMDN

RISKY_STATIONS = {"NAT013271", "NAT040257"}  # 동대구, 전주


def normal_cdf(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def mixture_cdf(x_norm: float, pi: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> float:
    z = (x_norm - mu) / np.clip(sigma, 1e-6, None)
    return float(np.sum(pi * normal_cdf(z)))


def time_features(ts: pd.DatetimeIndex) -> np.ndarray:
    """
    ts: DatetimeIndex length T
    returns: (T,4) -> [is_twt, is_peak, hour_sin, hour_cos]
    """
    dow = ts.weekday  # Mon=0 ... Sun=6
    is_twt = np.isin(dow, [1, 2, 3]).astype(np.float32)

    minutes = ts.hour.to_numpy() * 60 + ts.minute.to_numpy()
    peak = ((minutes >= 7*60) & (minutes <= 9*60+30)
            ) | ((minutes >= 17*60) & (minutes <= 19*60+30))
    is_peak = peak.astype(np.float32)

    frac_day = minutes / (24.0 * 60.0)
    hour_sin = np.sin(2 * np.pi * frac_day).astype(np.float32)
    hour_cos = np.cos(2 * np.pi * frac_day).astype(np.float32)

    return np.stack([is_twt, is_peak, hour_sin, hour_cos], axis=1)


def parse_segment(segment: str) -> Tuple[str, str]:
    # "DEP->ARR"
    dep, arr = segment.split("->", 1)
    return dep, arr


def is_risky_segment(segment: str) -> bool:
    dep, arr = parse_segment(segment)
    return (dep in RISKY_STATIONS) or (arr in RISKY_STATIONS)


@dataclass
class SegmentSeries:
    ts: np.ndarray      # datetime64[ns]
    y: np.ndarray       # raw delay minutes (float)
    y_norm: np.ndarray  # normalized


def build_series_index(series_df: pd.DataFrame, mean: float, std: float) -> Dict[str, SegmentSeries]:
    idx: Dict[str, SegmentSeries] = {}
    for seg, g in series_df.groupby("segment"):
        g = g.sort_values("ts")
        ts = g["ts"].values.astype("datetime64[ns]")
        y = g["y"].values.astype(np.float32)
        y_norm = ((y - mean) / max(std, 1e-8)).astype(np.float32)
        idx[seg] = SegmentSeries(ts=ts, y=y, y_norm=y_norm)
    return idx


def recent_window(seg_idx: Dict[str, SegmentSeries], segment: str, target_ts: np.datetime64, lookback: int) -> Tuple[np.ndarray, pd.DatetimeIndex]:
    """
    returns:
      delay_norm_window: (lookback,)
      ts_window: DatetimeIndex length lookback (aligned to delay steps)
    """
    s = seg_idx[segment]
    # find target position == target_ts
    pos = np.searchsorted(s.ts, target_ts)
    # target_ts should exist as a bucket; allow nearest previous
    if pos == len(s.ts) or s.ts[pos] != target_ts:
        pos = max(0, pos - 1)

    start = pos - lookback
    if start < 0:
        raise ValueError("not enough history")
    # up to pos-1 inclusive, length=lookback
    window_norm = s.y_norm[start:pos].copy()
    ts_window = pd.to_datetime(s.ts[start:pos])
    return window_norm, ts_window


def build_model_input(window_norm: np.ndarray, ts_window: pd.DatetimeIndex) -> np.ndarray:
    """
    window_norm: (lookback,)
    ts_window: length lookback
    returns X: (1, lookback, 5)
    """
    tf = time_features(ts_window)  # (lookback,4)
    x = np.concatenate([window_norm.reshape(-1, 1), tf],
                       axis=1).astype(np.float32)  # (lookback,5)
    return x[None, :, :]


def load_model_and_data(cfg_path="config.yaml"):
    cfg = load_config(cfg_path).raw
    device = torch.device(cfg["train"]["device"])

    engine = get_engine(cfg["db"]["url"])
    raw = load_raw(engine)
    series_df = make_bucket_series(raw, cfg["data"]["bucket_minutes"])

    art = load_artifacts(cfg["paths"]["artifacts_dir"])
    seg_idx = build_series_index(series_df, art.scaler_mean, art.scaler_std)

    model = LSTMMDN(
        num_segments=len(art.segment_to_id),
        emb_dim=cfg["train"]["emb_dim"],
        hidden_size=cfg["train"]["hidden_size"],
        num_layers=cfg["train"]["num_layers"],
        K=cfg["train"]["mdn_components"],
        num_features=5,
    ).to(device)
    model.load_state_dict(torch.load(
        cfg["paths"]["model_path"], map_location=device))
    model.eval()

    return cfg, art, seg_idx, model, device


def prob_delay_leq_slack(
    cfg, art, seg_idx, model, device,
    segment: str, target_ts: np.datetime64, slack_min: float
) -> float:
    lookback = cfg["data"]["lookback_steps"]
    w_norm, ts_window = recent_window(seg_idx, segment, target_ts, lookback)
    X = build_model_input(w_norm, ts_window)
    xb = torch.from_numpy(X).to(device)
    sid = torch.tensor([art.segment_to_id[segment]],
                       dtype=torch.long, device=device)

    with torch.no_grad():
        pi, mu, sigma = model(xb, sid)

    pi = pi.cpu().numpy()[0]
    mu = mu.cpu().numpy()[0]
    sigma = sigma.cpu().numpy()[0]

    x_norm = (slack_min - art.scaler_mean) / max(art.scaler_std, 1e-8)
    p = mixture_cdf(float(x_norm), pi, mu, sigma)
    return float(max(0.0, min(1.0, p)))


def main():
    cfg, art, seg_idx, model, device = load_model_and_data()

    # 테스트 설정
    # deadline 여유(분): planned_arrival + 15분까지 도착할 확률
    slack_min = 15.0
    num_trials = 200              # 여러 시점에서 반복
    pool_size = 30                # 각 시점마다 후보 구간 몇 개를 비교할지
    random.seed(42)

    # 사용할 세그먼트 목록 (모델이 아는 segment만)
    segments = [s for s in seg_idx.keys() if s in art.segment_to_id]
    risky_segments = [s for s in segments if is_risky_segment(s)]
    safe_segments = [s for s in segments if not is_risky_segment(s)]

    if len(risky_segments) == 0 or len(safe_segments) == 0:
        raise RuntimeError(
            "risky/safe segments split failed. Check segment format or station codes.")

    # 각 segment의 가능한 ts(버킷) 중 충분히 history 있는 ts만 후보로
    lookback = cfg["data"]["lookback_steps"]
    seg_valid_ts: Dict[str, np.ndarray] = {}
    for s in segments:
        ts = seg_idx[s].ts
        if len(ts) > lookback + 10:
            seg_valid_ts[s] = ts[lookback+1:]  # history 확보된 시점만

    # 통계
    risky_probs, safe_probs = [], []
    risky_avg_rank = []
    risky_bottom_half_rate = []

    # “같은 시점” 기준 비교: 랜덤 ts를 하나 뽑고, 그 ts가 있는 segment들만 대상으로 pool 구성
    # (엄밀히는 segment마다 ts 범위가 다르므로, 교집합을 완벽히 맞추기보단 대략 맞춤)
    all_ts = np.unique(np.concatenate([seg_valid_ts[s] for s in random.sample(
        list(seg_valid_ts.keys()), min(50, len(seg_valid_ts)))]))
    all_ts = np.sort(all_ts)

    for _ in range(num_trials):
        target_ts = random.choice(all_ts)

        # 후보 세그먼트 풀 구성: risky와 safe를 섞어서 뽑되, 해당 ts에서 history가 충분한 것만
        def pick_candidates(cands, k):
            out = []
            tries = 0
            while len(out) < k and tries < k * 20:
                s = random.choice(cands)
                if s in seg_valid_ts and target_ts in seg_valid_ts[s]:
                    out.append(s)
                tries += 1
            return out

        half = pool_size // 2
        cand_risky = pick_candidates(risky_segments, half)
        cand_safe = pick_candidates(safe_segments, pool_size - len(cand_risky))
        cand = cand_risky + cand_safe

        if len(cand) < max(10, pool_size // 2):
            # 해당 ts에서 비교 가능한 세그먼트가 너무 적으면 스킵
            continue

        scored = []
        for s in cand:
            try:
                p = prob_delay_leq_slack(
                    cfg, art, seg_idx, model, device, s, target_ts, slack_min)
            except ValueError:
                continue
            scored.append((p, s))

        if len(scored) < 10:
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        ranks = {s: i+1 for i, (_, s) in enumerate(scored)}  # 1=best

        # 확률 통계
        for p, s in scored:
            if is_risky_segment(s):
                risky_probs.append(p)
            else:
                safe_probs.append(p)

        # risky가 평균적으로 얼마나 아래에 있나?
        risky_in_pool = [s for _, s in scored if is_risky_segment(s)]
        if risky_in_pool:
            avg_rank = float(np.mean([ranks[s] for s in risky_in_pool]))
            risky_avg_rank.append(avg_rank)

            bottom_half = sum(1 for s in risky_in_pool if ranks[s] > len(
                scored) / 2) / len(risky_in_pool)
            risky_bottom_half_rate.append(bottom_half)

    # 결과 출력
    def summarize(name, arr):
        arr = np.array(arr, dtype=np.float32)
        if len(arr) == 0:
            print(f"{name}: no samples")
            return
        print(f"{name}: n={len(arr)} mean={arr.mean():.4f} p50={np.median(arr):.4f} p10={np.quantile(arr, 0.1):.4f} p90={np.quantile(arr, 0.9):.4f}")

    print("\n=== Probability P(delay <= slack) summary ===")
    summarize("SAFE  ", safe_probs)
    summarize("RISKY ", risky_probs)

    print("\n=== Ranking behavior (lower is better rank number) ===")
    summarize("RISKY avg rank", risky_avg_rank)
    summarize("RISKY bottom-half rate", risky_bottom_half_rate)

    # 간단 판정(휴리스틱)
    if len(safe_probs) and len(risky_probs):
        safe_mean = float(np.mean(safe_probs))
        risky_mean = float(np.mean(risky_probs))
        print("\n=== Simple check ===")
        print(
            f"mean prob SAFE={safe_mean:.4f} vs RISKY={risky_mean:.4f} (slack={slack_min}m)")
        if risky_mean < safe_mean:
            print(
                "✅ OK: risky segments tend to have LOWER on-time probability (rank should push them down).")
        else:
            print("⚠️ Unexpected: risky segments not lower than safe on average. Check data generation / feature alignment.")


if __name__ == "__main__":
    main()
