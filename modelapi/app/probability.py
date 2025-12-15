import math
import numpy as np


def normal_cdf(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def mixture_cdf(x_norm: float, pi: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> float:
    z = (x_norm - mu) / np.clip(sigma, 1e-6, None)
    return float(np.sum(pi * normal_cdf(z)))


def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))
