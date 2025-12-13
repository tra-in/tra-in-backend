#!/usr/bin/env python3
"""
한국관광공사 데이터 임베딩 실행 스크립트
"""
from app.core.config import settings
from app.services.kto_ingestion import KTOIngestionService
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    print("한국관광공사 데이터 임베딩 시작")
    print("=" * 60)
    print(f"DB 경로: {settings.VECTOR_DB_PATH}")
    print(f"임베딩 타입: {settings.EMBEDDING_TYPE}")
    print(f"배치 크기: {settings.BATCH_SIZE}")
    print("=" * 60)

    try:
        # 서비스 초기화
        ingestion_service = KTOIngestionService()

        # 전체 임베딩 실행
        ingestion_service.run_full_ingestion()

        print("\n모든 작업이 성공적으로 완료되었습니다!")
        print(f"데이터가 {settings.VECTOR_DB_PATH}에 저장되었습니다.")

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("환경 설정(.env 파일)을 확인해주세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
