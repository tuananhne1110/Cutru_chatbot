from typing import List, Dict, Any, Optional
from .base import BaseRetriever
from .vector_retriever import VectorRetriever
from ..rerankers.base import BaseReranker
from qdrant_client.models import Filter

class HybridRetriever(BaseRetriever):
    """Hybrid retriever với vector search + reranking"""
    
    def __init__(self, vector_retriever: VectorRetriever, reranker: BaseReranker):
        self.vector_retriever = vector_retriever
        self.reranker = reranker
    
    def initialize(self) -> bool:
        """Khởi tạo hybrid retriever"""
        try:
            success = self.vector_retriever.initialize() and self.reranker.initialize()
            if success:
                # self.logger.info("HybridRetriever đã sẵn sàng")
                pass
            return success
        except Exception as e:
            # self.logger.error(f"Lỗi khởi tạo HybridRetriever: {e}")
            return False
    
    def retrieve(self, query: str, collection_name: str,  limit: int = 10, filters: Optional[Filter] = None) -> List[Dict[str, Any]]:
        """Retrieve với vector search + reranking"""
        try:
            # Lấy nhiều kết quả hơn để rerank
            vector_limit = limit
            vector_results = self.vector_retriever.retrieve(query, collection_name,vector_limit, filters)
            
            if not vector_results:
                return []
            
            # Chuẩn bị documents cho reranking
            documents = []
            for result in vector_results:
                content = result.get("payload", {}).get("content", "")
                documents.append(content)
            
            # Rerank
            reranked_results = self.reranker.rerank(query, documents, top_k=limit)
            
            # Kết hợp kết quả
            final_results = []
            for doc, score in reranked_results:
                # Tìm document gốc
                for result in vector_results:
                    if result.get("payload", {}).get("content") == doc:
                        result["rerank_score"] = score
                        final_results.append(result)
                        break
            
            # self.logger.info(f"Rerank được {len(final_results)} kết quả cho query: {query}")
            return final_results
        except Exception as e:
            # self.logger.error(f"Lỗi hybrid retrieve: {e}")
            return []
        

