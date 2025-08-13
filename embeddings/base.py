from abc import ABC, abstractmethod
from typing import List, Union

class BaseEmbedding(ABC):
    """Base class cho embedding models"""
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> Union[List[float], List[List[float]]]:
        """Encode text thành vector"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Lấy dimension của embedding"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Khởi tạo model"""
        pass