from fastapi import FastAPI
from sqlalchemy import text
import pandas as pd

from .settings import settings
from .db import get_engine
from .model_store import ModelStore
from .schemas import RecommendRequest
from .ranker import score_route_2legs, score_route_3legs
from .presenter import present_recommendation_v2
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # modelapi/app
SQL_DIR = BASE_DIR / "sql"


def load_sql(filename: str):
    return text((SQL_DIR / filename).read_text(encoding="utf-8"))


app = FastAPI(title="Train Transfer Recommender")

store: ModelStore | None = None


@app.on_event("startup")
def startup():
    global store
    store = ModelStore(settings.LSTM_CONFIG_PATH)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    assert store is not None

    deadline = pd.to_datetime(req.deadline)
    now = pd.to_datetime(req.now) if getattr(
        req, "now", None) else pd.Timestamp.now()
    deadline_plus = deadline + pd.Timedelta(minutes=settings.DEADLINE_PLUS_MIN)

    engine = get_engine()

    # 후보(1회 환승)
    q1 = load_sql("transfer1.sql")
    df1 = pd.read_sql(
        q1,
        engine,
        params={
            "from_name": req.from_name,
            "to_name": req.to_name,
            "now": now,  # ✅ 요청 now 기준
            "deadline_plus": deadline_plus,
            "min_transfer_min": req.min_transfer_min,
            "max_total_hours": settings.MAX_TOTAL_HOURS,
            "limit": req.limit,
        },
    )

    results = []
    for _, row in df1.iterrows():
        results.append(score_route_2legs(store, row, deadline))

    # 후보(2회 환승)
    if req.max_transfers >= 2:
        q2 = load_sql("transfer2.sql")
        df2 = pd.read_sql(
            q2,
            engine,
            params={
                "from_name": req.from_name,
                "to_name": req.to_name,
                "now": now,  # ✅ 요청 now 기준
                "deadline_plus": deadline_plus,
                "min_transfer_min": req.min_transfer_min,
                "max_total_hours": settings.MAX_TOTAL_HOURS,
                "limit": req.limit,
            },
        )
        for _, row in df2.iterrows():
            results.append(score_route_3legs(store, row, deadline))

    # 랭킹
    results.sort(key=lambda x: x["p_on_time"], reverse=True)

    return {
        "from": req.from_name,
        "to": req.to_name,
        "now": str(now),               # ✅ 추가(디버그/재현성)
        "deadline": str(deadline),
        "route_agg": settings.ROUTE_AGG,
        "count": len(results),
        "results": results[: req.topk],
    }


@app.post("/recommend/v2")
def recommend_v2(req: RecommendRequest):
    raw = recommend(req)  # 기존 recommend 로직 재사용

    # ✅ v2 query에 now 포함
    query = {
        "from": req.from_name,
        "to": req.to_name,
        "now": raw.get("now"),         # ✅ raw에 넣어둔 now 그대로 사용
        "deadline": raw.get("deadline"),
        "max_transfers": req.max_transfers,
        "min_transfer_min": req.min_transfer_min,
    }

    return present_recommendation_v2(
        raw,
        query=query,
        topk=req.topk,
    )
