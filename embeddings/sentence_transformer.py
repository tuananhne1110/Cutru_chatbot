from typing import List, Union
from sentence_transformers import SentenceTransformer
from .base import BaseEmbedding
from config.configs import EmbeddingModelConfig

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

        
            if isinstance(texts, str):
                result = self.model.encode(texts.lower(), normalize_embeddings=normalize, prompt_name=self.config.prompt_name)
                return result.tolist()
            else:
                results = self.model.encode([t.lower() for t in texts], normalize_embeddings=normalize, prompt_name=self.config.prompt_name)
                return [r.tolist() for r in results]
            

        except Exception as e:
            print(f"Lỗi encode: {e}")
            return [] if isinstance(texts, str) else [[]]
    
    def get_dimension(self) -> int:
        """Lấy dimension của embedding"""
        if not self.model:
            raise RuntimeError("Model chưa được khởi tạo")
        return self.model.get_sentence_embedding_dimension()