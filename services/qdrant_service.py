from config import qdrant_client

def search_qdrant(collection_name, query_embedding, limit=20):
    return qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=limit
    ) 