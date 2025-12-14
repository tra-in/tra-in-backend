"""
위치 + 선호도 통합 하이브리드 검색 서비스 (스마트 Fallback 포함)
RAG 데이터 부족 시 AI 쿼리 재해석 및 OpenAI 지식 기반 추천 자동 실행
"""

import math
import json
from typing import List, Dict, Optional, Tuple
import logging
from functools import lru_cache
from openai import OpenAI

from app.core.config import settings
from app.core.vector_db import vector_db
from app.schemas.search import LocationBasedRequest, HybridSearchResult, TravelPreference
from app.services.query_analyzer import query_analyzer

logger = logging.getLogger(__name__)


class HybridSearchService:
    """위치 + 선호도 통합 검색 서비스 (3단계 스마트 Fallback)"""

    def __init__(self):
        self.collection = vector_db.get_collection()

        # OpenAI 클라이언트 초기화
        try:
            if settings.OPENAI_API_KEY:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.openai_available = True
            else:
                self.openai_client = None
                self.openai_available = False
                logger.warning("⚠️ OpenAI API 키 미설정 - AI 기능 비활성화")
        except Exception as e:
            logger.error(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
            self.openai_client = None
            self.openai_available = False

        # 선호도 → 검색 키워드 매핑
        self.preference_keywords = {
            TravelPreference.NATURE: "자연 산 바다 공원 숲 계곡 해변 힐링",
            TravelPreference.CULTURE: "박물관 미술관 궁궐 사찰 유적지 전통 역사",
            TravelPreference.FOOD: "맛집 음식점 카페 레스토랑 전통음식 디저트",
            TravelPreference.SHOPPING: "쇼핑 시장 백화점 거리 상점 쇼핑몰",
            TravelPreference.ACTIVITY: "체험 액티비티 레저 스포츠 놀이 테마파크",
            TravelPreference.RELAXATION: "힐링 휴식 온천 스파 조용한 여유"
        }

        # 선호도 → 콘텐츠 타입 매핑
        self.preference_content_types = {
            TravelPreference.NATURE: ["12", "25"],
            TravelPreference.CULTURE: ["12", "14"],
            TravelPreference.FOOD: ["39"],
            TravelPreference.SHOPPING: ["38"],
            TravelPreference.ACTIVITY: ["28"],
            TravelPreference.RELAXATION: ["32", "12"]
        }

    def search(self, request: LocationBasedRequest) -> List[HybridSearchResult]:
        """
        3단계 스마트 Fallback 검색 실행

        1단계: 기존 파라미터로 RAG 검색
        2단계: AI 쿼리 재해석 + RAG 재검색  
        3단계: 순수 OpenAI 지식 기반 추천
        """
        logger.info(f"🔍 스마트 하이브리드 검색 시작")
        logger.info(f"  - 쿼리: {request.query}")
        logger.info(f"  - 위치: ({request.latitude}, {request.longitude})")
        logger.info(f"  - 반경: {request.max_distance_km}km")
        logger.info(f"  - 선호도: {request.travel_preference}")

        # ===== 1단계: 기존 RAG 검색 =====
        base_results = self._search_with_current_params(request)

        if len(base_results) >= max(3, request.n_results * 0.5):
            logger.info(f"✅ 1단계(기본 RAG) 성공: {len(base_results)}개 결과")
            return base_results[:request.n_results]

        logger.warning(f"⚠️ 1단계 결과 부족 ({len(base_results)}개) → AI 쿼리 재해석 시도")

        # ===== 2단계: AI 쿼리 재해석 + RAG 재검색 =====
        ai_rag_results = []
        if request.query and self.openai_available:
            ai_rag_results = self._search_with_ai_reinterpretation(request)

        combined_results = self._merge_unique_results(
            base_results, ai_rag_results)

        if len(combined_results) >= max(2, request.n_results * 0.3):
            logger.info(f"✅ 2단계(AI 재해석) 성공: {len(combined_results)}개 결과")
            return combined_results[:request.n_results]

        logger.warning(
            f"⚠️ 2단계도 부족 ({len(combined_results)}개) → OpenAI 순수 생성 시도")

        # ===== 3단계: 순수 OpenAI 생성 =====
        ai_only_results = []
        if self.openai_available:
            ai_only_results = self._generate_with_openai_knowledge(request)

        final_results = self._merge_unique_results(
            combined_results, ai_only_results)

        logger.info(
            f"✅ 최종 결과: {len(final_results)}개 "
            f"(RAG: {len(combined_results)}, AI생성: {len(ai_only_results)})"
        )
        return final_results[:request.n_results]

    def _search_with_current_params(self, request: LocationBasedRequest) -> List[HybridSearchResult]:
        """1단계: 현재 파라미터로 RAG 검색"""
        candidates = self.get_location_candidates(
            request.latitude,
            request.longitude,
            request.max_distance_km
        )

        if not candidates:
            logger.warning("📍 반경 내 후보 없음")
            return []

        enhanced_query = self.build_enhanced_query(
            request.query,
            request.travel_preference
        )

        content_types = getattr(request, 'content_types', None)
        if not content_types and request.travel_preference:
            content_types = self.preference_content_types.get(
                request.travel_preference, []
            )

        vector_results = self.vector_search_in_candidates(
            enhanced_query,
            candidates,
            request.n_results * 2,
            content_types
        )

        final_results = []

        for result in vector_results:
            metadata = result['metadata']

            preference_match = False
            if request.travel_preference and content_types:
                content_type = metadata.get('contenttypeid')
                preference_match = content_type in content_types

            hybrid_score, score_breakdown = self.calculate_hybrid_score(
                result['distance_km'],
                result.get('vector_distance', 0.0),
                preference_match,
                request.max_distance_km,
                {
                    'distance_weight': request.distance_weight,
                    'similarity_weight': request.similarity_weight,
                    'preference_weight': request.preference_weight
                }
            )

            search_result = HybridSearchResult(
                id=str(result['id']),
                title=metadata.get('title', 'N/A'),
                address=metadata.get('addr1'),
                content_type=metadata.get('contenttypeid', 'N/A'),
                content_type_name=self._get_content_type_name(
                    metadata.get('contenttypeid')),
                latitude=result['latitude'],
                longitude=result['longitude'],
                distance_km=result['distance_km'],
                hybrid_score=round(hybrid_score, 3),
                distance_score=score_breakdown['distance_score'],
                similarity_score=score_breakdown['similarity_score'],
                preference_score=score_breakdown['preference_score'],
                phone=metadata.get('tel'),
                image_url=metadata.get('firstimage'),
                category=metadata.get('cat2')
            )

            final_results.append(search_result)

        final_results.sort(key=lambda x: x.hybrid_score, reverse=True)

        logger.info(f"🔎 1단계 RAG 검색 완료: {len(final_results)}개")
        return final_results

    def _search_with_ai_reinterpretation(self, request: LocationBasedRequest) -> List[HybridSearchResult]:
        """2단계: AI 쿼리 재해석 후 RAG 재검색"""
        logger.info("🤖 AI 쿼리 재해석 시작")

        analysis = query_analyzer.analyze_travel_intent(
            user_query=request.query,
            current_location={
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        )

        optimized_queries = analysis.get("optimized_queries", [request.query])
        suggested_radius = analysis.get(
            "suggested_radius_km", request.max_distance_km * 2)
        inferred_preference_str = analysis.get("inferred_preference")
        suggested_content_types = analysis.get("content_types", [])

        logger.info(f"📊 AI 재해석 결과:")
        logger.info(f"  - 최적화 쿼리: {optimized_queries}")
        logger.info(f"  - 권장 반경: {suggested_radius}km")
        logger.info(f"  - 추론 선호도: {inferred_preference_str}")

        preference = None
        if inferred_preference_str:
            try:
                preference = TravelPreference(inferred_preference_str.lower())
            except ValueError:
                preference = request.travel_preference

        all_results = []

        for query in optimized_queries[:3]:
            optimized_request = request.copy(update={
                "query": query,
                "max_distance_km": min(float(suggested_radius), 100.0),
                "travel_preference": preference or request.travel_preference,
                "content_types": suggested_content_types or getattr(request, 'content_types', None)
            })

            sub_results = self._search_with_current_params(optimized_request)
            all_results.extend(sub_results)

        unique_results = self._deduplicate_by_id(all_results)

        logger.info(f"✅ AI 재해석 검색 완료: {len(unique_results)}개")
        return unique_results

    def _generate_with_openai_knowledge(self, request: LocationBasedRequest) -> List[HybridSearchResult]:
        """3단계: 순수 OpenAI 지식 기반 추천"""
        if not self.openai_available:
            logger.warning("OpenAI 클라이언트 미구성 → AI 생성 불가")
            return []

        logger.warning("🤖 RAG 데이터 부족 → OpenAI 지식 기반 추천 생성")

        system_prompt = """당신은 한국 여행 전문 가이드입니다.
한국 내 실제 존재하는 여행지만 추천하세요.
존재하지 않는 장소를 만들어내지 마세요.
사용자의 현재 위치와 요청을 고려하여 적절한 거리 내의 장소를 추천하세요."""

        user_prompt = f"""
[사용자 정보]
- 현재 위치: 위도 {request.latitude}, 경도 {request.longitude}
- 요청: {request.query}
- 선호도: {request.travel_preference.value if request.travel_preference else '지정 안 됨'}
- 최대 거리: {request.max_distance_km}km
- 추천 개수: {min(request.n_results, 8)}개

[응답 형식]
아래 JSON 형식으로만 답변하세요:

{{
  "recommendations": [
    {{
      "name": "장소명",
      "address": "주소 (시/군/구 포함)",
      "latitude": 37.123,
      "longitude": 127.456,
      "description": "왜 이 장소가 적합한지 간단 설명",
      "category": "자연/힐링/공원/산/계곡/바다/도시/카페 등"
    }}
  ]
}}
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            recommendations = data.get("recommendations", [])

            openai_results = []
            for i, rec in enumerate(recommendations):
                lat = rec.get("latitude", request.latitude)
                lon = rec.get("longitude", request.longitude)

                distance = self.calculate_distance_km(
                    request.latitude, request.longitude,
                    lat, lon
                )

                result = HybridSearchResult(
                    id=f"openai_generated_{i}",
                    title=rec.get("name", "AI 추천 장소"),
                    address=rec.get("address", "주소 정보 없음"),
                    content_type="12",
                    content_type_name="AI 추천",
                    latitude=lat,
                    longitude=lon,
                    distance_km=round(distance, 1),
                    hybrid_score=0.65,
                    distance_score=0.5,
                    similarity_score=0.9,
                    preference_score=0.6,
                    phone=None,
                    image_url=None,
                    category=f"AI 추천 ({rec.get('category', '기타')})"
                )
                openai_results.append(result)

            logger.info(f"🤖 OpenAI 추천 생성: {len(openai_results)}개")
            return openai_results

        except Exception as e:
            logger.error(f"❌ OpenAI 추천 생성 실패: {e}")
            return []

    # ===== 유틸리티 메서드 =====

    def calculate_distance_km(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Haversine 공식으로 두 좌표 간 거리(km) 계산"""
        R = 6371.0

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    @lru_cache(maxsize=50)
    def get_location_candidates(
        self,
        user_lat: float,
        user_lon: float,
        max_distance_km: float
    ) -> List[Dict]:
        """지리적 사전 필터링"""
        logger.info(
            f"📍 위치 후보 추출: ({user_lat}, {user_lon}) 반경 {max_distance_km}km")

        area_code = self._estimate_area_code(user_lat, user_lon)
        where_filter = {"areacode": area_code} if area_code else None

        all_results = self.collection.get(
            limit=1000,
            where=where_filter,
            include=['metadatas']
        )

        logger.info(f"📊 DB에서 가져온 데이터: {len(all_results.get('ids', []))}개")

        candidates = []

        if all_results and all_results.get('metadatas'):
            for i, metadata in enumerate(all_results['metadatas']):
                lat_str = metadata.get('mapy')
                lon_str = metadata.get('mapx')

                if not lat_str or not lon_str:
                    continue

                try:
                    place_lat = float(lat_str)
                    place_lon = float(lon_str)

                    distance = self.calculate_distance_km(
                        user_lat, user_lon,
                        place_lat, place_lon
                    )

                    if distance <= max_distance_km:
                        candidates.append({
                            'id': all_results['ids'][i],
                            'metadata': metadata,
                            'distance_km': round(distance, 2),
                            'latitude': place_lat,
                            'longitude': place_lon
                        })

                except (ValueError, TypeError):
                    continue

        candidates.sort(key=lambda x: x['distance_km'])

        logger.info(f"📍 최종 위치 후보: {len(candidates)}개")
        return candidates

    def build_enhanced_query(
        self,
        user_query: Optional[str],
        preference: Optional[TravelPreference]
    ) -> str:
        """검색 쿼리 강화"""
        query_parts = []

        if user_query:
            query_parts.append(user_query.strip())

        if preference and preference in self.preference_keywords:
            keywords = self.preference_keywords[preference]
            query_parts.append(keywords)

        enhanced_query = " ".join(query_parts)

        if not enhanced_query.strip():
            enhanced_query = "관광지 명소 추천"

        logger.info(f"🔍 강화된 검색 쿼리: {enhanced_query}")
        return enhanced_query

    def vector_search_in_candidates(
        self,
        query: str,
        candidates: List[Dict],
        n_results: int,
        content_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """후보군 내에서 Vector 검색"""
        if not candidates:
            return []

        if settings.EMBEDDING_TYPE == "korean" and vector_db.model:
            query_embedding = vector_db.generate_embedding(query)
        else:
            logger.warning("한국어 임베딩 모델 미사용")
            return candidates[:n_results]

        candidate_ids = [c['id'] for c in candidates]
        candidates_dict = {c['id']: c for c in candidates}

        search_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(len(candidates) * 2, 100),
            include=['metadatas', 'distances']
        )

        filtered_results = []

        if search_results.get('ids') and search_results['ids'][0]:
            for i, result_id in enumerate(search_results['ids'][0]):
                if result_id in candidates_dict:
                    candidate = candidates_dict[result_id]
                    metadata = search_results['metadatas'][0][i]
                    vector_distance = search_results['distances'][0][i]

                    if content_types:
                        content_type = metadata.get('contenttypeid')
                        if content_type not in content_types:
                            continue

                    filtered_results.append({
                        **candidate,
                        'vector_distance': vector_distance,
                        'metadata': metadata
                    })

        logger.info(f"🔎 Vector 검색 결과: {len(filtered_results)}개")
        return filtered_results[:n_results]

    def calculate_hybrid_score(
        self,
        distance_km: float,
        vector_distance: float,
        preference_match: bool,
        max_distance: float,
        weights: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """하이브리드 점수 계산"""
        distance_score = 1 / (1 + (distance_km / (max_distance / 3)) ** 2)
        similarity_score = 1 / (1 + vector_distance / 20)
        preference_score = 1.0 if preference_match else 0.6

        hybrid_score = (
            distance_score * weights['distance_weight'] +
            similarity_score * weights['similarity_weight'] +
            preference_score * weights['preference_weight']
        )

        return hybrid_score, {
            'distance_score': round(distance_score, 3),
            'similarity_score': round(similarity_score, 3),
            'preference_score': round(preference_score, 3)
        }

    def _merge_unique_results(
        self,
        results1: List[HybridSearchResult],
        results2: List[HybridSearchResult]
    ) -> List[HybridSearchResult]:
        """두 결과 리스트 병합 (중복 제거, 점수 기준 정렬)"""
        merged = {r.id: r for r in results1}

        for r in results2:
            if r.id not in merged:
                merged[r.id] = r
            elif r.hybrid_score > merged[r.id].hybrid_score:
                merged[r.id] = r

        sorted_results = sorted(
            merged.values(),
            key=lambda x: x.hybrid_score,
            reverse=True
        )

        return sorted_results

    def _deduplicate_by_id(self, results: List[HybridSearchResult]) -> List[HybridSearchResult]:
        """ID 기준 중복 제거"""
        seen = {}
        for result in results:
            if result.id not in seen or result.hybrid_score > seen[result.id].hybrid_score:
                seen[result.id] = result
        return list(seen.values())

    def _estimate_area_code(self, latitude: float, longitude: float) -> Optional[str]:
        """위도/경도 기반 지역 코드 추정 (성능 최적화용)"""
        regions = {
            "1": {"lat_range": (37.428, 37.701), "lon_range": (126.764, 127.183)},
            "6": {"lat_range": (35.000, 35.362), "lon_range": (128.850, 129.300)},
            "39": {"lat_range": (33.100, 33.570), "lon_range": (126.150, 126.950)},
            "2": {"lat_range": (37.260, 37.650), "lon_range": (126.400, 126.850)},
            "4": {"lat_range": (35.650, 36.000), "lon_range": (128.450, 128.750)},
            "3": {"lat_range": (36.200, 36.450), "lon_range": (127.300, 127.550)},
        }

        for area_code, bounds in regions.items():
            lat_min, lat_max = bounds["lat_range"]
            lon_min, lon_max = bounds["lon_range"]

            if lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max:
                return area_code

        return None

    def _get_content_type_name(self, content_type: str) -> str:
        """콘텐츠 타입 코드 → 이름 변환"""
        type_map = {
            "12": "관광지", "14": "문화시설", "15": "축제공연행사",
            "25": "여행코스", "28": "레포츠", "32": "숙박",
            "38": "쇼핑", "39": "음식점"
        }
        return type_map.get(content_type, "기타")


# 전역 인스턴스
hybrid_search_service = HybridSearchService()
