import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Any, Dict, List, Union
import numpy as np
from qdrant_client.models import Filter
from ..utils.logger_utils import get_logger
from ..utils.config_utils import BaseConfig


class TextChatMessage:
    pass

logger = get_logger(__name__)

@dataclass
class FilterConfig:
    _data : Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __getattr__(self, key: str) -> Any:
        ignored_prefixes = ("_ipython", "_repr_")
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
            del self._data[key]
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
    
    def __delitem__(self, key:str) -> None:
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
    def from_dict(cls, config_dict: Dict[str, Any]) -> "FilterConfig":
        
        """Create an FilterConfig instance from a dictionary."""
        instance = cls()
        instance.batch_upsert(config_dict)
        return instance
    
    @classmethod
    def from_json(cls, json_str: str) -> "FilterConfig":
        """Create an FilterConfig instance from a JSON string."""
        instance = cls()
        instance.batch_upsert(json.loads(json_str))
        return instance

    def __str__(self) -> str:
        """Provide a user-friendly string representation of the configuration."""
        return json.dumps(self._data, indent=4)


class BaseFilterConfig(ABC):
    global_config: BaseConfig
    llm_name: str
    filter_config: FilterConfig

    def __init__(self, global_config: Optional[BaseConfig] = None) -> None:
        if global_config is None:
            logger.debug("global config is not given. Using the default BaseConfig instance.")
            self.global_config = BaseConfig()
        else:
            self.global_config = global_config

        try:
            logger.debug(f"Loading {self.__class__.__name__} with global_config: {asdict(self.global_config)}")

            self.llm_name = self.global_config.llm_name
            logger.debug(f"Init {self.__class__.__name__}'s llm_name with: {self.llm_name}")

        except Exception:
            # asdict() chỉ dùng được với dataclass; fallback nếu BaseConfig không phải dataclass
            logger.debug(f"Loading {self.__class__.__name__} with global_config: {self.global_config}")

    @abstractmethod
    def _init_filter_llm_config(self) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def automate_filtering(self, user_query, formatted_indexes, filter_prompt) -> Filter:
        raise NotImplementedError
