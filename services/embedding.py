from sentence_transformers import SentenceTransformer

# Khởi tạo model embedding mới
embedding_model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)

def get_embedding(text):
    return embedding_model.encode(text, show_progress_bar=False).tolist() 