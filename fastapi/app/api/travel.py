# app/api/travel.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
import logging

from app.schemas.travel import UserRequest, RecommendedPlace
from app.services.recommendation import get_travel_recommendations, recommendation_service
from app.core.config import settings
from app.schemas.search import LocationBasedRequest, HybridSearchResponse

# 조건부 import - KTO 기능이 활성화된 경우에만 Vector 검색 기능 로드
try:
    if settings.is_kto_enabled:
        from app.schemas.search import (
            TourismSearchRequest,
            TourismSearchResponse,
            StatsResponse
        )
        from app.services.tourism_search import tourism_search
        from app.services.hybrid_search import hybrid_search_service
        VECTOR_SEARCH_AVAILABLE = True
    else:
        VECTOR_SEARCH_AVAILABLE = False
        tourism_search = None
        hybrid_search_service = None
        print("KTO 키가 설정되지 않아 Vector 검색 기능이 비활성화됩니다.")
except ImportError as e:
    VECTOR_SEARCH_AVAILABLE = False
    tourism_search = None
    print(f"Vector 검색 모듈 로드 실패: {e}")

# 로거 설정
logger = logging.getLogger(__name__)

# APIRouter 인스턴스 생성 - 일관된 URL 구조 제공
router = APIRouter(
    prefix="/travel",
    tags=["Travel"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Not found"},
        503: {"description": "Service unavailable"}
    }
)


# ==================== 1. 기존 API 엔드포인트 (완벽한 하위 호환성 보장) ====================

@router.post(
    "/recommend-travel",
    response_model=List[RecommendedPlace],
    summary="여행지 추천 API (기존)",
    description="""
    **기존 API - 완전한 하위 호환성 보장**
    
    사용자의 현재 위치(위도, 경도)와 여행 선호도를 기반으로 주변 여행지를 추천합니다.
    
    ### 자동 업그레이드된 기능:
    - **RAG 모드**: KTO 데이터가 있으면 실제 관광지 정보를 기반으로 더 정확한 추천
    - **기본 모드**: KTO 데이터가 없어도 OpenAI 기반 일반 추천으로 정상 작동
    
    ### 파라미터:
    - **latitude**: WGS84 위도 (예: 37.5665)
    - **longitude**: WGS84 경도 (예: 126.9780)  
    - **travel_type**: 선호 여행 스타일
      - `"nature"` - 자연 관광지
      - `"culture"` - 문화/역사 시설
      - `"food"` - 맛집/카페
      - `"shopping"` - 쇼핑 장소
      - `"activity"` - 액티비티/레저
      - `"relaxation"` - 휴양/힐링
    """
)
async def recommend_travel_places(request: UserRequest):
    """
    기존 여행지 추천 API - 인터페이스 완전 동일, 내부 로직만 RAG로 강화
    """
    try:
        recommendations = await get_travel_recommendations(request)

        if not recommendations:
            raise HTTPException(
                status_code=404,
                detail="현재 조건에 맞는 추천 장소를 찾을 수 없습니다. 다른 여행 타입이나 위치로 시도해보세요."
            )

        logger.info(
            f"추천 완료: {len(recommendations)}개 장소 (위치: {request.latitude}, {request.longitude})")
        return recommendations

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"여행지 추천 중 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail="추천 서비스에 일시적 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )


# ==================== 2. Vector 기반 검색 API (조건부 활성화) ====================

