import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.app_config import embedding_model


def get_embedding(text: str):
    """Lấy embedding từ model đã cấu hình."""
    return embedding_model.encode(text, prompt_name="query").tolist()

# # import sys
# # import os
# # sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # # Sử dụng model từ app_config thay vì tạo mới
# # from config.app_config import embedding_model
# # from embeddings.bedrock_embeddings import BedrockEmbedding, BedrockEmbeddingConfig
# from services.embeddings.bedrock_embeddings import BedrockEmbedding, BedrockEmbeddingConfig


# config = BedrockEmbeddingConfig(
#     model_id="amazon.titan-embed-text-v2:0",
#     output_dimension=1024,
#     normalize=True, 
#     region_name="us-east-1"
# )
# embedder = BedrockEmbedding(config)

# def get_embedding(text):
#     return embedder.encode(text)