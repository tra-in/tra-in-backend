import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
from sentence_transformers import SentenceTransformer

from app.core.config import settings


class VectorDBManager:
    """Vector DB 싱글톤 관리자 - 리소스 최적화"""

    _instance: Optional['VectorDBManager'] = None
    _client: Optional[chromadb.PersistentClient] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize()

    def _initialize(self):
        """DB 클라이언트와 임베딩 모델 초기화"""
        print("Vector DB 초기화 중...")

        # 디렉토리 생성
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

        # ChromaDB 클라이언트 초기화
        self._client = chromadb.PersistentClient(
            path=settings.VECTOR_DB_PATH,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
        )

        # 임베딩 모델 초기화 (한 번만 로딩)
        if settings.EMBEDDING_TYPE == "korean":
            print("한국어 임베딩 모델 로딩 중...")
            self._model = SentenceTransformer('jhgan/ko-sroberta-multitask')
            print("한국어 모델 로딩 완료")

        print("Vector DB 초기화 완료")

    @property
    def client(self) -> chromadb.PersistentClient:
        """클라이언트 인스턴스 반환"""
        if self._client is None:
            self._initialize()
        return self._client

    @property
    def model(self) -> Optional[SentenceTransformer]:
        """임베딩 모델 반환"""
        return self._model

    def get_collection(self, name: Optional[str] = None):
        """컬렉션 가져오기 또는 생성"""
        collection_name = name or settings.VECTOR_DB_COLLECTION
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "source": "KTO_API",
                "embedding_type": settings.EMBEDDING_TYPE,
                "version": "1.0"
            }
        )

    def reset_collection(self, name: Optional[str] = None) -> bool:
        """컬렉션 초기화"""
        collection_name = name or settings.VECTOR_DB_COLLECTION
        try:
            self.client.delete_collection(name=collection_name)
            return True
        except Exception as e:
            print(f"컬렉션 삭제 실패: {e}")
            return False

    def generate_embedding(self, text: str) -> list:
        """텍스트 임베딩 생성"""
        if settings.EMBEDDING_TYPE == "korean" and self._model:
            return self._model.encode([text])[0].tolist()
        elif settings.EMBEDDING_TYPE == "openai":
            # OpenAI 임베딩 로직 추가 가능
            pass
        return []


# 전역 싱글톤 인스턴스
vector_db = VectorDBManager()