if VECTOR_SEARCH_AVAILABLE:

    @router.post(
        "/search",
        response_model=TourismSearchResponse,
        summary="관광지 의미 기반 검색 (Vector DB)",
        description="""
        **Vector DB를 활용한 고급 검색 기능**
        
        ### 의미 기반 검색:
        - 단순 키워드 매칭이 아닌 의미 이해 기반 검색
        - 자연어 쿼리 지원 ("가족과 가기 좋은 서울 맛집")
        - 유사도 점수 제공으로 관련성 확인 가능
        
        ### 필터링 옵션:
        - **area_code**: 지역 제한 (1=서울, 6=부산, 39=제주 등)
        - **content_type**: 콘텐츠 타입 (12=관광지, 39=음식점 등)
        - **n_results**: 결과 개수 (1~50)
        
        ### 사용 예시:
        ```json
        {
          "query": "서울 데이트 코스 카페",
          "area_code": "1",
          "content_type": "39",
          "n_results": 10
        }
        ```
        """
    )
    async def search_tourism_places(request: TourismSearchRequest):
        """상세 관광지 검색 (POST 방식)"""
        try:
            results = tourism_search.search(
                query=request.query,
                n_results=request.n_results,
                area_code=request.area_code,
                content_type=request.content_type,
                include_distances=request.include_similarity
            )

            logger.info(
                f"검색 완료: '{request.query}' -> {results.get('total_results', 0)}개 결과")
            return TourismSearchResponse(**results)

        except Exception as e:
            logger.error(f"Vector 검색 중 오류: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"검색 처리 중 오류가 발생했습니다: {str(e)}"
            )

    @router.get(
        "/search/simple",
        summary="간단한 관광지 검색 (GET)",
        description="""
        **URL 파라미터를 통한 간편 검색**
        
        브라우저에서 직접 호출하거나 간단한 GET 요청으로 검색할 때 사용합니다.
        
        ### 예시:
        ```
        GET /travel/search/simple?q=경복궁&limit=5&area=1
        ```
        """
    )
    async def simple_search(
        q: str = Query(..., description="검색어", example="경복궁"),
        limit: int = Query(10, ge=1, le=50, description="결과 개수"),
        area: Optional[str] = Query(None, description="지역 코드", example="1"),
        type: Optional[str] = Query(None, description="콘텐츠 타입", example="12")
    ):
        """간단한 GET 방식 검색"""
        try:
            results = tourism_search.search(
                query=q,
                n_results=limit,
                area_code=area,
                content_type=type
            )

            logger.info(
                f"간단 검색: '{q}' -> {results.get('total_results', 0)}개 결과")
            return results

        except Exception as e:
            logger.error(f"간단 검색 중 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/recommend/query",
        summary="자연어 기반 AI 추천 (RAG)",
        description="""
        **자연어 질문으로 맞춤 추천 받기**
        
        ### AI + Vector DB 결합:
        - Vector DB에서 실제 관광지 데이터 검색
        - 검색 결과를 OpenAI에 컨텍스트로 제공
        - 자연스럽고 정확한 추천 생성
        
        ### 자연어 쿼리 예시:
        - "가족과 함께 갈 만한 서울 관광지"
        - "부산에서 바다 뷰 맛집 추천해줘"
        - "제주도 혼자 여행하기 좋은 곳"
        - "아이들과 가기 좋은 경기도 체험 장소"
        """
    )
    async def get_ai_recommendations_by_query(
        query: str = Query(..., description="자연어 추천 요청",
                           example="가족과 함께 갈 만한 서울 관광지"),
        area_code: Optional[str] = Query(None, description="지역 필터"),
        content_type: Optional[str] = Query(None, description="콘텐츠 타입 필터"),
        limit: int = Query(10, ge=1, le=30, description="결과 개수")
    ):
        """자연어 기반 AI 추천 (RAG 모드)"""
        try:
            preferences = {}
            if area_code:
                preferences["area_code"] = area_code
            if content_type:
                preferences["content_type"] = content_type
            if limit != 10:
                preferences["n_results"] = limit

            result = recommendation_service.get_travel_recommendations_by_query(
                user_query=query,
                preferences=preferences if preferences else None
            )

            logger.info(
                f"AI 추천 완료: '{query}' -> {result.get('total_found', 0)}개 결과")
            return result

        except Exception as e:
            logger.error(f"AI 추천 중 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/similar",
        summary="유사 장소 찾기",
        description="""
        **특정 장소와 비슷한 다른 장소 검색**
        
        좋아하는 장소가 있다면, 그와 유사한 특성을 가진 다른 장소들을 찾아드립니다.
        
        ### 예시:
        - query="경복궁" → 다른 궁궐, 역사적 건물들
        - query="홍대 카페거리" → 비슷한 분위기의 카페 밀집 지역
        """
    )
    async def find_similar_places(
        query: str = Query(..., description="기준이 되는 장소나 특징", example="경복궁"),
        area_code: Optional[str] = Query(None, description="검색 지역 제한"),
        limit: int = Query(10, ge=1, le=30, description="결과 개수")
    ):
        """유사한 장소 검색"""
        try:
            filters = {"n_results": limit}
            if area_code:
                filters["area_code"] = area_code

            results = recommendation_service.search_similar_places(
                query, filters)

            logger.info(
                f"유사 장소 검색: '{query}' -> {results.get('total_results', 0)}개 결과")
            return results

        except Exception as e:
            logger.error(f"유사 장소 검색 중 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    # hybrid search

    @router.post(
        "/search/location-hybrid",
        summary="🎯 위치 + 선호도 하이브리드 검색",
        description="사용자의 정확한 위치와 개인 선호도를 모두 고려한 차세대 검색",
        tags=["Advanced Search"]
    )
    async def location_hybrid_search(request: LocationBasedRequest):
        """위치 + 선호도 통합 하이브리드 검색"""

        # 🔑 안전장치: 서비스 가용성 확인
        if not VECTOR_SEARCH_AVAILABLE or hybrid_search_service is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "하이브리드 검색 기능이 비활성화되어 있습니다.",
                    "reason": "KTO_SERVICE_KEY가 설정되지 않았거나 Vector DB가 준비되지 않았습니다.",
                    "available_alternatives": [
                        "/travel/recommend-travel (기본 위치 기반 추천)",
                        "/travel/search/simple (기본 텍스트 검색)"
                    ],
                    "setup_guide": "KTO API 키를 .env 파일에 설정하고 서버를 재시작해주세요."
                }
            )

        try:
            # 가중치 합계 검증
            total_weight = (
                request.distance_weight +
                request.similarity_weight +
                request.preference_weight
            )
            if abs(total_weight - 1.0) > 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"가중치 합계는 1.0이어야 합니다. 현재: {total_weight:.3f}"
                )

            # 하이브리드 검색 실행
            results = hybrid_search_service.search(request)

            return {
                "search_metadata": {
                    "user_location": {"lat": request.latitude, "lon": request.longitude},
                    "search_radius_km": request.max_distance_km,
                    "travel_preference": request.travel_preference.value if request.travel_preference else None,
                    "query": request.query,
                    "weights": {
                        "distance": request.distance_weight,
                        "similarity": request.similarity_weight,
                        "preference": request.preference_weight
                    }
                },
                "results": [r.dict() for r in results],
                "total_results": len(results),
                "search_quality": {
                    "excellent": len(results) >= 8,
                    "good": 4 <= len(results) < 8,
                    "limited": len(results) < 4
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"하이브리드 검색 오류: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"검색 처리 중 오류가 발생했습니다: {str(e)}"
            )
else:
    # Vector 검색이 비활성화된 경우의 대체 엔드포인트들

    @router.post("/search")
    @router.get("/search/simple")
    @router.get("/recommend/query")
    @router.get("/similar")
    @router.post("/search/location-hybrid")
    async def vector_search_unavailable():
        """Vector 검색 기능 비활성화 안내"""
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Vector 검색 기능이 비활성화되어 있습니다.",
                "reason": "KTO_SERVICE_KEY가 설정되지 않았습니다.",
                "available_api": "/travel/recommend-travel",
                "setup_guide": "KTO API 키를 .env 파일에 설정 후 서버를 재시작해주세요."
            }
        )


