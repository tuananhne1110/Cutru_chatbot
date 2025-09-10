from typing import Any, Dict, List, Optional, Union
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, Distance, VectorParams, PointStruct, PointIdsList, PayloadSchemaType

from .base import DatabaseConfig, BaseDatabaseConfig
from ..utils.config_utils import BaseConfig
from ..utils.logger_utils import get_logger


logger = get_logger(__name__)

class QdrantDatabase(BaseDatabaseConfig):
    def __init__(self, global_config: Optional[BaseConfig] = None, database_name: Optional[str] = None) -> None:
        super().__init__(global_config=global_config)

        if database_name is not None:
            self.database_name = database_name
            logger.debug(f"Overriding {self.__class__.__name__}'s database_name with: {self.database_name}")
        
        self._init_db_config()
        self._connect()

    def _init_db_config(self) -> None:
        config_dict = self.global_config.__dict__
        config_dict['database_params'] = {
                "url": self.global_config.qdrant_url,
                "api_key": self.global_config.qdrant_api_key,
            }
        self.database_config = DatabaseConfig.from_dict(config_dict=config_dict)
    
    def _connect(self) -> None:
        self.client = QdrantClient(**self.database_config.database_params)
        try:
            collections = self.client.get_collections()
            logger.info(f"✅ Kết nối Qdrant thành công. ")

        except Exception as e:
            logger.error(f"❌ Không thể kết nối Qdrant: {e}")
            
    def create_collection(self, name: str, vector_size: int, **kwargs: Any) -> bool:
        """Tạo collection trong Qdrant. Trả về True nếu tạo thành công hoặc đã tồn tại."""
        try:
            # Kiểm tra nếu collection đã tồn tại
            existing = self.client.get_collections()
            if name in [col.name for col in existing.collections]:
                logger.warning(f"⚠️ Collection '{name}' đã tồn tại.")
                return True

            distance = kwargs.get("distance", Distance.COSINE)

            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=distance)
            )
            logger.info(f"✅ Đã tạo collection '{name}' thành công.")
            return True
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo collection '{name}': {e}")
            return False

    def delete_collection(self, name: str) -> bool:
        """Xoá collection khỏi Qdrant. Trả về True nếu xoá thành công."""
        try:
            # Kiểm tra collection có tồn tại không
            collections = self.client.get_collections()
            if name not in [col.name for col in collections.collections]:
                logger.info(f"⚠️ Collection '{name}' không tồn tại.")
                return False

            # Gọi xoá
            self.client.delete_collection(collection_name=name)
            logger.info(f"✅ Đã xoá collection '{name}' thành công.")
            return True
        except Exception as e:
            logger.error(f"❌ Lỗi khi xoá collection '{name}': {e}")
            return False

    def upsert(
        self,
        collection_name: str,
        records: List[Dict[str, Any]],
        **kwargs: Any,
        ) -> List[str] | bool:
        """Thêm mới hoặc cập nhật điểm vào collection. Trả về danh sách point_id hoặc False nếu lỗi."""
        try:
            # Chuyển đổi records thành PointStruct
            points = []
            for record in records:
                point_id = record.get("id")
                vector = record.get("vector")
                payload = record.get("payload", {})

                if point_id is None or vector is None:
                    raise ValueError("Mỗi record phải có 'id' và 'vector'.")

                points.append(PointStruct(id=point_id, vector=vector, payload=payload))

            # Gửi lên Qdrant
            self.client.upsert(collection_name=collection_name, points=points)

            # Trả về danh sách id đã upsert
            return [str(p.id) for p in points]

        except Exception as e:
            logger.error(f"❌ Lỗi khi upsert vào collection '{collection_name}': {e}")
            return False

    def delete(self, collection_name: str, ids: List[str], **kwargs: Any) -> int:
        """Xoá các điểm theo danh sách id. Trả về số lượng đã xoá."""
        try:
            if not ids:
                logger.warning("⚠️ Danh sách id rỗng, không có gì để xoá.")
                return 0

            # Gọi xoá
            self.client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=ids),
                **kwargs  # Có thể truyền wait=True nếu cần
            )

            logger.info(f"✅ Đã xoá {len(ids)} điểm khỏi collection '{collection_name}'.")
            return len(ids)

        except Exception as e:
            logger.error(f"❌ Lỗi khi xoá điểm khỏi collection '{collection_name}': {e}")
            return 0
    
    def search(
        self,
        query_vector: List[float],
        collection_name: str,
        limit: int = 10,
        filters: Optional[Filter] = None,
        with_vectors: bool = False,
        with_payload: bool = True,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        try:
            if filters:
                results = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    query_filter=filters,
                    limit=limit,
                    with_payload=with_payload,
                    with_vectors=with_vectors
                )
                # return [{"id": p.id, "score": p.score, "payload": p.payload} 
                #        for p in results.points]

                rs = []
                for p in results.points:
                    if with_vectors:
                        rs.append({
                            "id": p.id,
                            "score": p.score, 
                            "payload": p.payload,
                            "vector": p.vector
                        })
                    else:
                        rs.append({
                            "id": p.id,
                            "score": p.score, 
                            "payload": p.payload
                        })
                return rs            
            else:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=with_payload, 
                    with_vectors=with_vectors
                )
                rs = []
                for r in results:
                    if with_vectors:
                        rs.append({
                            "id": r.id,
                            "score": r.score, 
                            "payload": r.payload,
                            "vector": r.vector
                        })
                    else:
                        rs.append({
                            "id": r.id,
                            "score": r.score, 
                            "payload": r.payload
                        })
                return rs            

        except Exception as e:
            logger.error(f"Lỗi tìm kiếm: {e}")
            return []
        
    def query_by_id(
        self, collection_name: str, id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Lấy một bản ghi theo id từ Qdrant. Trả về dict hoặc None nếu không tìm thấy."""
        try:
            response = self.client.retrieve(
                collection_name=collection_name,
                ids=[id],
                with_payload=True,
                with_vector=True,
                **kwargs  # Có thể truyền thêm nếu cần
            )

            if not response:
                logger.warning(f"⚠️ Không tìm thấy bản ghi với id '{id}' trong collection '{collection_name}'.")
                return None

            point = response[0]
            return {
                "id": str(point.id),
                "vector": point.vector,
                "payload": point.payload
            }

        except Exception as e:
            logger.error(f"❌ Lỗi khi truy vấn id '{id}' trong collection '{collection_name}': {e}")
            return None

    # def create_index(self, collection_name: str, **kwargs: Any) -> bool:
    #     """Tạo chỉ mục cho trường payload (nếu cần)."""
    #     try:
    #         field_name = kwargs.get("field")
    #         field_type = kwargs.get("type", PayloadSchemaType.KEYWORD)

    #         if not field_name:
    #             raise ValueError("Cần truyền tên trường payload để tạo index (field='...').")

    #         self.client.create_payload_index(
    #             collection_name=collection_name,
    #             field_name=field_name,
    #             field_schema=field_type
    #         )

    #         return True

    #     except Exception as e:
    #         return False

# run: python -m langgraph_rag.database.qdrant_client
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     db_qdrant = QdrantDatabase(global_config= global_config)

    


        