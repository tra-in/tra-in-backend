"""
AI 기반 여행 쿼리 분석 서비스
사용자의 자연어 쿼리를 분석하여 최적화된 검색 파라미터를 추출합니다.
"""

import logging
import json
from typing import Dict, List, Optional
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """자연어 쿼리 분석 및 검색 파라미터 최적화 서비스"""

    def __init__(self):
        try:
            if not settings.OPENAI_API_KEY:
                logger.warning(
                    "⚠️ OPENAI_API_KEY가 설정되지 않았습니다. AI 분석 기능이 제한됩니다.")
                self.available = False
                self.client = None
            else:
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.available = True
                logger.info("✅ QueryAnalyzer 초기화 성공")
        except Exception as e:
            logger.error(f"❌ QueryAnalyzer 초기화 실패: {e}")
            self.available = False
            self.client = None

    def analyze_travel_intent(
        self,
        user_query: str,
        current_location: Dict[str, float]
    ) -> Dict:
        """
        사용자 쿼리에서 여행 의도를 분석하여 최적화된 검색 파라미터 추출

        Args:
            user_query: "도시를 떠나 혼자 힐링할 수 있는 여행"
            current_location: {"latitude": 37.5665, "longitude": 126.978}

        Returns:
            {
                "optimized_queries": ["자연 힐링 여행지", "산 계곡 휴양지"],
                "inferred_preference": "nature",
                "suggested_radius_km": 50,
                "content_types": ["12", "25"],
                "location_strategy": "expand_suburban",
                "reasoning": "분석 근거"
            }
        """

        if not self.available:
            return self._get_fallback_analysis(user_query)

        system_prompt = """당신은 여행 검색 의도 분석 전문가입니다.
        사용자의 자연어 쿼리를 분석하여 최적의 검색 전략을 JSON으로 제안하세요.

        **응답 형식 (반드시 준수):**
        ```json
        {
        "optimized_queries": ["검색에 최적화된 키워드 조합 1", "키워드 조합 2"],
        "inferred_preference": "nature|culture|food|shopping|activity|relaxation",
        "suggested_radius_km": 숫자,
        "content_types": ["12", "25"],
        "location_strategy": "expand_suburban|stay_urban|go_rural",
        "reasoning": "분석 근거 설명"
        }
        분석 가이드라인:

        "도시를 떠나다", "교외", "근교" → 도심에서 벗어난 지역 선호 (반경 40-80km)
        "혼자" + "힐링" → 조용하고 사색적인 자연/휴양 장소
        "가족" → 안전하고 편의시설이 있는 곳
        "데이트" → 분위기 좋은 카페, 레스토랑, 산책로
        막연한 표현을 구체적 장소로 확장 (예: "자연" → "산", "숲", "계곡", "호수")
        콘텐츠 타입: 12=관광지, 14=문화시설, 15=축제, 25=여행코스, 28=레포츠, 32=숙박, 38=쇼핑, 39=음식점

        반경 가이드:

        도심 내 검색: 5-15km

        근교 여행: 20-50km

        지방/교외: 60-100km"""

        user_prompt = f"""
        사용자 쿼리: "{user_query}" 현재 위치: 위도 {current_location['latitude']}, 경도 {current_location['longitude']}

        이 쿼리를 분석하여 최적의 검색 전략을 제안해주세요. 특히 다음을 고려하세요:

        사용자가 원하는 장소의 특성과 분위기

        현재 위치에서 적절한 검색 반경

        관련된 콘텐츠 타입들

        검색에 효과적인 구체적 키워드들 """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            analysis = json.loads(content)

            logger.info(f"✅ 쿼리 분석 완료:")
            logger.info(f"  - 원본: {user_query}")
            logger.info(f"  - 최적화: {analysis.get('optimized_queries', [])}")
            logger.info(f"  - 권장 반경: {analysis.get('suggested_radius_km')}km")
            logger.info(f"  - 추론 선호도: {analysis.get('inferred_preference')}")
            logger.info(f"  - 근거: {analysis.get('reasoning', 'N/A')}")

            return analysis

        except Exception as e:
            logger.error(f"❌ 쿼리 분석 실패: {e}")
            return self._get_fallback_analysis(user_query)

    def _get_fallback_analysis(self, query: str) -> Dict:
        """AI 분석 실패 시 기본값 반환"""
        query_lower = query.lower()

        if any(keyword in query_lower for keyword in ["도시를 떠나", "교외", "근교"]):
            radius = 50
            preference = "nature"
        elif any(keyword in query_lower for keyword in ["힐링", "휴식", "조용"]):
            radius = 30
            preference = "relaxation"
        elif any(keyword in query_lower for keyword in ["맛집", "카페", "음식"]):
            radius = 15
            preference = "food"
        else:
            radius = 20
            preference = "nature"

        return {
            "optimized_queries": [query],
            "inferred_preference": preference,
            "suggested_radius_km": radius,
            "content_types": ["12"],
            "location_strategy": "expand_suburban",
            "reasoning": "AI 분석 불가로 기본 휴리스틱 적용"
        }


# 전역 인스턴스
query_analyzer = QueryAnalyzer()
