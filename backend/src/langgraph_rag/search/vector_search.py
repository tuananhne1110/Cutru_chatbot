from typing import List, Dict, Any, Optional
from qdrant_client.models import Filter
from ..embeddings.qwen_embedding_model import QwenEmbeddingModel
from ..database.qdrant_client import QdrantDatabase
from ..utils.logger_utils import get_logger


logger = get_logger(__name__)

class VectorRetriever:
    """Vector search retriever"""
    
    def __init__(self, database: QdrantDatabase, embedding: QwenEmbeddingModel):
        self.database = database
        self.embedding = embedding
    
    def retrieve(self, query: str, collection_name: str,  limit: int = 10, threshold: float = 0.9, filters: Optional[Filter] = None) -> List[Dict[str, Any]]:
        """Retrieve documents bằng vector search"""
        try:
            # Encode query
            query_vector = self.embedding.batch_encode(query.lower()) # text to list[float] or list[list[float]]

            # # qdrant cache
            # result_cache = self.database.search(
            #     query_vector=query_vector,
            #     collection_name="qdrant_cache",
            #     limit=1,
            #     with_vectors=True
            # )

            # if result_cache[0]["score"] >= threshold:
            #     return result_cache


            # Search
            results = self.database.search(
                query_vector=query_vector,
                collection_name=collection_name,
                limit=limit,
                filters=filters
            )

            logger.info(f"Tìm được {len(results)} kết quả cho query: {query}")

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
            logger.error(f"Lỗi retrieve: {e}")
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
    #         query_vector = self.embedding.batch_encode(query)
    #         print(f"[DEBUG] query_vector: {len(query_vector)}")

    #         # Search
    #         results = self.database.search(
    #             query_vector=query_vector,
    #             collection_name=collection_name,
    #             limit=limit,
    #             filters=filters
    #         )

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



# # run: python -m src.langgraph_rag.search.vector_search
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     embedd = QwenEmbeddingModel(global_config=global_config)
#     qdrant_db = QdrantDatabase(global_config=global_config)
#     retrieval = VectorRetriever(embedding=embedd, database= qdrant_db)

#     response = retrieval.retrieve(query="Thủ tục đăng ký tạm trú gồm những giấy tờ gì?", collection_name="qdrant_cache")

#     print("📨 Response:", response)
