from dataclasses import dataclass
import yaml


@dataclass
class Cfg:
    raw: dict


def load_config(path: str) -> Cfg:
    with open(path, "r", encoding="utf-8") as f:
        return Cfg(yaml.safe_load(f))
