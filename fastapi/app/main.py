# app/main.py
from fastapi import FastAPI
from app.api import travel

# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="Travel Recommender API",
    description="사용자 위치와 선호도 기반 여행지 추천 API",
    version="1.0.0"
)

# travel.py에서 정의한 라우터를 메인 앱에 포함
app.include_router(travel.router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "여행 추천 API에 오신 것을 환영합니다. /docs 로 이동하여 API 문서를 확인하세요."}
