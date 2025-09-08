import hashlib
from typing import Any, Dict, List, Optional, Union

from .base import RedisConfig, BaseRedisConfig
from ..utils.config_utils import BaseConfig
from ..utils.logger_utils import get_logger
from ..embeddings.qwen_embedding_model import QwenEmbeddingModel

import redis
logger = get_logger(__name__)


class CacheRedis(BaseRedisConfig):
    def __init__(self, global_config: Optional[BaseConfig] = None) -> None:
        super().__init__(global_config=global_config)

        self._init_redis_config()
        self._connect()
    
    def _init_redis_config(self) -> None:
        config_dict = self.global_config.__dict__
        dsn = self.global_config.get_redis_dsn()

        config_dict['redis_params'] = {
            "enabled": self.global_config.redis_enabled,
            "dsn": dsn,
            "host": self.global_config.redis_host,
            "port": self.global_config.redis_port,
            "db": self.global_config.redis_db,
            "password": self.global_config.redis_password,
            "ttl_seconds": self.global_config.redis_ttl_seconds,
            "prefix": self.global_config.redis_prefix,
            "socket_timeout": self.global_config.redis_socket_timeout,
            "max_connections": self.global_config.redis_max_connections
        }

        self.redis_config = RedisConfig.from_dict(config_dict=config_dict)
    
    def _connect(self) -> None:
        
        if not self.redis_config.redis_params["enabled"]:
            logger.info("Redis cache is disabled by config.")
            self.client = None
            return
        
        try:
            if self.redis_config.redis_params["dsn"]:
                pool = redis.ConnectionPool.from_url(
                    self.redis_config.redis_params["dsn"],
                    socket_timeout=self.redis_config.redis_params["socket_timeout"],
                    max_connections=self.redis_config.redis_params["max_connections"],
                )
                self.client = redis.Redis(connection_pool=pool)
            else:
                pool = redis.ConnectionPool(
                    host=self.redis_config.redis_params["host"],
                    port=self.redis_config.redis_params["port"],
                    db=self.redis_config.redis_params["db"],
                    password=self.redis_config.redis_params["password"],
                    socket_timeout=self.redis_config.redis_params["socket_timeout"],
                    max_connections=self.redis_config.redis_params["max_connections"],
                )
                self.client = redis.Redis(connection_pool=pool)

            # Ping thử
            self.client.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.exception(f"Failed to connect to Redis: {e}")
            self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None
    
    @property
    def ttl_default(self) -> int:
        return int(self.redis_config.redis_params["ttl_seconds"])

    @property
    def prefix(self) -> str:
        return str(self.redis_config.redis_params["prefix"])

    @staticmethod
    def _sha256(s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
    
    # def 

# # run: python -m backend.src.langgraph_rag.cache.cache_redis
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     cache_redis = CacheRedis(global_config= global_config)