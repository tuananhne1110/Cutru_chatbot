from typing import List, Dict, Any, Optional
from .base import BaseRetriever
from ..database.base import BaseDatabase
from ..embeddings.base import BaseEmbedding
from qdrant_client.models import Filter

class VectorRetriever(BaseRetriever):
    """Vector search retriever"""
    
    def __init__(self, database: BaseDatabase, embedding: BaseEmbedding):
        self.database = database
        self.embedding = embedding
    
    def initialize(self) -> bool:
        pass
    
    def retrieve(self, query: str, collection_name: str,  limit: int = 10, filters: Optional[Filter] = None) -> List[Dict[str, Any]]:
        """Retrieve documents bằng vector search"""
        try:
            # Encode query
            query_vector = self.embedding.encode(query) # text to list[float] or list[list[float]]

            # Search
            results = self.database.search(
                query_vector=query_vector,
                collection_name=collection_name,
                limit=limit,
                filters=filters
            )

            # self.logger.info(f"Tìm được {len(results)} kết quả cho query: {query}")

            if filters is not None and len(results) == 0:
                results = self.database.search(
                    query_vector=query_vector,
                    collection_name=collection_name,
                    limit=limit,
                    filters=None
                )
                # self.logger.info(f"Tiếp tục tìm kiếm lại và KHÔNG dùng FILTER, tìm được  {len(results)} kết quả cho query: {query} ")
            return results
        except Exception as e:
            # self.logger.error(f"Lỗi retrieve: {e}")
            return []

    # def retrieve(self, query: str, collection_name: str,  limit: int = 10, filters: Optional[Filter] = None) -> List[Dict[str, Any]]:
    #     """Retrieve documents bằng vector search"""
    #     from traceback import print_exc

    #     try:
    #         print(f"[DEBUG] query: {query}")
    #         print(f"[DEBUG] collection_name: {collection_name}")
    #         print(f"[DEBUG] limit: {limit}")
    #         print(f"[DEBUG] filters: {filters}")

    #         # Encode query
    #         query_vector = self.embedding.encode(query)
    #         print(f"[DEBUG] query_vector: {query_vector[:5]}...")  # In 5 số đầu để tránh quá dài

    #         # Search
    #         results = self.database.search(
    #             query_vector=query_vector,
    #             collection_name=collection_name,
    #             limit=limit,
    #             filters=filters
    #         )

    #         print(f"[DEBUG] Kết quả tìm kiếm (filters): {len(results)}")

    #         if filters is not None and len(results) == 0:
    #             print("[DEBUG] Không có kết quả với filter, thử lại không dùng filter")
    #             results = self.database.search(
    #                 query_vector=query_vector,
    #                 collection_name=collection_name,
    #                 limit=limit,
    #                 filters=None
    #             )
    #             print(f"[DEBUG] Kết quả tìm kiếm (no filter): {len(results)}")

    #         return results

    #     except Exception as e:
    #         print(f"[ERROR] Lỗi trong retrieve: {e}")
    #         print_exc()
    #         return []
