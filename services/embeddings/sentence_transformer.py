from typing import List, Union
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbedding:
    """SentenceTransformer embedding implementation"""
    
    def __init__(self, model_name: str = "Alibaba-NLP/gte-multilingual-base", trust_remote_code: bool = True, device: str = "cpu"):
        self.model_name = model_name
        self.trust_remote_code = trust_remote_code
        self.device = device
        self.model = None
        self._initialize()

    def _initialize(self)-> None:
        """Khởi tạo mô hình SentenceTransformer."""
        self.model = SentenceTransformer(
            model_name_or_path=self.model_name,
            trust_remote_code=self.trust_remote_code,
            device=self.device
        )

    def _check_model(self) -> None:
        """Kiểm tra model đã được khởi tạo chưa."""
        if self.model is None:
            raise RuntimeError("Model chưa được khởi tạo.")
        
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> Union[List[float], List[List[float]]]:
        """Encode text thành vector"""
        self._check_model()
        try:
            if isinstance(texts, str):
                result = self.model.encode(texts.lower(), normalize_embeddings=normalize)
                return result.tolist()
            else:
                results = self.model.encode([t.lower() for t in texts], normalize_embeddings=normalize)
                return [r.tolist() for r in results]
        except Exception as e:
            self.logger.error(f"Lỗi encode: {e}")
            return [] if isinstance(texts, str) else [[]]
    
    def get_dimension(self) -> int:
        """Lấy dimension của embedding"""
        if not self.model:
            raise RuntimeError("Model chưa được khởi tạo")
        return self.model.get_sentence_embedding_dimension()
    
