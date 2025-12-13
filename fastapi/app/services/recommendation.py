# app/services/recommendation.py
import openai
import json
import logging
from typing import List, Dict, Optional, Union
from fastapi import HTTPException
from openai import OpenAI

from app.core.config import settings, OPENAI_API_KEY
from app.schemas.travel import UserRequest

# 조건부 import - KTO 기능이 활성화된 경우에만 Vector 검색 사용
try:
    if settings.is_kto_enabled:
        from app.services.tourism_search import tourism_search
        VECTOR_SEARCH_AVAILABLE = True
    else:
        VECTOR_SEARCH_AVAILABLE = False
        tourism_search = None
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False
    tourism_search = None
    print("Vector 검색 서비스를 로드할 수 없습니다. 기본 OpenAI 모드로 동작합니다.")

# 로거 설정
logger = logging.getLogger(__name__)


class RecommendationService:
    """
    AI 여행 추천 서비스
    - RAG 패턴: Vector DB 검색 결과를 OpenAI 프롬프트 컨텍스트로 활용
    - 하위 호환성: 기존 함수 시그니처 완전 지원
    - 조건부 기능: KTO 키 없어도 기본 OpenAI 추천 동작
    """

    def __init__(self):
        """서비스 초기화"""
        # 최신 OpenAI 클라이언트 사용
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Vector 검색 서비스 설정
        self.search_service = tourism_search if VECTOR_SEARCH_AVAILABLE else None
        self.vector_enabled = VECTOR_SEARCH_AVAILABLE and settings.is_kto_enabled

        # 초기화 상태 로깅
        if self.vector_enabled:
            logger.info("RAG 모드 활성화: Vector DB + OpenAI")
        else:
            logger.info("ℹ기본 모드: OpenAI만 사용")

    async def get_travel_recommendations(self, request: UserRequest) -> List[Dict]:
        """
        여행지 추천 생성 (기존 함수 시그니처 유지 + RAG 강화)

        Args:
            request: UserRequest 객체 (위도, 경도, 여행 타입)

        Returns:
            추천 장소 리스트 [{"place_name", "latitude", "longitude", "description"}]
        """
        try:
            # 1단계: Vector DB에서 실제 관광지 정보 검색 (RAG)
            vector_context = await self._get_vector_context_for_location(request)

            # 2단계: RAG 컨텍스트를 포함한 프롬프트 생성
            prompt = self._build_enhanced_prompt(request, vector_context)

            # 3단계: OpenAI API 호출
            response = await self._call_openai_api(prompt)

            # 4단계: 응답 파싱 및 검증
            recommendations = self._parse_openai_response(response)

            logger.info(f"추천 생성 완료: {len(recommendations)}개 장소")
            return recommendations

        except Exception as e:
            logger.error(f"추천 생성 실패: {e}")
            raise self._handle_recommendation_error(e)

    async def _get_vector_context_for_location(self, request: UserRequest) -> Optional[str]:
        """
        사용자 위치와 선호도 기반으로 Vector DB에서 관련 관광지 검색
        """
        if not self.vector_enabled:
            return None

        try:
            # 검색 쿼리 생성
            search_query = self._build_location_search_query(request)

            # 지역 코드 추정
            area_code = self._estimate_area_code(
                request.latitude, request.longitude)

            # 콘텐츠 타입 매핑
            content_type = self._map_travel_type_to_content_type(
                request.travel_type)

            # Vector 검색 실행
            search_results = self.search_service.search(
                query=search_query,
                n_results=8,
                area_code=area_code,
                content_type=content_type,
                include_distances=True
            )

            # 검색 결과를 프롬프트용 컨텍스트로 변환
            if search_results and search_results.get("results"):
                context_lines = ["=== 실제 존재하는 관련 관광지 정보 (우선 참고) ==="]

                for idx, item in enumerate(search_results["results"][:5], 1):
                    metadata = item.get("metadata", {})
                    similarity = item.get("similarity_score", 0)

                    context_lines.append(
                        f"{idx}. {metadata.get('title', 'N/A')}\n"
                        f"   주소: {metadata.get('addr1', 'N/A')}\n"
                        f"   분류: {metadata.get('cat2', metadata.get('cat1', 'N/A'))}\n"
                        f"   연락처: {metadata.get('tel', '정보없음')}\n"
                        f"   관련도: {similarity:.2f}\n"
                        f"   좌표: ({metadata.get('mapy', 'N/A')}, {metadata.get('mapx', 'N/A')})"
                    )

                context_lines.append("=" * 50)
                context = "\n".join(context_lines)

                logger.info(
                    f"Vector 컨텍스트 생성 완료: {len(search_results['results'])}개 장소")
                return context

            return None

        except Exception as e:
            logger.warning(f"Vector 컨텍스트 생성 실패: {e}")
            return None

    def _build_location_search_query(self, request: UserRequest) -> str:
        """사용자 요청을 검색 쿼리로 변환"""
        # 여행 타입을 한국어로 매핑
        travel_type_kr_map = {
            "nature": "자연 관광지 산 바다 공원",
            "culture": "문화 유적지 박물관 궁궐 전통",
            "food": "맛집 음식점 카페 레스토랑",
            "shopping": "쇼핑 시장 백화점 거리",
            "activity": "레저 스포츠 액티비티 체험",
            "relaxation": "휴양 힐링 온천 리조트"
        }

        base_query = travel_type_kr_map.get(
            request.travel_type, request.travel_type)
        return base_query

    def _estimate_area_code(self, latitude: float, longitude: float) -> Optional[str]:
        """위도/경도 기반 지역 코드 추정 (개선된 버전)"""
        # 주요 도시별 경계 정의 (더 정확한 범위)
        regions = {
            # 서울특별시
            "1": {"lat_range": (37.428, 37.701), "lon_range": (126.764, 127.183)},
            # 부산광역시
            "6": {"lat_range": (35.000, 35.362), "lon_range": (128.850, 129.300)},
            # 제주특별자치도
            "39": {"lat_range": (33.100, 33.570), "lon_range": (126.150, 126.950)},
            # 인천광역시
            "2": {"lat_range": (37.260, 37.650), "lon_range": (126.400, 126.850)},
            # 대구광역시
            "4": {"lat_range": (35.650, 36.000), "lon_range": (128.450, 128.750)},
            # 대전광역시
            "3": {"lat_range": (36.200, 36.450), "lon_range": (127.300, 127.550)},
        }

        for area_code, bounds in regions.items():
            lat_min, lat_max = bounds["lat_range"]
            lon_min, lon_max = bounds["lon_range"]

            if lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max:
                return area_code

        # 광역 지역 추정 (도 단위)
        if 37.0 <= latitude <= 38.2 and 126.5 <= longitude <= 127.8:
            return "31"  # 경기도
        elif 36.8 <= latitude <= 38.5 and 127.8 <= longitude <= 129.5:
            return "32"  # 강원도
        elif 35.6 <= latitude <= 37.2 and 128.0 <= longitude <= 129.5:
            return "35"  # 경상북도
        elif 34.5 <= latitude <= 36.2 and 127.8 <= longitude <= 129.2:
            return "36"  # 경상남도

        return None

    def _map_travel_type_to_content_type(self, travel_type: str) -> Optional[str]:
        """여행 타입을 KTO 콘텐츠 타입으로 매핑"""
        mapping = {
            "nature": "12",      # 관광지
            "culture": "14",     # 문화시설
            "food": "39",        # 음식점
            "shopping": "38",    # 쇼핑
            "activity": "28",    # 레포츠
            "relaxation": "32"   # 숙박
        }
        return mapping.get(travel_type)

    def _build_enhanced_prompt(self, request: UserRequest, vector_context: Optional[str]) -> str:
        """RAG 컨텍스트를 포함한 향상된 프롬프트 생성"""
        base_prompt = f"""
당신은 최고의 여행 전문가입니다. 사용자의 위치와 선호도를 기반으로 여행 계획을 추천해주세요.

**사용자 정보:**
- 현재 위치: 위도 {request.latitude}, 경도 {request.longitude}
- 선호 여행 타입: '{request.travel_type}'
- 요청: 주변 추천 장소 3곳

**응답 형식 (JSON):**
응답은 반드시 'recommendations'라는 키를 가진 JSON 객체여야 하며, 그 값은 JSON 배열이어야 합니다.
배열의 각 객체는 다음 키를 포함해야 합니다:
- 'place_name': 장소 이름 (문자열)
- 'latitude': 위도 (float 형태)
- 'longitude': 경도 (float 형태)  
- 'description': 추천 이유 및 상세 설명 (문자열)
"""

        if vector_context:
            # Vector 검색 결과가 있으면 RAG 컨텍스트 추가
            enhanced_prompt = base_prompt + f"""

**중요 지침:**
아래는 한국관광공사에서 제공하는 실제 존재하는 관광지 정보입니다.
이 정보를 **최우선으로 참고**하여 추천해주세요. 실제 데이터이므로 신뢰성이 높습니다.

{vector_context}

**추천 규칙:**
1. 위 실제 관광지 정보에서 사용자 위치와 가까운 곳을 우선 선택
2. 사용자의 선호 여행 타입에 맞는 장소 선별
3. 실제 좌표 정보가 있는 경우 정확한 위도/경도 사용
4. 모든 추천 장소는 한국 지도에서 검색 가능한 실제 장소여야 함
5. 위 정보에 적절한 장소가 없다면, 검증된 한국의 유명 관광지 추천
"""
        else:
            # Vector 검색 결과가 없으면 기본 지침
            enhanced_prompt = base_prompt + """

**추천 규칙:**
- 모든 장소는 한국 카카오맵/네이버지도에서 검색 가능한 실제 장소여야 합니다.
- 사용자 위치에서 접근 가능한 거리의 장소를 추천해주세요.
- 각 장소의 정확한 위도/경도를 제공해주세요.
"""

        return enhanced_prompt

    async def _call_openai_api(self, prompt: str) -> Dict:
        """OpenAI API 호출"""
        try:
            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful travel assistant that provides accurate recommendations based on real tourism data. Always prioritize verified location information when available."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=settings.OPENAI_TEMPERATURE,
            )
            return response

        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            raise e

    def _parse_openai_response(self, response) -> List[Dict]:
        """OpenAI 응답 파싱 및 검증"""
        try:
            response_content = response.choices[0].message.content
            data = json.loads(response_content)

            recommendations = data.get("recommendations", [])

            if not recommendations:
                raise ValueError("추천 결과가 비어있습니다.")

            # 데이터 검증 및 정제
            validated_recommendations = []
            for rec in recommendations:
                if self._validate_recommendation(rec):
                    validated_recommendations.append(rec)

            if not validated_recommendations:
                raise ValueError("유효한 추천 결과가 없습니다.")

            return validated_recommendations

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            raise ValueError(f"AI 응답 형식 오류: {e}")

    def _validate_recommendation(self, rec: Dict) -> bool:
        """추천 결과 검증"""
        required_fields = ["place_name",
                           "latitude", "longitude", "description"]

        # 필수 필드 확인
        if not all(field in rec for field in required_fields):
            return False

        # 좌표 유효성 확인
        try:
            lat = float(rec["latitude"])
            lon = float(rec["longitude"])

            # 한국 영토 범위 확인 (대략적)
            if not (33.0 <= lat <= 38.6 and 124.0 <= lon <= 132.0):
                logger.warning(f"좌표 범위 이상: {lat}, {lon}")
                # 범위를 벗어나도 일단 허용 (해외 여행일 수도 있음)
        except (ValueError, TypeError):
            logger.warning(
                f"좌표 형식 오류: {rec.get('latitude')}, {rec.get('longitude')}")
            return False

        return True

    def _handle_recommendation_error(self, error: Exception) -> HTTPException:
        """에러 처리 및 사용자 친화적 메시지 생성"""
        if "API" in str(error):
            return HTTPException(status_code=500, detail="AI 서비스 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        elif "JSON" in str(error) or "파싱" in str(error):
            return HTTPException(status_code=500, detail="AI 응답 처리 중 오류가 발생했습니다.")
        else:
            return HTTPException(status_code=500, detail=f"추천 서비스 오류: {str(error)}")

    # ==================== 새로운 Vector 기반 메서드 ====================

    def get_travel_recommendations_by_query(self, user_query: str, preferences: dict = None) -> Dict:
        """
        자연어 쿼리 기반 여행 추천 (Vector 검색 우선)
        """
        if not self.vector_enabled:
            return {
                "user_query": user_query,
                "recommendations": [],
                "message": "Vector 검색이 비활성화되어 있습니다. 위치 기반 추천을 사용해주세요."
            }

        try:
            # Vector 검색으로 관련 관광지 찾기
            context = self.search_service.get_recommendations_for_chat(
                user_query, n_results=8)

            # 상세 검색 결과
            detailed_results = self.search_service.search(
                query=user_query,
                n_results=15,
                area_code=preferences.get(
                    "area_code") if preferences else None,
                content_type=preferences.get(
                    "content_type") if preferences else None
            )

            return {
                "user_query": user_query,
                "context": context,
                "recommendations": detailed_results.get("results", []),
                "total_found": detailed_results.get("total_results", 0),
                "filters_applied": detailed_results.get("filters_applied", {})
            }

        except Exception as e:
            logger.error(f"쿼리 기반 추천 실패: {e}")
            return {
                "user_query": user_query,
                "recommendations": [],
                "error": str(e)
            }

    def search_similar_places(self, query: str, filters: dict = None) -> Dict:
        """유사한 장소 검색 (Vector DB 직접 검색)"""
        if not self.vector_enabled:
            return {
                "query": query,
                "results": [],
                "message": "Vector 검색이 비활성화되어 있습니다."
            }

        return self.search_service.search(
            query=query,
            area_code=filters.get("area_code") if filters else None,
            content_type=filters.get("content_type") if filters else None,
            n_results=filters.get("n_results", 10) if filters else 10
        )

    def get_service_status(self) -> Dict:
        """서비스 상태 정보"""
        return {
            "openai_enabled": bool(settings.OPENAI_API_KEY),
            "vector_search_enabled": self.vector_enabled,
            "kto_data_available": settings.is_kto_enabled,
            "embedding_type": settings.EMBEDDING_TYPE if self.vector_enabled else None,
            "total_tourism_data": self.search_service.get_stats()["total_items"] if self.vector_enabled else 0
        }


# ==================== 전역 서비스 인스턴스 ====================
recommendation_service = RecommendationService()


# ==================== 기존 함수 호환성 유지 ====================
async def get_travel_recommendations(request: UserRequest) -> list:
    """
    기존 함수 시그니처 완전 유지 - 하위 호환성 보장
    내부적으로는 향상된 RAG 기능 사용
    """
    return await recommendation_service.get_travel_recommendations(request)


# ==================== 레거시 OpenAI 설정 유지 ====================
# 기존 코드에서 직접 참조하는 경우를 위한 호환성 유지
openai.api_key = OPENAI_API_KEY
