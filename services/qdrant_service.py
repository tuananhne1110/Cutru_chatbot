import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_config import qdrant_client

def search_qdrant(collection_name, query_embedding, limit=5):
    return qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=limit
    ) 