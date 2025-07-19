import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sử dụng model từ app_config thay vì tạo mới
from config.app_config import embedding_model

def get_embedding(text):
    return embedding_model.encode(text, show_progress_bar=False).tolist() 