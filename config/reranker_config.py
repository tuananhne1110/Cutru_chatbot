"""
Configuration cho BGE Reranker
Có thể bật/tắt và điều chỉnh các tham số reranking
"""

import os
from typing import Dict, Any

class RerankerConfig:
    """Cấu hình cho BGE Reranker"""
    
    def __init__(self):
        # Bật/tắt reranker
        self.enabled = self._get_bool_env("RERANKER_ENABLED", True)
        
        # Model configuration
        self.model_name = self._get_env("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        self.max_length = self._get_int_env("RERANKER_MAX_LENGTH", 512)
        
        # Performance configuration
        self.batch_size = self._get_int_env("RERANKER_BATCH_SIZE", 16)
        self.top_k_before_rerank = self._get_int_env("RERANKER_TOP_K_BEFORE", 25)
        self.top_k_after_rerank = self._get_int_env("RERANKER_TOP_K_AFTER", 15)
        
        # Fallback configuration
        self.fallback_on_error = self._get_bool_env("RERANKER_FALLBACK", True)
        self.log_rerank_stats = self._get_bool_env("RERANKER_LOG_STATS", True)
        
        # Device configuration
        self.force_cpu = self._get_bool_env("RERANKER_FORCE_CPU", False)
        self.device = self._get_device()
    
    def _get_env(self, key: str, default: str) -> str:
        """Lấy giá trị từ environment variable"""
        return os.getenv(key, str(default))
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Lấy giá trị integer từ environment variable"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Lấy giá trị boolean từ environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_device(self) -> str:
        """Xác định device để sử dụng"""
        if self.force_cpu:
            return "cpu"
        
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        except ImportError:
            return "cpu"
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi config thành dictionary"""
        return {
            "enabled": self.enabled,
            "model_name": self.model_name,
            "max_length": self.max_length,
            "batch_size": self.batch_size,
            "top_k_before_rerank": self.top_k_before_rerank,
            "top_k_after_rerank": self.top_k_after_rerank,
            "fallback_on_error": self.fallback_on_error,
            "log_rerank_stats": self.log_rerank_stats,
            "device": self.device
        }
    
    def __str__(self) -> str:
        """String representation của config"""
        config_str = "BGE Reranker Configuration:\n"
        config_str += f"  Enabled: {self.enabled}\n"
        config_str += f"  Model: {self.model_name}\n"
        config_str += f"  Device: {self.device}\n"
        config_str += f"  Batch Size: {self.batch_size}\n"
        config_str += f"  Top-K Before: {self.top_k_before_rerank}\n"
        config_str += f"  Top-K After: {self.top_k_after_rerank}\n"
        config_str += f"  Max Length: {self.max_length}\n"
        config_str += f"  Fallback on Error: {self.fallback_on_error}\n"
        config_str += f"  Log Stats: {self.log_rerank_stats}"
        return config_str

# Global config instance
reranker_config = RerankerConfig()

def get_reranker_config() -> RerankerConfig:
    """Get global reranker config"""
    return reranker_config 