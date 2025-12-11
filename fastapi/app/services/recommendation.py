# app/services/recommendation.py
import openai
import json
from fastapi import HTTPException

from app.core.config import OPENAI_API_KEY
from app.schemas.travel import UserRequest

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY


async def get_travel_recommendations(request: UserRequest) -> list:
    """OpenAI API를 호출하여 여행지 추천 목록을 생성하는 서비스 함수"""
    try:
        # OpenAI에 전달할 프롬프트 생성
        prompt = f"""
        당신은 최고의 여행 전문가입니다. 사용자의 위치와 선호도를 기반으로 여행 계획을 추천해주세요.
        응답은 반드시 'recommendations'라는 키를 가진 JSON 객체여야 하며, 그 값은 JSON 배열이어야 합니다.
        배열의 각 객체는 'place_name', 'latitude', 'longitude', 'description' 키를 가져야 합니다.
        위도(latitude)와 경도(longitude)는 float 형태로 제공해주세요.

        - 사용자 위치: 위도 {request.latitude}, 경도 {request.longitude}
        - 선호 여행 타입: '{request.travel_type}'
        - 추천 장소 개수: 3곳
        - 참고: 모든 장소는 한국 카카오맵에서 검색이 가능한 실제 장소여야 합니다.
        """

        # OpenAI Chat Completions API 호출
        response = openai.chat.completions.create(
            model="gpt-5-mini",  # 또는 "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant that provides recommendations in a structured JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},  # JSON 형식 응답 강제
            # temperature=1, 모델 특성상 temperature 적용 안됨
        )

        # API 응답 파싱
        response_content = response.choices[0].message.content
        data = json.loads(response_content)

        # 프롬프트에서 요청한 'recommendations' 키로 데이터 추출
        recommended_places = data.get("recommendations", [])

        if not recommended_places:
            raise HTTPException(status_code=404, detail="추천 장소를 생성하지 못했습니다.")

        return recommended_places

    except openai.APIError as e:
        # OpenAI API 관련 에러 처리
        raise HTTPException(status_code=500, detail=f"OpenAI API 에러: {e}")
    except (json.JSONDecodeError, TypeError) as e:
        # JSON 파싱 또는 데이터 형식 관련 에러 처리
        raise HTTPException(status_code=500, detail=f"API 응답 처리 중 에러 발생: {e}")
    except Exception as e:
        # 기타 예외 처리
        raise HTTPException(status_code=500, detail=f"알 수 없는 에러 발생: {e}")
