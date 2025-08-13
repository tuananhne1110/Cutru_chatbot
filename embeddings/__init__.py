from .base import BaseEmbedding
from .sentence_transformer import SentenceTransformerEmbedding
from .bedrock_embeddings import BedrockEmbedding
from config import settings

def get_embedding_model(embedding_type: str = None) -> BaseEmbedding:
    """Factory function để tạo embedding model dựa trên config"""
    if embedding_type is None:
        # Lấy embedding type từ config
        embedding_config = settings.retrieval_settings.embedding_config
        # Kiểm tra xem có phải Bedrock Titan không
        if hasattr(embedding_config, 'model_id') and embedding_config.model_id and 'titan' in embedding_config.model_id.lower():
            embedding_type = 'bedrock'
        else:
            embedding_type = 'sentence_transformer'
    
    if embedding_type == 'bedrock':
        model = BedrockEmbedding(settings.retrieval_settings.embedding_config)
    else:
        model = SentenceTransformerEmbedding(settings.retrieval_settings.embedding_config)
    
    if not model.initialize():
        raise RuntimeError(f"Không thể khởi tạo embedding model: {embedding_type}")
    
    return model

# Global embedding model instance
_embedding_model = None

def get_embedding(text: str):
    """Lấy embedding từ model đã cấu hình."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = get_embedding_model()
    
    return _embedding_model.encode(text)

__all__ = [
    'BaseEmbedding',
    'SentenceTransformerEmbedding', 
    'BedrockEmbedding',
    'get_embedding_model',
    'get_embedding'
]
