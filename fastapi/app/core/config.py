
import os
import logging
import sys
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()


class Settings(BaseSettings):
    """
    AI Travel Chat 애플리케이션 설정
    기존 OpenAI 설정 + 새로운 KTO/Vector DB 설정 통합
    """

    # ==================== 기본 프로젝트 설정 ====================
    PROJECT_NAME: str = "AI Travel Chat"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")

    # ==================== OpenAI 설정 (기존 유지) ====================
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    OPENAI_TEMPERATURE: float = Field(default=0.7, env="OPENAI_TEMPERATURE")

    # ==================== KTO API 설정 ====================
    KTO_SERVICE_KEY: Optional[str] = Field(default=None, env="KTO_SERVICE_KEY")
    KTO_API_BASE_URL: str = Field(
        default="https://apis.data.go.kr/B551011/KorService2",
        env="KTO_API_BASE_URL"
    )

    # ==================== Vector DB 설정 ====================
    VECTOR_DB_PATH: str = Field(
        default="./data/kto_tourism_db", env="VECTOR_DB_PATH")
    VECTOR_DB_COLLECTION: str = Field(
        default="kto_tourism", env="VECTOR_DB_COLLECTION")
    # korean, openai, default
    EMBEDDING_TYPE: str = Field(default="korean", env="EMBEDDING_TYPE")

    # ==================== 성능 설정 ====================
    BATCH_SIZE: int = Field(default=50, env="BATCH_SIZE")
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")

    # ==================== 검색 설정 ====================
    DEFAULT_SEARCH_RESULTS: int = Field(
        default=10, env="DEFAULT_SEARCH_RESULTS")
    MAX_SEARCH_RESULTS: int = Field(default=50, env="MAX_SEARCH_RESULTS")

    # ==================== 로깅 설정 ====================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default="app.log", env="LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    # ==================== 검증 로직 ====================
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """기존 로직 유지: OpenAI API 키 필수 검증"""
        if not v or v.strip() == "":
            raise ValueError(
                "OpenAI API 키가 설정되지 않았습니다. "
                ".env 파일이나 환경 변수를 확인해주세요."
            )
        if not v.startswith("sk-"):
            raise ValueError("올바르지 않은 OpenAI API 키 형식입니다.")
        return v.strip()

    @field_validator("KTO_SERVICE_KEY")
    @classmethod
    def validate_kto_key(cls, v: Optional[str]) -> Optional[str]:
        """KTO 키 검증 - 경고만 출력하고 진행"""
        if not v:
            print("   경고: KTO_SERVICE_KEY가 설정되지 않았습니다.")
            print("   관광 데이터 수집 기능이 비활성화됩니다.")
            return None
        return v.strip()

    @field_validator("EMBEDDING_TYPE")
    @classmethod
    def validate_embedding_type(cls, v: str) -> str:
        """임베딩 타입 검증"""
        valid_types = ["korean", "openai", "default"]
        if v not in valid_types:
            raise ValueError(
                f"잘못된 EMBEDDING_TYPE: {v}. "
                f"허용된 값: {', '.join(valid_types)}"
            )
        return v

    @field_validator("BATCH_SIZE")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """배치 크기 검증"""
        if not 1 <= v <= 200:
            raise ValueError(f"BATCH_SIZE는 1-200 사이여야 합니다. 현재: {v}")
        return v

    # ==================== 유틸리티 메서드 ====================
    @property
    def is_kto_enabled(self) -> bool:
        """KTO 기능 활성화 여부"""
        return bool(self.KTO_SERVICE_KEY)

    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return not self.DEBUG

    def get_openai_config(self) -> dict:
        """OpenAI 클라이언트 설정"""
        return {
            "api_key": self.OPENAI_API_KEY,
            "model": self.OPENAI_MODEL,
            "temperature": self.OPENAI_TEMPERATURE
        }

    def get_kto_config(self) -> dict:
        """KTO API 설정"""
        return {
            "service_key": self.KTO_SERVICE_KEY,
            "base_url": self.KTO_API_BASE_URL,
            "timeout": self.REQUEST_TIMEOUT,
            "max_retries": self.MAX_RETRIES
        }

    def get_vector_db_config(self) -> dict:
        """Vector DB 설정"""
        return {
            "path": self.VECTOR_DB_PATH,
            "collection": self.VECTOR_DB_COLLECTION,
            "embedding_type": self.EMBEDDING_TYPE
        }

    def display_config(self):
        """현재 설정 출력 (개발용)"""
        print("=" * 60)
        print(f"{self.PROJECT_NAME} v{self.VERSION}")
        print("=" * 60)
        print(f"환경: {'프로덕션' if self.is_production else '개발'}")
        print(f"OpenAI: {'활성화' if self.OPENAI_API_KEY else '비활성화'}")
        print(f"KTO: {'활성화' if self.is_kto_enabled else '비활성화'}")
        print(f"임베딩: {self.EMBEDDING_TYPE}")
        print(f"Vector DB: {self.VECTOR_DB_PATH}")
        print(f"배치 크기: {self.BATCH_SIZE}")
        print("=" * 60)


