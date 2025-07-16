"""Configuration for BGE Reranker.

Allows enabling/disabling and tuning reranking parameters.
"""

import os
from typing import Any, Dict


class RerankerConfig:
    """Configuration for BGE Reranker."""

    def __init__(self):
        # Toggle reranker
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
        """Get value from environment variable.

        Args:
            key: Environment variable name.
            default: Default value if key is not found.

        Returns:
            Value as a string.
        """
        return os.getenv(key, str(default))

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer value from environment variable.

        Args:
            key: Environment variable name.
            default: Default integer value.

        Returns:
            Integer value.
        """
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable.

        Args:
            key: Environment variable name.
            default: Default boolean value.

        Returns:
            Boolean value.
        """
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _get_device(self) -> str:
        """Detect the device to use.

        Returns:
            "cuda" if GPU available, otherwise "cpu".
        """
        if self.force_cpu:
            return "cpu"

        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            A dictionary representation of the config.
        """
        return {
            "enabled": self.enabled,
            "model_name": self.model_name,
            "max_length": self.max_length,
            "batch_size": self.batch_size,
            "top_k_before_rerank": self.top_k_before_rerank,
            "top_k_after_rerank": self.top_k_after_rerank,
            "fallback_on_error": self.fallback_on_error,
            "log_rerank_stats": self.log_rerank_stats,
            "device": self.device,
        }

    def __str__(self) -> str:
        """String representation of the config."""
        return (
            "BGE Reranker Configuration:\n"
            f"  Enabled: {self.enabled}\n"
            f"  Model: {self.model_name}\n"
            f"  Device: {self.device}\n"
            f"  Batch Size: {self.batch_size}\n"
            f"  Top-K Before: {self.top_k_before_rerank}\n"
            f"  Top-K After: {self.top_k_after_rerank}\n"
            f"  Max Length: {self.max_length}\n"
            f"  Fallback on Error: {self.fallback_on_error}\n"
            f"  Log Stats: {self.log_rerank_stats}"
        )


# Global config instance
_reranker_config = RerankerConfig()


def get_reranker_config() -> RerankerConfig:
    """Return global reranker config instance."""
    return _reranker_config
