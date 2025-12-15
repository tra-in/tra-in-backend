import numpy as np
import torch

from .config import load_config
from .data import load_artifacts
from .model import LSTMMDN


def load_model(cfg_path="config.yaml"):
    cfg = load_config(cfg_path).raw
    device = torch.device(cfg["train"]["device"])
    art = load_artifacts(cfg["paths"]["artifacts_dir"])

    model = LSTMMDN(
        num_segments=len(art.segment_to_id),
        emb_dim=cfg["train"]["emb_dim"],
        hidden_size=cfg["train"]["hidden_size"],
        num_layers=cfg["train"]["num_layers"],
        K=cfg["train"]["mdn_components"],
    ).to(device)
    model.load_state_dict(torch.load(
        cfg["paths"]["model_path"], map_location=device))
    model.eval()
    return cfg, art, model, device


def normalize(x: np.ndarray, mean: float, std: float) -> np.ndarray:
    return (x - mean) / max(std, 1e-8)


def predict_delay_distribution(segment: str, recent_delays_min: list[float], cfg, art, model, device):
    if segment not in art.segment_to_id:
        raise ValueError(f"unknown segment: {segment}")

    lookback = cfg["data"]["lookback_steps"]
    if len(recent_delays_min) != lookback:
        raise ValueError(
            f"need recent_delays_min length == lookback_steps({lookback})")

    x = np.array(recent_delays_min, dtype=np.float32).reshape(1, lookback, 1)
    x = normalize(x, art.scaler_mean, art.scaler_std)
    seg_id = np.array([art.segment_to_id[segment]], dtype=np.int64)

    xb = torch.from_numpy(x).to(device)
    sid = torch.from_numpy(seg_id).to(device)

    with torch.no_grad():
        pi, mu, sigma = model(xb, sid)  # normalized space
    return pi.cpu().numpy()[0], mu.cpu().numpy()[0], sigma.cpu().numpy()[0]