# ==================== 설정 인스턴스 생성 ====================
try:
    settings = Settings()
except Exception as e:
    print(f"\n설정 로드 실패: {e}\n")
    print(".env 파일 예시:")
    print("OPENAI_API_KEY=sk-your-openai-key-here")
    print("KTO_SERVICE_KEY=your-kto-service-key-here")
    print("EMBEDDING_TYPE=korean")
    print("DEBUG=False")
    print()
    raise


# ==================== 기존 코드 호환성 유지 ====================
OPENAI_API_KEY = settings.OPENAI_API_KEY


# ==================== 로깅 설정 ====================
def setup_logging():
    """로깅 시스템 초기화"""
    # 기본 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택적)
    if settings.LOG_FILE:
        try:
            file_handler = logging.FileHandler(
                settings.LOG_FILE, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"파일 로깅 설정 실패: {e}")

    return logger


# 로거 초기화
logger = setup_logging()


# ==================== 개발 환경에서 설정 표시 ====================
if settings.DEBUG:
    settings.display_config()


# ==================== 유틸리티 함수 ====================
def get_settings() -> Settings:
    """FastAPI 의존성 주입용 설정 반환"""
    return settings


def validate_all_settings():
    """전체 설정 검증"""
    issues = []

    # OpenAI 키 재검증
    if not settings.OPENAI_API_KEY.startswith("sk-"):
        issues.append("OpenAI API 키 형식이 올바르지 않습니다")

    # KTO 키 길이 체크 (선택적)
    if settings.KTO_SERVICE_KEY and len(settings.KTO_SERVICE_KEY) < 50:
        issues.append("KTO Service Key가 너무 짧습니다")

    if issues:
        raise ValueError(
            "설정 검증 실패:\n" + "\n".join(f"  - {issue}" for issue in issues))

    return True


# ==================== 환경별 설정 (선택적 사용) ====================
class DevelopmentSettings(Settings):
    """개발 환경 전용 설정"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """프로덕션 환경 전용 설정"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    LOG_FILE: Optional[str] = None  # 프로덕션에서는 외부 로깅 시스템 사용


def get_settings_by_env(env: str = "development") -> Settings:
    """환경별 설정 반환"""
    if env.lower() == "production":
        return ProductionSettings()
    elif env.lower() == "development":
        return DevelopmentSettings()
    else:
        return Settings()


# ==================== 설정 테스트 (스크립트 실행시) ====================
if __name__ == "__main__":
    print("\n 설정 검증 테스트")
    print("-" * 40)

    try:
        # 전체 검증
        validate_all_settings()
        print("모든 설정 검증 통과")

        # 설정 정보 출력
        settings.display_config()

        # 설정 그룹 테스트
        print(f"\n OpenAI 설정: {settings.get_openai_config()}")
        print(f"KTO 설정: {settings.get_kto_config()}")
        print(f"Vector DB 설정: {settings.get_vector_db_config()}")

        print("\n설정 로드 완료!")

    except Exception as e:
        print(f"설정 검증 실패: {e}")
        raise
