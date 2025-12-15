import sys
from pathlib import Path
from dataclasses import dataclass

import torch


def _ensure_lstm_on_path():
    # TRA-IN-BACKEND/modelapi/app/model_store.py 기준
    ROOT = Path(__file__).resolve().parents[2]  # TRA-IN-BACKEND
    LSTM_DIR = ROOT / "LSTM"
    sys.path.insert(0, str(LSTM_DIR))
    return LSTM_DIR


@dataclass
class Artifacts:
    segment_to_id: dict
    mean: float
    std: float


class ModelStore:
    def __init__(self, lstm_config_path: str):
        _ensure_lstm_on_path()

        # ✅ import는 init 내부에서 (reload/spawn 꼬임 방지)
        from src.config import load_config
        from src.data import load_artifacts
        from src.model import LSTMMDN

        self.cfg = load_config(lstm_config_path).raw
        self.device = torch.device(self.cfg["train"]["device"])

        # ✅ config.yaml 기준으로 상대경로 보정
        cfg_path = Path(lstm_config_path).resolve()
        cfg_dir = cfg_path.parent  # .../TRA-IN-BACKEND/LSTM

        art_dir = Path(self.cfg["paths"]["artifacts_dir"])
        model_path = Path(self.cfg["paths"]["model_path"])

        if not art_dir.is_absolute():
            self.cfg["paths"]["artifacts_dir"] = str(
                (cfg_dir / art_dir).resolve())

        if not model_path.is_absolute():
            self.cfg["paths"]["model_path"] = str(
                (cfg_dir / model_path).resolve())

        # ✅ 여기부터도 전부 init 안에 있어야 함!
        art = load_artifacts(self.cfg["paths"]["artifacts_dir"])
        self.artifacts = Artifacts(
            segment_to_id=art.segment_to_id,
            mean=float(art.scaler_mean),
            std=float(art.scaler_std),
        )

        self.model = LSTMMDN(
            num_segments=len(self.artifacts.segment_to_id),
            emb_dim=self.cfg["train"]["emb_dim"],
            hidden_size=self.cfg["train"]["hidden_size"],
            num_layers=self.cfg["train"]["num_layers"],
            K=self.cfg["train"]["mdn_components"],
            num_features=5,
        ).to(self.device)

        self.model.load_state_dict(
            torch.load(self.cfg["paths"]["model_path"],
                       map_location=self.device)
        )
        self.model.eval()

    def segment_id(self, segment: str) -> int | None:
        return self.artifacts.segment_to_id.get(segment)
