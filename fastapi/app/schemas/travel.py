# app/schemas/travel.py
from pydantic import BaseModel


class UserRequest(BaseModel):
    """사용자 요청을 위한 스키마"""
    latitude: float
    longitude: float
    travel_type: str


class RecommendedPlace(BaseModel):
    """API 응답으로 보낼 추천 장소의 스키마"""
    place_name: str
    latitude: float
    longitude: float
    description: str
