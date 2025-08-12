import logging
import time
from typing import Dict, List

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

class BGEReranker:
    """Reranker sử dụng BGE transformers để tính điểm query-doc, khớp với logic bạn yêu cầu."""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        """Khởi tạo BGE reranker."""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load BGE reranker model."""
        try:
            logger.info(f"Loading BGE reranker model: {self.model_name}")
            start_time = time.time()
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            
            load_time = time.time() - start_time
            logger.info(f"BGE reranker loaded successfully in {load_time:.2f}s on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load BGE reranker: {e}")
            raise
    
    def rerank(self, 
               query: str, 
               documents: List[Dict], 
               top_k: int = 10,
               batch_size: int = 32) -> List[Dict]:
        """Rerank documents dựa trên query."""
        if not documents:
            return []
        
        if not self.model:
            logger.warning("BGE reranker model not loaded, returning original order")
            return documents[:top_k]
        
        try:
            start_time = time.time()
            
            pairs = []
            contents = []
            for doc in documents:
                content = doc.get('content', doc.get('text', ''))
                contents.append(content)
                pairs.append([query, content])

            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors='pt',
                max_length=512
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                scores = outputs.logits.view(-1).float().cpu().numpy()
            
            scored_docs = []
            for i, (doc, score, content) in enumerate(zip(documents, scores, contents)):
                doc_copy = doc.copy()
                doc_copy['content'] = content
                doc_copy['rerank_score'] = float(score)
                doc_copy['original_rank'] = i
                scored_docs.append(doc_copy)
            
            scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            reranked_docs = scored_docs[:top_k]
            
            for i, doc in enumerate(reranked_docs):
                doc['final_rank'] = i
                doc['rank_improvement'] = doc['original_rank'] - i
            
            rerank_time = time.time() - start_time
            logger.info(f"Reranked {len(documents)} documents in {rerank_time:.3f}s, returned top {len(reranked_docs)}")
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return documents[:top_k]
    
    def _extract_metadata_str(self, doc: Dict) -> str:
        """Trích xuất metadata thành chuỗi để dùng cho reranking."""
        metadata_parts = []
        
        if doc.get('law_name'):
            metadata_parts.append(f"Luật: {doc['law_name']}")
        if doc.get('article'):
            metadata_parts.append(f"Điều: {doc['article']}")
        if doc.get('chapter'):
            metadata_parts.append(f"Chương: {doc['chapter']}")
        if doc.get('form_name'):
            metadata_parts.append(f"Biểu mẫu: {doc['form_name']}")
        if doc.get('form_code'):
            metadata_parts.append(f"Mã biểu mẫu: {doc['form_code']}")
        if doc.get('term'):
            metadata_parts.append(f"Thuật ngữ: {doc['term']}")
        if doc.get('definition'):
            metadata_parts.append(f"Định nghĩa: {doc['definition']}")
        if doc.get('procedure_name'):
            metadata_parts.append(f"Thủ tục: {doc['procedure_name']}")
        if doc.get('procedure_code'):
            metadata_parts.append(f"Mã thủ tục: {doc['procedure_code']}")
        
        return " | ".join(metadata_parts) if metadata_parts else "Không có metadata"
    
    def get_rerank_stats(self, reranked_docs: List[Dict]) -> Dict:
        """Tính toán thống kê về hiệu quả reranking."""
        if not reranked_docs:
            return {}
        
        improvements = [doc.get('rank_improvement', 0) for doc in reranked_docs]
        avg_improvement = sum(improvements) / len(improvements)
        
        improved_count = sum(1 for imp in improvements if imp > 0)
        improvement_rate = improved_count / len(improvements)
        
        scores = [doc.get('rerank_score', 0) for doc in reranked_docs]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        return {
            'total_documents': len(reranked_docs),
            'improved_documents': improved_count,
            'improvement_rate': improvement_rate,
            'average_improvement': avg_improvement,
            'average_score': avg_score,
            'max_score': max_score,
            'min_score': min_score,
            'score_range': max_score - min_score
        }

# Global instance
bge_reranker = BGEReranker()
def get_reranker() -> BGEReranker:
    return bge_reranker 