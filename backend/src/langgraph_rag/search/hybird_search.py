from typing import List, Dict, Any, Optional
from .vector_search import VectorRetriever
from qdrant_client.models import Filter
from ..reranker.bge_reranker import BGEReranker
from ..utils.logger_utils import get_logger


logger = get_logger(__name__)
class HybridRetriever:
    """Hybrid retriever với vector search + reranking"""
    
    def __init__(self, vector_retriever: VectorRetriever, reranker: BGEReranker):
        self.vector_retriever = vector_retriever
        self.reranker = reranker
    
    
    def retrieve(self, query: str, collection_name: str,  limit: int = 10, top_k = 5, filters: Optional[Filter] = None) -> List[Dict[str, Any]]:
        """Retrieve với vector search + reranking"""
        try:
            # Lấy nhiều kết quả hơn để rerank
            vector_results = self.vector_retriever.retrieve(query=query, collection_name=collection_name, limit=limit, filters=filters)
            
            if not vector_results:
                return []
            
            if "question" in vector_results[0]['payload'].keys() and "answer" in vector_results[0]['payload'].keys():
                return vector_results

            # Chuẩn bị documents cho reranking
            documents = []
            for result in vector_results:
                content = result.get("payload", {}).get("content", "")
                documents.append(content)
            
            # Rerank
            reranked_results = self.reranker.rerank(query, documents, top_k=top_k)
            
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
            logger.error(f"Lỗi hybrid retrieve: {e}")
            return []
        

# run: python -m backend.src.langgraph_rag.search.hybird_search
if __name__ == "__main__":
    from ..embeddings.qwen_embedding_model import QwenEmbeddingModel
    from ..database.qdrant_client import QdrantDatabase
    from ..utils.config_utils import BaseConfig
    global_config = BaseConfig()
    embedd = QwenEmbeddingModel(global_config=global_config)
    qdrant_db = QdrantDatabase(global_config=global_config)
    retrieval = VectorRetriever(embedding=embedd, database= qdrant_db)
    bge_ranker = BGEReranker(global_config=global_config)
    hybird = HybridRetriever(vector_retriever=retrieval, reranker= bge_ranker)
    response = hybird.retrieve(
        query="Thủ tục đăng ký tạm trú gồm những giấy tờ gì?", 
        collection_name="legal",
        filters=None, 
        limit=10,
        top_k=5
        )
    

    print("📨 Response:", response)