from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

class Qdrantcache:
    def __init__(self, qclient: QdrantClient):
        self.qclient = qclient
    
    def up_points(self, points: List[PointStruct]) -> None:
        self.qclient.upload_points(
            collection_name="qdrant_cache", 
            points=points,
        )