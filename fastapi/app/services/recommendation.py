# app/services/recommendation.py
"""
AI 여행 추천 서비스 - 완전 통합 버전
- 기존 위치 기반 추천 (완전한 하위 호환성)
- 새로운 하이브리드 RAG 추천 (위치 + 선호도 + Vector DB)
- RAG 패턴: Vector DB 검색 결과를 OpenAI 프롬프트 컨텍스트로 활용
"""

import openai
import json
import logging
import math
from typing import List, Dict, Optional, Union
from datetime import datetime
from fastapi import HTTPException
from openai import OpenAI

from app.core.config import settings, OPENAI_API_KEY
from app.schemas.travel import UserRequest

# 조건부 import - KTO 기능이 활성화된 경우에만 Vector 검색 기능 로드
try:
    if settings.is_kto_enabled:
        from app.services.tourism_search import tourism_search
        from app.services.hybrid_search import hybrid_search_service
        from app.schemas.search import LocationBasedRequest
        VECTOR_SEARCH_AVAILABLE = True
    else:
        VECTOR_SEARCH_AVAILABLE = False
        tourism_search = None
        hybrid_search_service = None
        print("ℹ️ KTO 키가 설정되지 않아 Vector 검색 기능이 비활성화됩니다.")
except ImportError as e:
    VECTOR_SEARCH_AVAILABLE = False
    tourism_search = None
    hybrid_search_service = None
    print(f"⚠️ Vector 검색 모듈 로드 실패: {e}")

# 로거 설정
logger = logging.getLogger(__name__)


