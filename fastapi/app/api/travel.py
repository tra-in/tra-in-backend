# app/api/travel.py
from fastapi import APIRouter, Depends
from typing import List

from app.schemas.travel import UserRequest, RecommendedPlace
from app.services.recommendation import get_travel_recommendations

# APIRouter 인스턴스 생성
router = APIRouter()


@router.post(
    "/recommend-travel",
    response_model=List[RecommendedPlace],
    tags=["Travel"],
    summary="여행지 추천 API"
)
async def recommend_travel_places(request: UserRequest):
    """
    사용자의 현재 위치(위도, 경도)와 여행 선호도를 기반으로 주변 여행지를 추천합니다.

    - **latitude**: WGS84 위도
    - **longitude**: WGS84 경도
    - **travel_type**: 사용자가 선호하는 여행 스타일 (예: "잔잔한", "활동적인", "카페 투어")
    """
    recommendations = await get_travel_recommendations(request)
    return recommendations