# ==================== 3. 시스템 정보 및 통계 ====================


@router.get(
    "/stats",
    response_model=StatsResponse if VECTOR_SEARCH_AVAILABLE else Dict,
    summary="서비스 통계 정보",
    description="Vector DB 저장 데이터 통계 및 서비스 상태 정보"
)
async def get_service_stats():
    """서비스 통계 및 상태 정보"""
    if VECTOR_SEARCH_AVAILABLE:
        try:
            stats = tourism_search.get_stats()
            return StatsResponse(**stats)
        except Exception as e:
            logger.error(f"통계 조회 중 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        return {
            "message": "Vector DB 통계를 사용할 수 없습니다.",
            "reason": "KTO 데이터가 활성화되지 않음",
            "available_features": ["기본 OpenAI 추천"]
        }


@router.get(
    "/status",
    summary="서비스 상태 확인",
    description="전체 추천 서비스의 현재 상태 및 활성화된 기능 확인"
)
async def get_service_status():
    """
    서비스 상태 종합 정보

    Returns:
        현재 활성화된 기능들과 서비스 상태
    """
    try:
        # 기본 상태 정보
        status_info = {
            "service_name": "AI Travel Recommendation API",
            "version": "1.0.0",
            "status": "healthy"
        }

        # 추천 서비스 상태
        if hasattr(recommendation_service, 'get_service_status'):
            rec_status = recommendation_service.get_service_status()
            status_info.update(rec_status)
        else:
            status_info.update({
                "openai_enabled": bool(settings.OPENAI_API_KEY),
                "vector_search_enabled": VECTOR_SEARCH_AVAILABLE,
                "kto_data_available": settings.is_kto_enabled
            })

        # 사용 가능한 기능 목록
        status_info["available_features"] = {
            "location_based_recommendation": True,  # 항상 사용 가능
            "vector_search": VECTOR_SEARCH_AVAILABLE,
            "semantic_search": VECTOR_SEARCH_AVAILABLE,
            "rag_recommendation": VECTOR_SEARCH_AVAILABLE,
            "similarity_search": VECTOR_SEARCH_AVAILABLE,
            "hybrid_search": VECTOR_SEARCH_AVAILABLE
        }

        # API 엔드포인트 맵
        status_info["endpoints"] = {
            "legacy_recommend": "/travel/recommend-travel",
            "vector_search": "/travel/search" if VECTOR_SEARCH_AVAILABLE else None,
            "simple_search": "/travel/search/simple" if VECTOR_SEARCH_AVAILABLE else None,
            "ai_recommend": "/travel/recommend/query" if VECTOR_SEARCH_AVAILABLE else None,
            "similar_search": "/travel/similar" if VECTOR_SEARCH_AVAILABLE else None,
            "hybrid_search": "/travel/search/location-hybrid" if VECTOR_SEARCH_AVAILABLE else None
        }

        return status_info

    except Exception as e:
        logger.error(f"상태 확인 중 오류: {e}")
        return {
            "service_name": "AI Travel Recommendation API",
            "status": "error",
            "error": str(e),
            "basic_features": True
        }


