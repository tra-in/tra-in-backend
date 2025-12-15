from sqlalchemy import create_engine


def get_engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True)
