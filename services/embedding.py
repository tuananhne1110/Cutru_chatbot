import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.app_config import embedding_model


def get_embedding(text: str):
    """Lấy embedding từ model đã cấu hình."""
    return embedding_model.encode(text, show_progress_bar=False).tolist()