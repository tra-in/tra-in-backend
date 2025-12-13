from typing import List, Dict, Optional
from app.core.config import settings
from app.core.vector_db import vector_db


class TourismSearchService:
    """관광지 검색 전용 서비스"""

    def __init__(self):
        self.collection = vector_db.get_collection()

    def search(
        self,
        query: str,
        n_results: int = 10,
        area_code: Optional[str] = None,
        content_type: Optional[str] = None,
        include_distances: bool = True
    ) -> Dict:
        """의미 기반 관광지 검색"""

        # 필터 조건 구성
        where_filter = {}
        if area_code:
            where_filter["areacode"] = area_code
        if content_type:
            where_filter["contenttypeid"] = content_type

        try:
            # 검색 실행
            if settings.EMBEDDING_TYPE == "korean":
                query_embedding = vector_db.generate_embedding(query)
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_filter if where_filter else None,
                    include=['documents', 'metadatas', 'distances']
                )
            else:
                # 기본 텍스트 검색
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_filter if where_filter else None,
                    include=['documents', 'metadatas', 'distances']
                )

            # 결과 포맷팅
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    item = {
                        "id": results['ids'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "document": results['documents'][0][i]
                    }

                    if include_distances and 'distances' in results:
                        item["similarity_score"] = 1 - \
                            results['distances'][0][i]  # 거리를 유사도로 변환

                    formatted_results.append(item)

            return {
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "filters_applied": where_filter
            }

        except Exception as e:
            print(f"검색 실패: {e}")
            return {
                "query": query,
                "total_results": 0,
                "results": [],
                "error": str(e)
            }

    def get_recommendations_for_chat(self, user_query: str, n_results: int = 3) -> str:
        """AI 채팅용 컨텍스트 생성"""
        search_results = self.search(user_query, n_results)

        if not search_results["results"]:
            return "관련 관광지 정보를 찾을 수 없습니다."

        context_parts = []
        for item in search_results["results"]:
            metadata = item["metadata"]

            # 핵심 정보만 추출
            title = metadata.get("title", "정보 없음")
            addr = metadata.get("addr1", "주소 정보 없음")
            category = metadata.get("cat2", metadata.get("cat1", ""))

            context = f"• {title} (위치: {addr}"
            if category:
                context += f", 분류: {category}"
            context += ")"

            context_parts.append(context)

        return "\n".join(context_parts)

    def get_stats(self) -> Dict:
        """검색 서비스 통계"""
        return {
            "total_items": self.collection.count(),
            "embedding_type": settings.EMBEDDING_TYPE,
            "collection_name": settings.VECTOR_DB_COLLECTION
        }


# 전역 인스턴스
tourism_search = TourismSearchService()