# ==================== 4. 참조 정보 API ====================

@router.get(
    "/area-codes",
    summary="지역 코드 참조표",
    description="검색 및 필터링에 사용할 수 있는 한국 지역 코드 목록",
    response_model=Dict[str, str]
)
async def get_area_codes():
    """
    지역 코드 참조표

    Vector 검색이나 필터링에서 사용할 수 있는 지역 코드 목록입니다.
    """
    return {
        # 특별시/광역시
        "1": "서울특별시",
        "2": "인천광역시",
        "3": "대전광역시",
        "4": "대구광역시",
        "5": "광주광역시",
        "6": "부산광역시",
        "7": "울산광역시",
        "8": "세종특별자치시",

        # 도 지역
        "31": "경기도",
        "32": "강원특별자치도",
        "33": "충청북도",
        "34": "충청남도",
        "35": "경상북도",
        "36": "경상남도",
        "37": "전북특별자치도",
        "38": "전라남도",
        "39": "제주특별자치도"
    }


@router.get(
    "/content-types",
    summary="콘텐츠 타입 참조표",
    description="검색 및 필터링에 사용할 수 있는 관광 콘텐츠 타입 목록",
    response_model=Dict[str, str]
)
async def get_content_types():
    """
    콘텐츠 타입 참조표

    Vector 검색에서 특정 유형의 장소만 필터링할 때 사용합니다.
    """
    return {
        "12": "관광지",
        "14": "문화시설",
        "15": "축제공연행사",
        "25": "여행코스",
        "28": "레포츠",
        "32": "숙박",
        "38": "쇼핑",
        "39": "음식점"
    }


