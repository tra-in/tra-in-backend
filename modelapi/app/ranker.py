# 핵심: 후보 route(2 legs/3 legs) → leg별 P → route P → 설명(explain)
import pandas as pd
import numpy as np
import torch

from .settings import settings
from .features import floor_to_bucket, build_model_input
from .buckets import fetch_lookback_bucket_delays
from .probability import mixture_cdf, clamp01

RISKY = {"NAT013271", "NAT040257"}  # 동대구, 전주


def is_risky_segment(seg: str) -> bool:
    dep, arr = seg.split("->", 1)
    return dep in RISKY or arr in RISKY


def prob_leg_on_time(
    store,
    segment: str,
    planned_arrival: pd.Timestamp,
    deadline: pd.Timestamp,
) -> tuple[float, dict]:
    sid = store.segment_id(segment)
    if sid is None:
        # 모델이 모르는 segment면 보수적으로 낮게
        return 0.50, {"reason": "unknown_segment", "segment": segment, "is_risky_segment": is_risky_segment(segment)}

    target_ts = floor_to_bucket(planned_arrival, settings.BUCKET_MINUTES)
    hist = fetch_lookback_bucket_delays(
        segment, target_ts, settings.LOOKBACK_STEPS, settings.BUCKET_MINUTES
    )

    if len(hist) < settings.LOOKBACK_STEPS:
        # history 부족하면 기본값(0) padding
        missing = settings.LOOKBACK_STEPS - len(hist)
        pad_ts = pd.date_range(
            end=target_ts - pd.Timedelta(minutes=settings.BUCKET_MINUTES),
            periods=missing,
            freq=f"{settings.BUCKET_MINUTES}min",
        )
        pad = pd.DataFrame({"segment": segment, "ts": pad_ts, "y": 0.0})
        hist = (
            pd.concat([pad, hist], ignore_index=True)
            .sort_values("ts")
            .reset_index(drop=True)
        )

    # delay_norm window
    mean, std = store.artifacts.mean, store.artifacts.std
    y = hist["y"].astype(np.float32).to_numpy()
    y_norm = ((y - mean) / max(std, 1e-8)).astype(np.float32)

    ts_window = pd.DatetimeIndex(pd.to_datetime(hist["ts"]))

    X = build_model_input(y_norm, ts_window)  # (1, lookback, 5)

    xb = torch.from_numpy(X).to(store.device)
    seg_id = torch.tensor([sid], dtype=torch.long, device=store.device)

    with torch.no_grad():
        pi, mu, sigma = store.model(xb, seg_id)

    pi = pi.cpu().numpy()[0]
    mu = mu.cpu().numpy()[0]
    sigma = sigma.cpu().numpy()[0]

    slack_min = max(0.0, (deadline - planned_arrival).total_seconds() / 60.0)
    x_norm = (slack_min - mean) / max(std, 1e-8)
    p = clamp01(mixture_cdf(float(x_norm), pi, mu, sigma))

    explain = {
        "segment": segment,
        "slack_min": float(slack_min),
        "target_ts": str(target_ts),
        # 모델 explain에도 남겨두되, has_risky는 SQL row 기반으로 계산할 것
        "is_risky_segment": is_risky_segment(segment),
    }
    return float(p), explain


def aggregate_route(probs: list[float]) -> float:
    if settings.ROUTE_AGG == "product":
        out = 1.0
        for p in probs:
            out *= p
        return float(out)
    # default: min
    return float(min(probs)) if probs else 0.0


def _row_bool(row, key: str) -> bool:
    """SQL 결과 row에서 0/1, True/False, None 모두 안전하게 bool로 변환."""
    try:
        v = row[key]
    except Exception:
        return False
    if v is None:
        return False
    # pandas row면 numpy scalar일 수 있음
    try:
        return bool(int(v))
    except Exception:
        return bool(v)


