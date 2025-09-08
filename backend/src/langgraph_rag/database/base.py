import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Any, Dict, List

from ..utils.logger_utils import get_logger
from ..utils.config_utils import BaseConfig



logger = get_logger(__name__)

@dataclass
class DatabaseConfig:
    _data : Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __getattr__(self, key: str) -> Any:
        ignored_prefixes = ("_ipyhon", "_repr_")
        if any(key.startswith(prefix) for prefix in ignored_prefixes):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}")
        if key in self._data:
            return self._data[key]
        logger.error(f"'{self.__class__.__name__}' object has no attribute '{key}'")
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __setattr__(self, key: str, value: Any) -> None:
        if key == '_data':
            super().__setattr__(key, value)
        else:
            self._data[key] = value
        
        # ví dụ object._data = {} -> obj.__setattr__("_data",{} )
        # ví dụ object.x = 1 -> obj.__setattr__("x",1 )

    def __delattr__(self, key: str) -> None:
        if key in self._data:
            return self._data[key]
        else:
            logger.error(f"'{self.__class__.__name__}' object has no attribute '{key}'")
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    def __getitem__(self, key: str) -> Any:
        if key in self._data:
            return self._data[key]
        logger.error(f"'{key}' not found in configuration.")
        raise KeyError(f"'{key}' not found in configuration.")
    
    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
    
    def __delitem_(self, key:str) -> None:
        if key in self._data:
            return self._data[key]
        else:
            logger.error(f"'{key}' not found in configuration.")
            raise KeyError(f"'{key}' not found in configuration.")
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def batch_upsert(self, updates: Dict[str, Any]) -> None:
        self._data.update(updates)
    
    def to_dict(self) -> Dict[str, Any]:
        return self._data

    def to_json(self) -> str:
        return json.dumps(self._data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "DatabaseConfig":
        
        """Create an LLMConfig instance from a dictionary."""
        instance = cls()
        instance.batch_upsert(config_dict)
        return instance
    
    @classmethod
    def from_json(cls, json_str: str) -> "DatabaseConfig":
        """Create an LLMConfig instance from a JSON string."""
        instance = cls()
        instance.batch_upsert(json.loads(json_str))
        return instance

    def __str__(self) -> str:
        """Provide a user-friendly string representation of the configuration."""
        return json.dumps(self._data, indent=4)


class BaseDatabaseConfig(ABC):
    """Base class cho các database clients."""

    global_config: BaseConfig
    db_name: str
    db_config: DatabaseConfig  # store DB-specific configs, init bởi lớp con

    def __init__(self, global_config: Optional[BaseConfig] = None) -> None:
        # 1) Lấy global_config
        if global_config is None:
            logger.debug(
                "global config is not given. Using the default BaseConfig instance."
            )
            self.global_config = BaseConfig()
        else:
            self.global_config = global_config

        # 2) Log cấu hình
        try:
            logger.debug(
                f"Loading {self.__class__.__name__} with global_config: {asdict(self.global_config)}"
            )
        except Exception:
            # asdict() chỉ dùng được với dataclass; fallback nếu BaseConfig không phải dataclass
            logger.debug(
                f"Loading {self.__class__.__name__} with global_config: {self.global_config}"
            )

        # 3) Tên DB (ưu tiên lấy từ config, fallback = tên lớp)
        self.db_name = getattr(self.global_config, "db_name", self.__class__.__name__)
        logger.debug(
            f"Init {self.__class__.__name__}'s db_name with: {self.db_name}"
        )


    # ---------------------------------------------------------------------
    # Các hook bắt buộc lớp con phải cài đặt
    # ---------------------------------------------------------------------
  
    @abstractmethod
    def _connect(self) -> None:
        """Kết nối đến database. Trả về True nếu thành công."""
        raise NotImplementedError

    @abstractmethod
    def create_collection(self, name: str, vector_size: int,  **kwargs: Any) -> bool:
        """Tạo collection / table / index nếu DB yêu cầu. Trả về True nếu OK."""
        raise NotImplementedError

    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """Xoá collection / table."""
        raise NotImplementedError

    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        records: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> List[str] | bool:
        """Thêm mới hoặc cập nhật (idempotent). Trả về list id đã upsert hoặc True/False tuỳ DB."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, collection_name: str, ids: List[str], **kwargs: Any) -> int:
        """Xoá theo danh sách id. Trả về số bản ghi bị xoá."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        collection_name: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        with_vectors: bool = False,
        with_payload: bool = True,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Tìm kiếm theo vector và/hoặc filter. Trả về list kết quả chuẩn hoá."""
        raise NotImplementedError

    @abstractmethod
    def query_by_id(
        self, collection_name: str, id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Lấy một bản ghi theo id."""
        raise NotImplementedError

    # @abstractmethod
    # def create_index(self, collection_name: str, **kwargs: Any) -> bool:
    #     """Tạo chỉ mục (nếu DB yêu cầu)."""
    #     raise NotImplementedError

    # @abstractmethod
    # def health(self) -> Dict[str, Any]:
    #     """Thông tin sức khoẻ / trạng thái của DB (ví dụ: version, uptime, ready)."""
    #     raise NotImplementedError

    # @abstractmethod
    # def ping(self) -> bool:
    #     """Ping thử kết nối nhanh, trả về True nếu DB phản hồi."""
    #     raise NotImplementedError

    # ---------------------------------------------------------------------
    # Tiện ích chung cho các lớp con
    # ---------------------------------------------------------------------
    def batch_upsert_db_config(self, updates: Dict[str, Any]) -> None:
        """Cập nhật cấu hình DB (đẩy vào self.db_config)."""
        self.db_config.batch_upsert(updates)
        logger.debug(
            f"Updated {self.__class__.__name__}'s db_config with {updates} -> {self.db_config}"
        )

    def ensure_connected(self) -> None:
        """Tuỳ chọn: lớp con có thể gọi phương thức này trước khi thao tác để đảm bảo đã connect."""
        if not getattr(self, "_connected", False):
            ok = self.connect()
            self._connected = bool(ok)
            if not self._connected:
                raise RuntimeError(
                    f"{self.__class__.__name__} cannot establish a connection."
                )

    # Context manager để dùng với "with" đảm bảo đóng kết nối an toàn
    def __enter__(self) -> "BaseDatabaseConfig":
        self.ensure_connected()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self.close()
        except Exception as e:
            logger.exception("Error while closing DB connection: %s", e)
        # return False để propagate exception (nếu có)
        return False

    # Helper kiểm tra vector hợp lệ
    @staticmethod
    def _validate_vector(vec: List[float]) -> None:
        if not isinstance(vec, list) or not all(isinstance(x, (int, float)) for x in vec):
            raise TypeError("query_vector must be a List[float]")
        # Nếu cần, bạn có thể enforce chiều dài vector ở lớp con