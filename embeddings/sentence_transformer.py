from typing import List, Union
from sentence_transformers import SentenceTransformer
from .base import BaseEmbedding
from config.configs import EmbeddingModelConfig
from utils.text_utils import normalize_vietnamese_text

class SentenceTransformerEmbedding(BaseEmbedding):
    """SentenceTransformer embedding implementation"""
    
    def __init__(self, config: EmbeddingModelConfig):
        self.config = config
        self.model = None
    
    def initialize(self) -> bool:
        """Khởi tạo model"""
        try:
            
            if self.config.trust_remote_code:
                self.model = SentenceTransformer(
                    self.config.model_name,
                    trust_remote_code=self.config.trust_remote_code,
                    device=self.config.device
                )
            else :

                self.model = SentenceTransformer(
                    self.config.model_name,
                    device=self.config.device
                )
            # self.logger.info(f"Đã tải embedding model: {self.config.model_name}")

            return True
        except Exception as e:
            # self.logger.error(f"Lỗi tải embedding model: {e}")
            return False
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> Union[List[float], List[List[float]]]:
        """Encode text thành vector"""
        

        if not self.model:
            raise RuntimeError("Model chưa được khởi tạo")
        try:
            # Fix UTF-8 encoding for input texts
            if isinstance(texts, str):
                normalized_text = normalize_vietnamese_text(texts)
                result = self.model.encode(normalized_text.lower(), normalize_embeddings=normalize, prompt_name=self.config.prompt_name)
                return result.tolist()
            else:
                normalized_texts = [normalize_vietnamese_text(t) for t in texts]
                results = self.model.encode([t.lower() for t in normalized_texts], normalize_embeddings=normalize, prompt_name=self.config.prompt_name)
                return [r.tolist() for r in results]
            

        except Exception as e:
            print(f"Lỗi encode: {e}")
            return [] if isinstance(texts, str) else [[]]
    
    def get_dimension(self) -> int:
        """Lấy dimension của embedding"""
        if not self.model:
            raise RuntimeError("Model chưa được khởi tạo")
        return self.model.get_sentence_embedding_dimension()