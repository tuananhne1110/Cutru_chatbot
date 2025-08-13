"""
Voice-to-Text Model Initialization
"""

import logging
from typing import Optional
import torch

logger = logging.getLogger(__name__)

def initialize_voice_model(config: dict) -> Optional[object]:
    """
    Khởi tạo voice-to-text model một cách an toàn
    
    Args:
        config: Voice configuration dictionary
        
    Returns:
        SpeechRecognizer instance or None if failed
    """
    try:
        # Check if preload is enabled

        if not config.get("preload_model", False):
            logger.info("Voice model preloading is disabled")
            return None
            
        logger.info("Initializing voice-to-text model...")
        
        # Import here to avoid circular imports
        from stream_speech import SpeechRecognizer
        
        # Get configuration
        model_name = config.get("model_name", "vinai/PhoWhisper-medium")
        device = config.get("device")
        batch_size = config.get("batch_size", 8)
        num_workers = config.get("num_workers", 1)
        
        # Auto-detect device if not specified
        if device is None:
            device = 0 if torch.cuda.is_available() else -1
            logger.info(f"Auto-detected device: {'GPU' if device >= 0 else 'CPU'}")
        
        # Create recognizer
        recognizer = SpeechRecognizer(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            num_workers=num_workers
        )
        
        logger.info(f"✓ Voice model '{model_name}' loaded successfully")
        logger.info(f"  - Device: {'GPU' if device >= 0 else 'CPU'}")
        logger.info(f"  - Batch size: {batch_size}")
        logger.info(f"  - Workers: {num_workers}")
        
        return recognizer
        
    except ImportError as e:
        logger.warning(f"Voice-to-text dependencies not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize voice model: {e}")
        return None

def get_voice_model_info(config: dict) -> dict:
    """
    Lấy thông tin về voice model configuration
    
    Args:
        config: Voice configuration dictionary
        
    Returns:
        Dictionary with model information
    """
    info = {
        "model_name": config.get("model_name", "vinai/PhoWhisper-medium"),
        "device": config.get("device"),
        "batch_size": config.get("batch_size", 8),
        "num_workers": config.get("num_workers", 1),
        "preload_model": config.get("preload_model", False),
        "vad_aggressiveness": config.get("vad_aggressiveness", 3),
        "frame_duration": config.get("frame_duration", 30),
        "sample_rate": config.get("sample_rate", 16000),
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }
    
    # Auto-detect device if not specified
    if info["device"] is None:
        info["device"] = 0 if torch.cuda.is_available() else -1
        info["device_name"] = "GPU" if info["device"] >= 0 else "CPU"
    
    return info
