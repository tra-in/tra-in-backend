import math
import numpy as np
import pandas as pd

from .predict import predict_delay_distribution, load_model


def normal_cdf(z: np.ndarray) -> np.ndarray:
    # Φ(z)
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def mixture_cdf(x, pi, mu, sigma):
    # x: scalar in normalized space
    z = (x - mu) / np.clip(sigma, 1e-6, None)
    return float(np.sum(pi * normal_cdf(z)))


def prob_arrive_before_deadline(
    segment: str,
    recent_delays_min: list[float],
    planned_arrival: pd.Timestamp,
    deadline: pd.Timestamp,
    cfg, art, model, device
) -> float:
    slack_min = (deadline - planned_arrival).total_seconds() / 60.0
    if slack_min < 0:
        return 0.0

    pi, mu, sigma = predict_delay_distribution(
        segment, recent_delays_min, cfg, art, model, device)

    # delay threshold를 normalized space로 변환
    x_norm = (slack_min - art.scaler_mean) / max(art.scaler_std, 1e-8)
    p = mixture_cdf(x_norm, pi, mu, sigma)
    return max(0.0, min(1.0, p))


def rank_routes_by_deadline_probability(routes, recent_lookup_fn, deadline, cfg, art, model, device):
    """
    routes: list of dict
      each route dict has:
        - "legs": list of legs
          leg: {"dep_station_code","arr_station_code","arr_planned","segment"}
    recent_lookup_fn(segment, ts)-> recent lookback delays list[float]
    """
    scored = []
    for r in routes:
        # 경로의 마지막 도착(계획)
        last_leg = r["legs"][-1]
        planned_arrival = pd.to_datetime(last_leg["arr_planned"])

        # 경로 전체 지연을 단순 합산 분포로 하는 건 복잡하니,
        # 최소 구현: "리스크 큰 구간들" 확률을 곱/최소로 근사하거나, 마지막 구간 기반 확률을 사용.
        # 여기서는 "각 구간 deadline 이전 도착 확률의 최소값"을 route 확률로 사용(보수적).
        probs = []
        for leg in r["legs"]:
            seg = leg["segment"]
            ts = pd.to_datetime(leg["arr_planned"])
            recent = recent_lookup_fn(seg, ts)
            p = prob_arrive_before_deadline(
                seg, recent, ts, deadline, cfg, art, model, device)
            probs.append(p)

        route_p = float(min(probs)) if probs else 0.0
        scored.append((route_p, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
