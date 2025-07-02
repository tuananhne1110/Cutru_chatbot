from sentence_transformers import SentenceTransformer
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Global embedding model instance
_embedding_model = None

def get_embedding_model():
    """Get global embedding model instance"""
    global _embedding_model
    if _embedding_model is None:
        try:
            logger.info("Loading Vietnamese PhoBERT embedding model...")
            _embedding_model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
            logger.info("Vietnamese PhoBERT embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _embedding_model

def get_embedding(text: str):
    """
    Generate embedding for Vietnamese text
    
    Args:
        text: Vietnamese text to embed
        
    Returns:
        numpy.ndarray: Embedding vector
    """
    model = get_embedding_model()
    return model.encode([text])[0] 