@router.get(
    "/travel-types",
    summary="여행 타입 참조표",
    description="기존 추천 API(/recommend-travel)에서 사용하는 여행 타입 목록"
)
async def get_travel_types():
    """
    여행 타입 참조표

    /recommend-travel API의 travel_type 파라미터에서 사용할 수 있는 값들입니다.
    """
    return {
        "available_types": [
            {
                "value": "nature",
                "label": "자연",
                "description": "산, 바다, 공원, 자연 관광지",
                "examples": ["국립공원", "해변", "산책로", "자연휴양림"]
            },
            {
                "value": "culture",
                "label": "문화",
                "description": "박물관, 궁궐, 유적지, 문화시설",
                "examples": ["경복궁", "국립박물관", "문화재", "전통마을"]
            },
            {
                "value": "food",
                "label": "음식",
                "description": "맛집, 카페, 레스토랑, 특산물",
                "examples": ["전통음식", "카페거리", "시장", "맛집"]
            },
            {
                "value": "shopping",
                "label": "쇼핑",
                "description": "시장, 백화점, 쇼핑몰, 거리",
                "examples": ["명동", "홍대", "전통시장", "아울렛"]
            },
            {
                "value": "activity",
                "label": "액티비티",
                "description": "레저, 스포츠, 체험 활동",
                "examples": ["테마파크", "수상스포츠", "등산", "체험관"]
            },
            {
                "value": "relaxation",
                "label": "휴양",
                "description": "온천, 리조트, 힐링 장소",
                "examples": ["온천", "스파", "리조트", "휴양지"]
            }
        ],
        "usage_note": "이 값들을 /travel/recommend-travel API의 travel_type 필드에 사용하세요."
    }


# ==================== 5. 헬스 체크 ====================

@router.get(
    "/health",
    summary="헬스 체크",
    description="서비스 및 의존성 상태 확인 (로드밸런서/모니터링용)",
    tags=["Health"]
)
async def health_check():
    """
    헬스 체크 엔드포인트

    서비스 상태와 주요 의존성들의 연결 상태를 확인합니다.
    """
    health_info = {
        "status": "healthy",
        "service": "AI Travel Recommendation API",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"  # 실제로는 현재 시간 사용
    }

    # OpenAI 연결 상태
    try:
        health_info["dependencies"] = {
            "openai": "connected" if settings.OPENAI_API_KEY else "not_configured"
        }
    except Exception:
        health_info["dependencies"] = {"openai": "error"}

    # Vector DB 연결 상태 (활성화된 경우에만)
    if VECTOR_SEARCH_AVAILABLE:
        try:
            stats = tourism_search.get_stats()
            health_info["dependencies"]["vector_db"] = {
                "status": "connected",
                "total_items": stats.get("total_items", 0)
            }
        except Exception as e:
            health_info["dependencies"]["vector_db"] = {
                "status": "error",
                "message": str(e)
            }
            health_info["status"] = "degraded"
    else:
        health_info["dependencies"]["vector_db"] = "disabled"

    return health_info
