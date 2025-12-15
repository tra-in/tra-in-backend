import json
import os
from dataclasses import dataclass
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset


@dataclass
class Artifacts:
    segment_to_id: Dict[str, int]
    scaler_mean: float
    scaler_std: float


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def load_raw(engine) -> pd.DataFrame:
    q = """
    SELECT
      service_date,
      train_no,
      dep_station_code,
      arr_station_code,
      dep_planned,
      arr_planned,
      dep_actual,
      arr_actual
    FROM actual_trains
    """
    df = pd.read_sql(q, engine)
    for c in ["dep_planned", "arr_planned", "dep_actual", "arr_actual"]:
        df[c] = pd.to_datetime(df[c])
    df["segment"] = df["dep_station_code"].astype(
        str) + "->" + df["arr_station_code"].astype(str)

    # 타깃: "도착 지연(분)" = arr_actual - arr_planned
    df["arr_delay_min"] = (
        df["arr_actual"] - df["arr_planned"]).dt.total_seconds() / 60.0
    df["arr_delay_min"] = df["arr_delay_min"].clip(lower=0.0)
    return df


def make_bucket_series(df: pd.DataFrame, bucket_minutes: int) -> pd.DataFrame:
    df = df.copy()

    # 버킷 기준 시각: 계획 도착(arr_planned)
    df["ts"] = df["arr_planned"].dt.floor(f"{bucket_minutes}min")

    g = (
        df.groupby(["segment", "ts"])["arr_delay_min"]
          .mean()
          .reset_index()
          .rename(columns={"arr_delay_min": "y"})
          .sort_values(["segment", "ts"])
    )

    # 구간별 결측 버킷은 0으로 채움
    out = []
    for seg, seg_df in g.groupby("segment"):
        seg_df = seg_df.set_index("ts").asfreq(
            f"{bucket_minutes}min").fillna(0.0)
        seg_df["segment"] = seg
        out.append(seg_df.reset_index())
    return pd.concat(out, ignore_index=True)


def build_segment_map(series: pd.DataFrame) -> Dict[str, int]:
    segs = sorted(series["segment"].unique().tolist())
    return {s: i for i, s in enumerate(segs)}


def fit_scaler(series: pd.DataFrame) -> StandardScaler:
    sc = StandardScaler()
    sc.fit(series[["y"]].values.astype(np.float32))
    return sc


def save_artifacts(artifacts_dir: str, segment_to_id: Dict[str, int], scaler: StandardScaler):
    _ensure_dir(artifacts_dir)
    with open(os.path.join(artifacts_dir, "segment_map.json"), "w", encoding="utf-8") as f:
        json.dump(segment_to_id, f, ensure_ascii=False, indent=2)
    with open(os.path.join(artifacts_dir, "scaler.json"), "w", encoding="utf-8") as f:
        json.dump({"mean": float(scaler.mean_[0]), "std": float(
            scaler.scale_[0])}, f, ensure_ascii=False, indent=2)


def load_artifacts(artifacts_dir: str) -> Artifacts:
    with open(os.path.join(artifacts_dir, "segment_map.json"), "r", encoding="utf-8") as f:
        seg_map = json.load(f)
    with open(os.path.join(artifacts_dir, "scaler.json"), "r", encoding="utf-8") as f:
        sc = json.load(f)
    return Artifacts(segment_to_id=seg_map, scaler_mean=float(sc["mean"]), scaler_std=float(sc["std"]))


def _time_features(ts: pd.Series) -> np.ndarray:
    """
    ts: pandas datetime series
    returns: (N, 4) -> [is_twt, is_peak, hour_sin, hour_cos]
    """
    dow = ts.dt.weekday  # Mon=0 ... Sun=6
    is_twt = dow.isin([1, 2, 3]).astype(np.float32).to_numpy()  # Tue/Wed/Thu

    t = ts.dt.time
    # 피크: 07:00~09:30 or 17:00~19:30
    hh = ts.dt.hour.to_numpy()
    mm = ts.dt.minute.to_numpy()
    minutes = hh * 60 + mm
    peak = ((minutes >= 7*60) & (minutes <= 9*60 + 30)
            ) | ((minutes >= 17*60) & (minutes <= 19*60 + 30))
    is_peak = peak.astype(np.float32)

    # hour_sin/cos (하루 주기)
    frac_day = minutes / (24.0 * 60.0)
    hour_sin = np.sin(2 * np.pi * frac_day).astype(np.float32)
    hour_cos = np.cos(2 * np.pi * frac_day).astype(np.float32)

    return np.stack([is_twt, is_peak, hour_sin, hour_cos], axis=1)


def make_windows_for_all_segments(
    series: pd.DataFrame,
    segment_to_id: Dict[str, int],
    scaler: StandardScaler,
    lookback_steps: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """
    X: (N, lookback, F)  where F=5 -> [delay_norm, is_twt, is_peak, hour_sin, hour_cos]
    seg_id: (N,)
    y: (N, 1) (next delay_norm)
    meta: segment, target_ts
    """
    Xs, seg_ids, ys = [], [], []
    meta_rows = []

    for seg, seg_df in series.groupby("segment"):
        ts = pd.to_datetime(seg_df["ts"])
        yvals = seg_df["y"].values.astype(np.float32).reshape(-1, 1)
        yscaled = scaler.transform(yvals).reshape(-1).astype(np.float32)

        tf = _time_features(ts)  # (T,4)
        # feature per step: [delay_norm] + tf
        feats = np.concatenate([yscaled.reshape(-1, 1), tf], axis=1)  # (T,5)

        for i in range(len(feats) - lookback_steps):
            x = feats[i:i+lookback_steps, :]         # (lookback,5)
            y = yscaled[i+lookback_steps]            # next step delay_norm
            Xs.append(x)
            seg_ids.append(segment_to_id[seg])
            ys.append(y)
            meta_rows.append(
                {"segment": seg, "target_ts": ts.iloc[i+lookback_steps]})

    X = np.array(Xs, dtype=np.float32)
    seg_id = np.array(seg_ids, dtype=np.int64)
    y = np.array(ys, dtype=np.float32)[:, None]
    meta = pd.DataFrame(meta_rows)
    return X, seg_id, y, meta


class WindowDataset(Dataset):
    def __init__(self, X: np.ndarray, seg_id: np.ndarray, y: np.ndarray):
        self.X = X
        self.seg_id = seg_id
        self.y = y

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx: int):
        return self.X[idx], self.seg_id[idx], self.y[idx]
