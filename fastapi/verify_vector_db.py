#!/usr/bin/env python3
"""Vector DB 무결성 검증 스크립트"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


def verify_vector_db():
    print("🔍 Vector DB 무결성 검증")
    print("=" * 50)

    # 1. 디렉토리 존재 확인
    db_path = Path("data/kto_tourism_db")
    if not db_path.exists():
        print("❌ Vector DB 디렉토리가 없습니다!")
        return False

    print(f"✅ Vector DB 디렉토리 존재: {db_path}")

    # 2. 파일 크기 확인
    total_size = sum(
        f.stat().st_size for f in db_path.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    print(f"📦 Vector DB 크기: {size_mb:.1f} MB")

    try:
        from app.core.config import settings
        from app.core.vector_db import vector_db

        print(f"🔧 임베딩 타입: {settings.EMBEDDING_TYPE}")

        # 3. 데이터 개수 및 타입 분석
        collection = vector_db.get_collection()
        count = collection.count()
        print(f"✅ 저장된 데이터: {count:,}개")

        # 4. 데이터 타입 분포 확인
        print("\n📊 데이터 타입 분석 (샘플 100개):")
        sample_results = collection.get(limit=100, include=['metadatas'])

        if sample_results and sample_results.get('metadatas'):
            type_stats = {}
            addr_count = 0

            for metadata in sample_results['metadatas']:
                content_type = metadata.get('contenttypeid', 'N/A')
                type_stats[content_type] = type_stats.get(content_type, 0) + 1

                if metadata.get('addr1') and metadata.get('addr1') != 'N/A':
                    addr_count += 1

            # 타입별 통계 출력
            type_names = {
                "12": "관광지", "14": "문화시설", "15": "축제공연행사",
                "25": "여행코스", "28": "레포츠", "32": "숙박",
                "38": "쇼핑", "39": "음식점"
            }

            for ctype, count in sorted(type_stats.items(), key=lambda x: -x[1]):
                type_name = type_names.get(ctype, "기타")
                percentage = (count / len(sample_results['metadatas'])) * 100
                print(
                    f"   타입 {ctype} ({type_name}): {count}개 ({percentage:.1f}%)")

            print(f"   주소 정보 있음: {addr_count}/100 ({addr_count}%)")

        # 5. 관광지만 검색 테스트 (🔑 핵심 수정)
        print(f"\n🧪 관광지 검색 테스트:")
        print("-" * 50)

        query_text = "서울 관광지"

        if settings.EMBEDDING_TYPE == "korean" and vector_db.model:
            query_embedding = vector_db.generate_embedding(query_text)

            # ✅ 관광지(12)만 필터링하여 검색
            test_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                where={"contenttypeid": "12"},  # 🔑 관광지만 검색
                include=['metadatas', 'documents', 'distances']
            )

            if test_results and test_results.get('ids') and test_results['ids'][0]:
                result_count = len(test_results['ids'][0])
                print(f"✅ 관광지 검색 성공: {result_count}개 결과")

                print("\n📍 관광지 검색 결과:")
                for i, metadata in enumerate(test_results['metadatas'][0], 1):
                    title = metadata.get('title', 'N/A')
                    addr = metadata.get('addr1', 'N/A')
                    content_type = metadata.get('contenttypeid', 'N/A')

                    # ✅ 거리 값 직접 표시 (변환 없음)
                    distance = test_results['distances'][0][i-1]

                    print(f"   {i}. [{content_type}] {title}")
                    print(f"      📍 {addr}")
                    print(f"      📏 거리: {distance:.3f} (낮을수록 유사)")
            else:
                print("⚠️ 관광지 타입 데이터가 부족합니다.")

                # 대안: 전체 검색 (타입 무관)
                print("\n🔄 전체 데이터 검색 시도:")
                all_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3,
                    include=['metadatas', 'distances']
                )

                if all_results and all_results.get('metadatas'):
                    for i, metadata in enumerate(all_results['metadatas'][0], 1):
                        title = metadata.get('title', 'N/A')
                        content_type = metadata.get('contenttypeid', 'N/A')
                        type_name = type_names.get(content_type, "기타")
                        distance = all_results['distances'][0][i-1]

                        print(f"   {i}. [{content_type}-{type_name}] {title}")
                        print(f"      📏 거리: {distance:.3f}")

        # 6. API 사용법 안내
        print(f"\n💡 올바른 API 사용법:")
        print(f"   # 관광지만 검색")
        print(f"   curl 'http://localhost:8000/travel/search/simple?q=서울&type=12'")
        print(f"   ")
        print(f"   # 음식점만 검색")
        print(f"   curl 'http://localhost:8000/travel/search/simple?q=서울 맛집&type=39'")

        print(f"\n🎉 Vector DB 검증 완료!")
        return True

    except Exception as e:
        print(f"❌ Vector DB 로드 실패: {e}")
        import traceback
        traceback.print_exc()

        print(f"\n🔧 해결 방법:")
        print(f"1. 환경변수 확인: .env에서 EMBEDDING_TYPE=korean")
        print(f"2. 서버 재시작: uvicorn app.main:app --reload")
        return False


if __name__ == "__main__":
    success = verify_vector_db()

    print(f"\n{'='*50}")
    if success:
        print("✅ 검증 완료! 관광지 중심 검색 사용 가능")
        print("🚀 서버 실행: uvicorn app.main:app --reload")
    else:
        print("❌ 검증 실패. 위의 해결 방법을 시도해보세요.")

    sys.exit(0 if success else 1)
