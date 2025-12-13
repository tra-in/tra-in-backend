import math
import time
import requests
from typing import List, Dict, Optional
from tqdm import tqdm

from app.core.config import settings
from app.core.vector_db import vector_db


class KTOIngestionService:
    """한국관광공사 데이터 수집 및 임베딩 서비스"""

    def __init__(self):
        self.base_url = f"{settings.KTO_API_BASE_URL}/areaBasedList2"
        self.service_key = settings.KTO_SERVICE_KEY
        self.collection = vector_db.get_collection()
        self.items_per_page = 1000

        if not self.service_key:
            raise ValueError("KTO_SERVICE_KEY가 설정되지 않았습니다.")

    def get_total_count(self) -> int:
        """전체 데이터 개수 조회"""
        params = {
            "serviceKey": self.service_key,
            "numOfRows": 1,
            "pageNo": 1,
            "MobileOS": "AND",
            "MobileApp": "train",
            "_type": "json"
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=settings.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            return int(data["response"]["body"]["totalCount"])
        except Exception as e:
            print(f"전체 개수 조회 실패: {e}")
            return 47543  # fallback

    def fetch_page_data(self, page_no: int, num_rows: int = 100) -> List[Dict]:
        """페이지별 데이터 가져오기 (재시도 로직 포함)"""
        params = {
            "serviceKey": self.service_key,
            "numOfRows": num_rows,
            "pageNo": page_no,
            "MobileOS": "AND",
            "MobileApp": "train",
            "_type": "json"
        }

        for attempt in range(settings.MAX_RETRIES):
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=settings.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                # 응답 데이터 정규화
                items = data["response"]["body"].get(
                    "items", {}).get("item", [])
                if isinstance(items, dict):
                    items = [items]

                return items

            except Exception as e:
                if attempt == settings.MAX_RETRIES - 1:
                    print(f"페이지 {page_no} 최종 실패: {e}")
                    return []
                else:
                    wait_time = 2 ** attempt
                    print(
                        f"페이지 {page_no} 재시도 {attempt + 1}/{settings.MAX_RETRIES} (대기: {wait_time}초)")
                    time.sleep(wait_time)

        return []

    def create_searchable_text(self, item: Dict) -> str:
        """검색 최적화된 텍스트 생성"""
        parts = []

        # 제목 (최우선)
        title = item.get("title", "").strip()
        if title:
            parts.append(f"제목: {title}")

        # 주소 정보
        addr1 = item.get("addr1", "").strip()
        addr2 = item.get("addr2", "").strip()
        if addr1:
            full_addr = f"{addr1} {addr2}".strip()
            parts.append(f"주소: {full_addr}")

        # 카테고리 계층
        categories = []
        for i in range(1, 4):
            cat = item.get(f"cat{i}", "").strip()
            if cat:
                categories.append(cat)

        if categories:
            parts.append(f"분류: {' > '.join(categories)}")

        # 연락처
        tel = item.get("tel", "").strip()
        if tel:
            parts.append(f"전화: {tel}")

        return " | ".join(parts)

    def prepare_metadata(self, item: Dict) -> Dict:
        """메타데이터 정제"""
        important_fields = [
            "contentid", "title", "addr1", "addr2", "areacode",
            "sigungucode", "contenttypeid", "mapx", "mapy",
            "tel", "firstimage", "zipcode", "cat1", "cat2", "cat3",
            "modifiedtime", "createdtime"
        ]

        metadata = {}
        for field in important_fields:
            value = item.get(field, "")
            if value and str(value).strip():  # 빈 값 제외
                metadata[field] = str(value).strip()

        return metadata

    def process_batch(self, items: List[Dict]) -> bool:
        """배치 단위 처리 및 저장"""
        if not items:
            return True

        try:
            ids = []
            documents = []
            metadatas = []
            embeddings = []

            for item in items:
                content_id = item.get("contentid")
                if not content_id:
                    continue

                # 데이터 준비
                doc_text = self.create_searchable_text(item)
                if not doc_text.strip():
                    continue

                ids.append(str(content_id))
                documents.append(doc_text)
                metadatas.append(self.prepare_metadata(item))

                # 임베딩 생성
                if settings.EMBEDDING_TYPE == "korean":
                    embedding = vector_db.generate_embedding(doc_text)
                    embeddings.append(embedding)

            if not ids:
                return True

            # ChromaDB에 저장
            if embeddings and settings.EMBEDDING_TYPE == "korean":
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                # 기본 임베딩 사용
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )

            return True

        except Exception as e:
            print(f"배치 처리 실패: {e}")
            return False

    def run_full_ingestion(self):
        """전체 데이터 수집 및 임베딩 실행"""
        # 기본 정보 수집
        total_count = self.get_total_count()
        total_pages = math.ceil(total_count / self.items_per_page)

        print(f"전체 데이터: {total_count:,}개")
        print(f"총 페이지: {total_pages}페이지")
        print(f"임베딩 방식: {settings.EMBEDDING_TYPE}")
        print(f"배치 크기: {settings.BATCH_SIZE}")
        print("=" * 60)

        # 기존 데이터 확인
        existing_count = self.collection.count()
        if existing_count > 0:
            print(f"기존 데이터: {existing_count:,}개")
            choice = input("기존 데이터를 삭제하고 새로 시작하시겠습니까? (y/N): ")
            if choice.lower() == 'y':
                vector_db.reset_collection()
                self.collection = vector_db.get_collection()
                print("기존 데이터 삭제 완료\n")

        # 데이터 처리
        buffer = []
        processed_count = 0
        failed_pages = []

        with tqdm(total=total_count, desc="데이터 처리", unit="개") as pbar:
            for page_no in range(1, total_pages + 1):
                # API 요청
                items = self.fetch_page_data(page_no, self.items_per_page)

                if not items:
                    failed_pages.append(page_no)
                    continue

                buffer.extend(items)

                # 배치 크기에 도달하면 처리
                while len(buffer) >= settings.BATCH_SIZE:
                    batch = buffer[:settings.BATCH_SIZE]
                    buffer = buffer[settings.BATCH_SIZE:]

                    if self.process_batch(batch):
                        processed_count += len(batch)
                        pbar.update(len(batch))
                    else:
                        # 실패한 배치 재시도를 위해 버퍼에 다시 추가
                        buffer = batch + buffer
                        time.sleep(5)

                # API 요청 간격 (rate limiting 방지)
                time.sleep(0.2)

        # 남은 데이터 처리
        if buffer:
            if self.process_batch(buffer):
                processed_count += len(buffer)

        # 결과 출력
        final_count = self.collection.count()
        print(f"\n처리 완료!")
        print(f"성공: {processed_count:,}개")
        print(f"DB 저장: {final_count:,}개")
        if failed_pages:
            print(f"실패한 페이지: {len(failed_pages)}개 - {failed_pages[:10]}...")