def score_route_2legs(store, row, deadline: pd.Timestamp) -> dict:
    seg1 = f"{row['leg1_dep_code']}->{row['leg1_arr_code']}"
    seg2 = f"{row['leg2_dep_code']}->{row['leg2_arr_code']}"

    p1, e1 = prob_leg_on_time(
        store, seg1, pd.to_datetime(row["leg1_arr_time"]), deadline)
    p2, e2 = prob_leg_on_time(
        store, seg2, pd.to_datetime(row["leg2_arr_time"]), deadline)

    p_route = aggregate_route([p1, p2])

    transfer_slack = (
        pd.to_datetime(row["leg2_dep_time"]) -
        pd.to_datetime(row["leg1_arr_time"])
    ).total_seconds() / 60.0

    # ✅ has_risky는 SQL에서 계산된 컬럼을 우선 사용
    # (없으면 False로 fallback)
    has_risky = _row_bool(row, "is_risky_segment_1") or _row_bool(
        row, "is_risky_segment_2")

    return {
        "transfers": 1,
        "p_on_time": p_route,
        "legs": [
            {
                "train_id": int(row["leg1_train_id"]),
                "train_no": row["leg1_train_no"],
                "dep": row["leg1_dep_code"],
                "arr": row["leg1_arr_code"],
                "dep_time": str(row["leg1_dep_time"]),
                "arr_time": str(row["leg1_arr_time"]),
                "p_leg": p1,
                "explain": e1,
            },
            {
                "train_id": int(row["leg2_train_id"]),
                "train_no": row["leg2_train_no"],
                "dep": row["leg2_dep_code"],
                "arr": row["leg2_arr_code"],
                "dep_time": str(row["leg2_dep_time"]),
                "arr_time": str(row["leg2_arr_time"]),
                "p_leg": p2,
                "explain": e2,
            },
        ],
        "transfer": {"station": row["transfer_station"], "min_transfer": float(transfer_slack)},
        "has_risky": bool(has_risky),
    }


def score_route_3legs(store, row, deadline: pd.Timestamp) -> dict:
    seg1 = f"{row['leg1_dep_code']}->{row['leg1_arr_code']}"
    seg2 = f"{row['leg2_dep_code']}->{row['leg2_arr_code']}"
    seg3 = f"{row['leg3_dep_code']}->{row['leg3_arr_code']}"

    p1, e1 = prob_leg_on_time(
        store, seg1, pd.to_datetime(row["leg1_arr_time"]), deadline)
    p2, e2 = prob_leg_on_time(
        store, seg2, pd.to_datetime(row["leg2_arr_time"]), deadline)
    p3, e3 = prob_leg_on_time(
        store, seg3, pd.to_datetime(row["leg3_arr_time"]), deadline)

    p_route = aggregate_route([p1, p2, p3])

    t1_slack = (
        pd.to_datetime(row["leg2_dep_time"]) -
        pd.to_datetime(row["leg1_arr_time"])
    ).total_seconds() / 60.0
    t2_slack = (
        pd.to_datetime(row["leg3_dep_time"]) -
        pd.to_datetime(row["leg2_arr_time"])
    ).total_seconds() / 60.0

    # ✅ has_risky는 SQL에서 계산된 컬럼을 우선 사용
    has_risky = (
        _row_bool(row, "is_risky_segment_1")
        or _row_bool(row, "is_risky_segment_2")
        or _row_bool(row, "is_risky_segment_3")
    )

    return {
        "transfers": 2,
        "p_on_time": p_route,
        "legs": [
            {
                "train_id": int(row["leg1_train_id"]),
                "train_no": row["leg1_train_no"],
                "dep": row["leg1_dep_code"],
                "arr": row["leg1_arr_code"],
                "dep_time": str(row["leg1_dep_time"]),
                "arr_time": str(row["leg1_arr_time"]),
                "p_leg": p1,
                "explain": e1,
            },
            {
                "train_id": int(row["leg2_train_id"]),
                "train_no": row["leg2_train_no"],
                "dep": row["leg2_dep_code"],
                "arr": row["leg2_arr_code"],
                "dep_time": str(row["leg2_dep_time"]),
                "arr_time": str(row["leg2_arr_time"]),
                "p_leg": p2,
                "explain": e2,
            },
            {
                "train_id": int(row["leg3_train_id"]),
                "train_no": row["leg3_train_no"],
                "dep": row["leg3_dep_code"],
                "arr": row["leg3_arr_code"],
                "dep_time": str(row["leg3_dep_time"]),
                "arr_time": str(row["leg3_arr_time"]),
                "p_leg": p3,
                "explain": e3,
            },
        ],
        "transfer": {
            "stations": [row["transfer1_name"], row["transfer2_name"]],
            "mins": [float(t1_slack), float(t2_slack)],
        },
        "has_risky": bool(has_risky),
    }
