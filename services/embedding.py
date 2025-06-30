from config import embedding_model

def get_embedding(text):
    return embedding_model.encode([text])[0] 