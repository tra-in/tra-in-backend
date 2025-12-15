from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from .settings import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DB_URL, pool_pre_ping=True)
    return _engine
