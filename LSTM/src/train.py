import os
import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from .config import load_config
from .db import get_engine
from .data import (
    load_raw, make_bucket_series, build_segment_map,
    fit_scaler, save_artifacts, make_windows_for_all_segments, WindowDataset
)
from .model import LSTMMDN, mdn_nll


def set_seed(seed: int):
    np.random.seed(seed)
    torch.manual_seed(seed)


def main():
    cfg = load_config("config.yaml").raw
    set_seed(cfg["train"]["seed"])
    device = torch.device(cfg["train"]["device"])

    engine = get_engine(cfg["db"]["url"])
    raw = load_raw(engine)
    series = make_bucket_series(raw, cfg["data"]["bucket_minutes"])

    seg_map = build_segment_map(series)
    scaler = fit_scaler(series)

    X, seg_id, y, meta = make_windows_for_all_segments(
        series, seg_map, scaler, cfg["data"]["lookback_steps"]
    )

    # ---- 시간 기준 split (전체 target_ts에서 cutoff) ----
    meta["target_ts"] = np.array(meta["target_ts"], dtype="datetime64[ns]")
    cutoff = meta["target_ts"].quantile(cfg["train"]["train_ratio"])
    tr_mask = meta["target_ts"] < cutoff
    va_mask = ~tr_mask

    train_ds = WindowDataset(
        X[tr_mask.values], seg_id[tr_mask.values], y[tr_mask.values])
    val_ds = WindowDataset(
        X[va_mask.values], seg_id[va_mask.values], y[va_mask.values])

    train_loader = DataLoader(
        train_ds, batch_size=cfg["train"]["batch_size"], shuffle=True)
    val_loader = DataLoader(
        val_ds, batch_size=cfg["train"]["batch_size"], shuffle=False)

    num_features = X.shape[-1]  # 5
    model = LSTMMDN(
        num_segments=len(seg_map),
        emb_dim=cfg["train"]["emb_dim"],
        hidden_size=cfg["train"]["hidden_size"],
        num_layers=cfg["train"]["num_layers"],
        K=cfg["train"]["mdn_components"],
        num_features=num_features
    ).to(device)

    opt = torch.optim.Adam(model.parameters(), lr=cfg["train"]["lr"])

    best_val = float("inf")
    os.makedirs(cfg["paths"]["artifacts_dir"], exist_ok=True)

    for epoch in range(1, cfg["train"]["epochs"] + 1):
        model.train()
        tr_loss = 0.0
        for xb, sid, yb in tqdm(train_loader, desc=f"epoch {epoch} train"):
            xb = xb.to(device)
            sid = sid.to(device)
            yb = yb.to(device)

            opt.zero_grad()
            pi, mu, sigma = model(xb, sid)
            loss = mdn_nll(yb, pi, mu, sigma)
            loss.backward()
            opt.step()
            tr_loss += loss.item() * xb.size(0)
        tr_loss /= len(train_ds)

        model.eval()
        va_loss = 0.0
        with torch.no_grad():
            for xb, sid, yb in tqdm(val_loader, desc=f"epoch {epoch} val"):
                xb = xb.to(device)
                sid = sid.to(device)
                yb = yb.to(device)
                pi, mu, sigma = model(xb, sid)
                loss = mdn_nll(yb, pi, mu, sigma)
                va_loss += loss.item() * xb.size(0)
        va_loss /= len(val_ds)

        print(f"[epoch {epoch}] train_nll={tr_loss:.4f} val_nll={va_loss:.4f}")

        print("X shape:", X.shape)  # (N, lookback, F)
        print("train samples:", len(train_ds), "val samples:", len(val_ds))
        print("steps/epoch:", (len(train_ds) +
              cfg["train"]["batch_size"] - 1) // cfg["train"]["batch_size"])

        if va_loss < best_val:
            best_val = va_loss
            torch.save(model.state_dict(), cfg["paths"]["model_path"])
            save_artifacts(cfg["paths"]["artifacts_dir"], seg_map, scaler)
            print(f"  saved best model -> {cfg['paths']['model_path']}")


if __name__ == "__main__":
    main()
