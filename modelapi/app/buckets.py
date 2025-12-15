import pandas as pd
from sqlalchemy import text
from .db import get_engine

# segment_delay_buckets에서 lookback만 가져옴 (빠름)


def fetch_lookback_bucket_delays(
    segment: str,
    target_ts: pd.Timestamp,
    lookback_steps: int,
    bucket_minutes: int,
) -> pd.DataFrame:
    """
    returns rows sorted asc by ts, length=lookback_steps
    """
    engine = get_engine()
    # target_ts 직전 lookback_steps개 버킷
    q = text("""
      SELECT segment, ts, y
      FROM segment_delay_buckets
      WHERE segment = :segment
        AND ts < :target_ts
      ORDER BY ts DESC
      LIMIT :n
    """)
    df = pd.read_sql(q, engine, params={
                     "segment": segment, "target_ts": target_ts, "n": lookback_steps})
    df = df.sort_values("ts").reset_index(drop=True)
    return df
