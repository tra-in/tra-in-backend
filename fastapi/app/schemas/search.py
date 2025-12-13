from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TourismSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리", example="서울 맛집")
    n_results: int = Field(10, ge=1, le=50, description="결과 개수")
    area_code: Optional[str] = Field(
        None, description="지역 코드 (1:서울, 6:부산, 39:제주 등)")
    content_type: Optional[str] = Field(
        None, description="콘텐츠 타입 (12:관광지, 39:음식점 등)")
    include_similarity: bool = Field(True, description="유사도 점수 포함 여부")


class TourismItem(BaseModel):
    id: str
    title: str
    address: Optional[str] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    similarity_score: Optional[float] = None


class TourismSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[Dict[str, Any]]
    filters_applied: Dict[str, str]


class StatsResponse(BaseModel):
    total_items: int
    embedding_type: str
    collection_name: str
