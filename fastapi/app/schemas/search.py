from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum


class TravelPreference(str, Enum):
    """여행 선호도"""
    NATURE = "nature"
    CULTURE = "culture"
    FOOD = "food"
    SHOPPING = "shopping"
    ACTIVITY = "activity"
    RELAXATION = "relaxation"


class LocationBasedRequest(BaseModel):
    """위치 기반 하이브리드 검색 요청"""

    # 필수 필드
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="사용자 위도 (WGS84)",
        example=37.5665
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="사용자 경도 (WGS84)",
        example=126.978
    )

    # 선택적 필드
    query: Optional[str] = Field(
        None,
        description="자연어 검색 쿼리",
        example="도시를 떠나 혼자 힐링할 수 있는 여행"
    )

    travel_preference: Optional[TravelPreference] = Field(
        None,
        description="여행 선호도"
    )

    # ✅ 누락된 필드 추가
    content_types: Optional[List[str]] = Field(
        None,
        description="콘텐츠 타입 필터 (생략 시 travel_preference 기반 자동 선택)",
        example=["12", "39"]
    )

    max_distance_km: float = Field(
        10.0,
        gt=0,
        le=100,
        description="최대 검색 반경 (km)"
    )

    n_results: int = Field(
        10,
        ge=1,
        le=50,
        description="반환할 결과 개수"
    )

    # 가중치 필드
    distance_weight: float = Field(
        0.4,
        ge=0,
        le=1,
        description="거리 가중치"
    )

    similarity_weight: float = Field(
        0.4,
        ge=0,
        le=1,
        description="의미 유사도 가중치"
    )

    preference_weight: float = Field(
        0.2,
        ge=0,
        le=1,
        description="선호도 매칭 가중치"
    )

    @field_validator('content_types')
    @classmethod
    def validate_content_types(cls, v):
        """콘텐츠 타입 검증"""
        if v is None:
            return v

        valid_types = ['12', '14', '15', '25', '28', '32', '38', '39']

        for content_type in v:
            if content_type not in valid_types:
                raise ValueError(
                    f"유효하지 않은 콘텐츠 타입: {v}. "
                    f"허용된 타입: {valid_types}"
                )

        return v

    def copy(self, update: Optional[Dict[str, Any]] = None):
        """Pydantic v2 호환 copy 메서드"""
        data = self.model_dump()
        if update:
            data.update(update)
        return LocationBasedRequest(**data)


class HybridSearchResult(BaseModel):
    """하이브리드 검색 결과 항목"""
    id: str
    title: str
    address: Optional[str] = None
    content_type: Optional[str] = None
    content_type_name: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: float
    hybrid_score: float
    distance_score: float
    similarity_score: float
    preference_score: float
    phone: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None


class HybridSearchResponse(BaseModel):
    """하이브리드 검색 응답"""
    search_metadata: Dict[str, Any]
    results: List[HybridSearchResult]
    total_results: int
    search_strategy: Optional[Dict[str, Any]] = None

# 기존 KTO 관련 클래스들 (유지)


class TourismSearchRequest(BaseModel):
    query: str
    n_results: int = 10
    area_code: Optional[str] = None
    content_type: Optional[str] = None
    include_similarity: bool = True


class TourismSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int
    query: str


class StatsResponse(BaseModel):
    total_items: int
    dimension: int
    collections: List[str]
