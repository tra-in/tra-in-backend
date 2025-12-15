import numpy as np
import pandas as pd


def time_features(ts: pd.DatetimeIndex) -> np.ndarray:
    # [is_twt, is_peak, hour_sin, hour_cos]
    dow = ts.weekday
    is_twt = np.isin(dow, [1, 2, 3]).astype(np.float32)

    minutes = ts.hour.to_numpy() * 60 + ts.minute.to_numpy()
    peak = ((minutes >= 7*60) & (minutes <= 9*60+30)
            ) | ((minutes >= 17*60) & (minutes <= 19*60+30))
    is_peak = peak.astype(np.float32)

    frac_day = minutes / (24.0 * 60.0)
    hour_sin = np.sin(2 * np.pi * frac_day).astype(np.float32)
    hour_cos = np.cos(2 * np.pi * frac_day).astype(np.float32)

    return np.stack([is_twt, is_peak, hour_sin, hour_cos], axis=1)


def build_model_input(delay_norm_window: np.ndarray, ts_window: pd.DatetimeIndex) -> np.ndarray:
    # (lookback,5) = [delay_norm] + time_features(4)
    tf = time_features(ts_window)  # (lookback,4)
    x = np.concatenate([delay_norm_window.reshape(-1, 1),
                       tf], axis=1).astype(np.float32)
    return x[None, :, :]  # (1, lookback, 5)


def floor_to_bucket(dt: pd.Timestamp, bucket_minutes: int) -> pd.Timestamp:
    return dt.floor(f"{bucket_minutes}min")
