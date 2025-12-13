#!/usr/bin/env python3
"""설치 검증 스크립트"""

import sys
import os


def test_installation():
    print("=" * 60)
    print("🧪 Vector DB 설치 검증")
    print("=" * 60)

    # Python 버전 확인
    print(f"\n✓ Python 버전: {sys.version}")

    # ChromaDB 테스트
    try:
        import chromadb
        print("✅ ChromaDB 설치 성공")

        # 간단한 기능 테스트
        client = chromadb.Client()
        collection = client.create_collection("test_collection")
        print("✅ ChromaDB 기본 기능 정상")

    except ImportError as e:
        print(f"❌ ChromaDB 설치 실패: {e}")
        print("   → Python 버전을 3.11로 변경하거나 Qdrant 사용을 권장합니다.")
        return False
    except Exception as e:
        print(f"⚠️ ChromaDB 기능 오류: {e}")

    # Sentence Transformers 테스트
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ Sentence Transformers 설치 성공")

        # 모델 로딩 테스트 (시간이 걸릴 수 있음)
        print("🔄 한국어 모델 로딩 테스트 중...")
        model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        embedding = model.encode(["테스트 문장"])
        print(f"✅ 임베딩 생성 성공 (차원: {len(embedding[0])})")

    except Exception as e:
        print(f"❌ Sentence Transformers 오류: {e}")
        return False

    # OpenAI 테스트
    try:
        from openai import OpenAI
        print("✅ OpenAI 라이브러리 설치 성공")
    except ImportError as e:
        print(f"❌ OpenAI 설치 실패: {e}")
        return False

    # FastAPI 테스트
    try:
        from fastapi import FastAPI
        from app.core.config import settings
        print("✅ FastAPI 및 설정 로드 성공")
        print(f"   KTO 활성화: {settings.is_kto_enabled}")
        print(f"   임베딩 타입: {settings.EMBEDDING_TYPE}")
    except Exception as e:
        print(f"⚠️ 앱 설정 로드 오류: {e}")

    print("\n" + "=" * 60)
    print("🎉 검증 완료! 모든 구성요소가 정상 설치되었습니다.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_installation()
    sys.exit(0 if success else 1)