class RecommendationService:
    """
    AI 여행 추천 서비스
    - RAG 패턴: Vector DB 검색 결과를 OpenAI 프롬프트 컨텍스트로 활용
    - 하이브리드 검색: 위치 + 선호도 + 의미 검색 통합
    - 하위 호환성: 기존 함수 시그니처 완전 지원
    - 조건부 기능: KTO 키 없어도 기본 OpenAI 추천 동작
    """

    def __init__(self):
        """서비스 초기화"""
        # 최신 OpenAI 클라이언트 사용
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Vector 검색 서비스 설정
        self.search_service = tourism_search if VECTOR_SEARCH_AVAILABLE else None
        self.hybrid_service = hybrid_search_service if VECTOR_SEARCH_AVAILABLE else None
        self.vector_enabled = VECTOR_SEARCH_AVAILABLE and settings.is_kto_enabled

        # 초기화 상태 로깅
        if self.vector_enabled:
            logger.info("✅ RAG 모드 활성화: Vector DB + OpenAI")
        else:
            logger.info("ℹ️ 기본 모드: OpenAI만 사용")

    # ==================== 1. 기존 위치 기반 추천 (완전한 하위 호환성 보장) ====================

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

                    # 거리 계산 (가능한 경우)
                    distance_info = ""
                    if metadata.get('mapy') and metadata.get('mapx'):
                        try:
                            place_lat = float(metadata['mapy'])
                            place_lon = float(metadata['mapx'])
                            distance = self._calculate_distance_km(
                                request.latitude, request.longitude,
                                place_lat, place_lon
                            )
                            distance_info = f" (거리: {distance:.1f}km)"
                        except (ValueError, TypeError):
                            pass

                    context_lines.append(
                        f"{idx}. {metadata.get('title', 'N/A')}\n"
                        f"   📍 주소: {metadata.get('addr1', 'N/A')}{distance_info}\n"
                        f"   🏷️ 분류: {metadata.get('cat2', metadata.get('cat1', 'N/A'))}\n"
                        f"   📞 연락처: {metadata.get('tel', '정보없음')}\n"
                        f"   📊 관련도: {similarity:.2f}\n"
                        f"   🗺️ 좌표: ({metadata.get('mapy', 'N/A')}, {metadata.get('mapx', 'N/A')})"
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
            "nature": "자연 관광지 산 바다 공원 힐링",
            "culture": "문화 유적지 박물관 궁궐 전통 역사",
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
        # 주요 도시별 경계 정의
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

    def _calculate_distance_km(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Haversine 공식으로 두 좌표 간 거리 계산 (km)
        """
        R = 6371.0  # 지구 반지름 (km)

        # 라디안 변환
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # 차이 계산
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine 공식
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

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

**🎯 중요 지침:**
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
            return HTTPException(
                status_code=500,
                detail="AI 서비스 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            )
        elif "JSON" in str(error) or "파싱" in str(error):
            return HTTPException(
                status_code=500,
                detail="AI 응답 처리 중 오류가 발생했습니다."
            )
        else:
            return HTTPException(
                status_code=500,
                detail=f"추천 서비스 오류: {str(error)}"
            )

    # ==================== 2. 신규 하이브리드 RAG 추천 ====================

    async def get_location_based_rag_recommendations(
        self,
        request: LocationBasedRequest
    ) -> Dict:
        """
        위치 + 선호도 기반 RAG 추천 (완전 개선 버전)
        """
        if not self.vector_enabled or not self.hybrid_service:
            return {
                "message": "Vector 검색이 비활성화되어 있습니다.",
                "reason": "KTO_SERVICE_KEY가 설정되지 않았습니다.",
                "fallback": "기본 위치 기반 추천(/travel/recommend-travel)을 사용해주세요.",
                "recommendations": []
            }

        logger.info(f"위치 기반 RAG 추천: ({request.latitude}, {request.longitude})")

        try:
            # 1단계: 하이브리드 검색으로 최적 후보 추출
            hybrid_results = self.hybrid_service.search(request)

            if not hybrid_results:
                return {
                    "message": f"반경 {request.max_distance_km}km 내에 조건에 맞는 장소가 없습니다.",
                    "suggestions": [
                        "검색 반경을 늘려보세요",
                        "선호도를 변경해보세요",
                        "검색어를 수정해보세요"
                    ],
                    "recommendations": [],
                    "hybrid_results": []
                }

            # 2단계: 상위 5개로 RAG 컨텍스트 생성
            top_candidates = hybrid_results[:5]
            rag_context = self._build_location_rag_context(
                top_candidates, request)

            # 3단계: 위치 인식 프롬프트 생성
            prompt = self._build_location_aware_prompt(request, rag_context)

            # 4단계: OpenAI API 호출
            response = await self._call_openai_api(prompt)
            ai_recommendations = self._parse_openai_response(response)

            return {
                "user_location": {
                    "latitude": request.latitude,
                    "longitude": request.longitude,
                    "address_estimate": self._reverse_geocode_estimate(
                        request.latitude,
                        request.longitude
                    )
                },
                "search_params": {
                    "query": request.query,
                    "preference": request.travel_preference.value if request.travel_preference else None,
                    "radius_km": request.max_distance_km,
                    "content_types": request.content_types
                },
                "hybrid_search_results": [
                    {
                        "place_name": r.title,
                        "address": r.address,
                        "distance_km": r.distance_km,
                        "hybrid_score": r.hybrid_score,
                        "content_type": r.content_type_name,
                        "coordinates": {"lat": r.latitude, "lon": r.longitude},
                        "scores": {
                            "distance": r.distance_score,
                            "similarity": r.similarity_score,
                            "preference": r.preference_score
                        }
                    }
                    for r in hybrid_results[:10]
                ],
                "ai_recommendations": ai_recommendations,
                "total_found": len(hybrid_results),
                "search_quality": "excellent" if len(hybrid_results) >= 5 else "limited"
            }

        except Exception as e:
            logger.error(f"OpenAI RAG 생성 실패: {e}")
            # Fallback: 하이브리드 검색 결과만 반환
            return {
                "hybrid_search_results": [r.dict() for r in hybrid_results] if 'hybrid_results' in locals() else [],
                "ai_recommendations": [],
                "note": "AI 추천 생성에 실패했지만, 검색 결과는 정상적으로 제공됩니다.",
                "fallback_mode": True
            }

    def _build_location_rag_context(
        self,
        places: List,
        request: LocationBasedRequest
    ) -> str:
        """위치 기반 RAG 컨텍스트 생성"""
        context_lines = [
            "=== 사용자 위치 기준 실제 존재하는 관광지 정보 ===",
            f"🗺️ 사용자 현재 위치: 위도 {request.latitude}, 경도 {request.longitude}",
            f"🔍 검색 반경: {request.max_distance_km}km",
            f"❤️ 선호 스타일: {request.travel_preference.value if request.travel_preference else '지정 없음'}",
            ""
        ]

        for i, place in enumerate(places, 1):
            # 도보/대중교통 접근성 판단
            if place.distance_km <= 1.5:
                access_method = "도보 가능"
            elif place.distance_km <= 10:
                access_method = "대중교통 이용"
            else:
                access_method = "차량 이용"

            context_lines.append(
                f"{i}. **{place.title}** ({place.content_type_name})\n"
                f"   📍 주소: {place.address}\n"
                f"   📏 거리: {place.distance_km}km ({access_method})\n"
                f"   🎯 종합 점수: {place.hybrid_score:.2f}/1.0\n"
                f"      ├ 거리 점수: {place.distance_score:.2f}\n"
                f"      ├ 관련성 점수: {place.similarity_score:.2f}\n"
                f"      └ 선호도 점수: {place.preference_score:.2f}\n"
                f"   📞 연락처: {place.phone or '정보 없음'}\n"
                f"   🗺️ 정확한 좌표: ({place.latitude}, {place.longitude})\n"
            )

        context_lines.append("\n" + "=" * 60)
        return "\n".join(context_lines)

    def _build_location_aware_prompt(
        self,
        request: LocationBasedRequest,
        context: str
    ) -> str:
        """위치 인식 RAG 프롬프트 생성"""

        preference_descriptions = {
            "nature": "자연과 힐링을 즐기며 여유로운 시간을 보내고 싶어하는",
            "culture": "문화와 역사를 탐방하며 의미 있는 경험을 원하는",
            "food": "맛집과 카페를 탐방하며 미식 경험을 중시하는",
            "shopping": "쇼핑과 거리 구경을 즐기며 트렌드를 따라가는",
            "activity": "액티비티와 체험을 통해 활동적인 시간을 보내고 싶어하는",
            "relaxation": "휴식과 여유를 통해 재충전하고 싶어하는"
        }

        user_profile = ""
        if request.travel_preference:
            user_profile = preference_descriptions.get(
                request.travel_preference.value,
                "다양한 경험을 원하는"
            )

        special_request = ""
        if request.query:
            special_request = f"- 특별 요청사항: \"{request.query}\""

        prompt = f"""
당신은 한국 최고의 여행 전문가입니다. 사용자의 정확한 위치와 개인 선호도를 기반으로 최적의 여행지를 추천해주세요.

**사용자 프로필:**
- 현재 정확한 위치: 위도 {request.latitude}, 경도 {request.longitude}
- 이동 가능 범위: 반경 {request.max_distance_km}km 이내
- 여행 성향: {user_profile}여행자
{special_request}

**핵심 지침:**
아래는 사용자 위치 기준 {request.max_distance_km}km 이내의 **실제 존재하는** 관광지 데이터입니다.
이 정보를 **절대 우선**으로 참고하여 추천해주세요.

{context}

**추천 기준 (중요도 순):**
1. **실제성**: 위 데이터의 실제 장소만 추천 (가상의 장소 절대 금지)
2. **접근성**: 거리가 가까운 곳 우선 (도보 > 대중교통 > 차량)
3. **선호도 일치**: 사용자 여행 성향과 부합하는 곳
4. **종합 점수**: 거리+관련성+선호도를 종합한 점수가 높은 곳
5. **동선 효율성**: 방문 순서를 고려한 합리적 경로

**응답 형식 (JSON):**
반드시 'recommendations' 키를 가진 JSON 객체로 응답하세요.
각 추천 장소는 다음 정보를 포함해야 합니다:

{{
  "recommendations": [
    {{
      "place_name": "위 데이터의 정확한 장소명",
      "latitude": 위 데이터의 정확한 위도(float),
      "longitude": 위 데이터의 정확한 경도(float),
      "distance_km": 위 데이터의 정확한 거리(float),
      "description": "추천 이유 및 특징 (150자 내외)",
      "visit_order": 방문 순서(1부터 시작),
      "estimated_time": "예상 소요 시간 (예: 1-2시간)",
      "access_method": "접근 방법 (도보/대중교통/차량)",
      "why_perfect": "사용자 선호도와 어떻게 맞는지 구체적 설명"
    }}
  ]
}}

**주의사항:**
- 총 3-5개 장소 추천
- 모든 정보는 위 실제 데이터에서 정확히 가져올 것
- 가상의 장소나 잘못된 좌표 절대 금지
- 사용자 위치에서 실제 이동 가능한 동선 고려
"""
        return prompt

    def _reverse_geocode_estimate(self, latitude: float, longitude: float) -> str:
        """간단한 역지오코딩 (대략적 주소 추정)"""
        # 주요 지역 추정 로직
        if 37.4 <= latitude <= 37.7 and 126.7 <= longitude <= 127.2:
            return "서울특별시 일대"
        elif 35.0 <= latitude <= 35.4 and 128.8 <= longitude <= 129.3:
            return "부산광역시 일대"
        elif 33.1 <= latitude <= 33.6 and 126.1 <= longitude <= 127.0:
            return "제주특별자치도 일대"
        else:
            return f"위도 {latitude:.3f}, 경도 {longitude:.3f} 일대"

    # ==================== 3. 기존 Vector 검색 기능 (하위 호환성) ====================

    def get_travel_recommendations_by_query(
        self,
        user_query: str,
        preferences: dict = None
    ) -> Dict:
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
        status = {
            "openai_enabled": bool(settings.OPENAI_API_KEY),
            "vector_search_enabled": self.vector_enabled,
            "kto_data_available": settings.is_kto_enabled,
            "embedding_type": settings.EMBEDDING_TYPE if self.vector_enabled else None,
            "total_tourism_data": 0
        }

        if self.vector_enabled and self.search_service:
            try:
                stats = self.search_service.get_stats()
                status["total_tourism_data"] = stats.get("total_items", 0)
            except Exception as e:
                logger.warning(f"통계 조회 실패: {e}")

        return status


# ==================== 전역 서비스 인스턴스 ====================
recommendation_service = RecommendationService()


# ==================== 기존 함수 호환성 유지 (완벽한 하위 호환성) ====================
async def get_travel_recommendations(request: UserRequest) -> list:
    """
    기존 함수 시그니처 완전 유지 - 하위 호환성 보장
    내부적으로는 향상된 RAG 기능 사용
    """
    return await recommendation_service.get_travel_recommendations(request)


# ==================== 레거시 OpenAI 설정 유지 ====================
# 기존 코드에서 직접 참조하는 경우를 위한 호환성 유지
openai.api_key = OPENAI_API_KEY
