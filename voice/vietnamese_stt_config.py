"""
Vietnamese STT Optimization Configuration
==========================================

This module provides optimized settings for Vietnamese speech recognition.
Import and use these settings to improve Vietnamese voice recognition quality.

Usage:
    from vietnamese_stt_config import apply_vietnamese_optimizations
    apply_vietnamese_optimizations()
"""

import os
import logging

logger = logging.getLogger(__name__)

# Vietnamese STT Optimized Settings
VIETNAMESE_STT_CONFIG = {
    # PhoWhisper Model Configuration
    "PHOWHISPER_MODEL": "vinai/PhoWhisper-base",
    "USE_VIETNAMESE_STT": "true",
    
    # Audio Processing Optimizations
    "MAX_AUDIO_QUEUE_SIZE": "150",
    "STT_CLEAR_CACHE": "false",
    
    # VAD (Voice Activity Detection) Settings - Optimized for Vietnamese
    "STT_SILERO_SENSITIVITY": "0.15",
    "STT_WEBRTC_SENSITIVITY": "1",
    "STT_SILERO_DEACT": "true",
    "STT_VAD_ABS_THRESHOLD": "200",
    
    # Speech Timing Settings - Tuned for Vietnamese speech patterns
    "STT_POST_SILENCE": "0.8",
    "STT_MIN_RECORDING": "0.3",
    "STT_MIN_GAP": "0.1",
    "STT_SPEECH_START_SILENCE": "0.1",
    "STT_SPEECH_END_SILENCE": "0.6",
    
    # Processing Performance
    "STT_REALTIME_PAUSE": "0.01",
    "STT_ALLOWED_LATENCY": "300",
    "STT_EARLY_ON_SILENCE": "0",
    
    # Audio Buffer Settings
    "STT_MIN_TRANSCRIBE_WINDOW_S": "0.8",
    "STT_TRANSCRIBE_ABS_THRESHOLD": "800",
    "STT_PRE_BUFFER": "1.0",
    
    # Silero VAD Fine-tuning for Vietnamese
    "STT_SILERO_WINDOW_SIZE": "1536",
    "STT_SILERO_PAD_FRAMES": "30",
    
    # Transcription Quality Settings
    "STT_NO_SPEECH_THRESHOLD": "0.3",
    "STT_LOGPROB_THRESHOLD": "-0.8",
    "STT_COMPRESSION_THRESHOLD": "3.0",
    
    # Vietnamese Context Prompt
    "STT_INITIAL_PROMPT_REALTIME": "Tôi đang nói chuyện bằng tiếng Việt. Xin chào. Cảm ơn. Hôm nay thời tiết đẹp.",
    
    # TTS Engine for Vietnamese
    "TTS_ENGINE": "coqui",
    
    # Language Setting
    "LANGUAGE": "vi",
    
    # Logging Level
    "LOG_LEVEL": "INFO"
}

def apply_vietnamese_optimizations():
    """
    Apply Vietnamese STT optimizations to environment variables.
    
    This function sets environment variables to optimize speech recognition
    for Vietnamese language. Only sets variables that aren't already set.
    """
    applied_count = 0
    
    for key, value in VIETNAMESE_STT_CONFIG.items():
        if key not in os.environ:
            os.environ[key] = value
            applied_count += 1
            logger.debug(f"🇻🇳 Set {key}={value}")
    
    if applied_count > 0:
        logger.info(f"🇻🇳✅ Applied {applied_count} Vietnamese STT optimizations")
    else:
        logger.info("🇻🇳ℹ️ Vietnamese STT optimizations already configured via environment")

def get_vietnamese_config():
    """
    Get the Vietnamese STT configuration dictionary.
    
    Returns:
        dict: Configuration settings optimized for Vietnamese STT
    """
    return VIETNAMESE_STT_CONFIG.copy()

def print_current_config():
    """
    Print current STT configuration for debugging.
    """
    logger.info("🇻🇳📋 Current Vietnamese STT Configuration:")
    for key, default_value in VIETNAMESE_STT_CONFIG.items():
        current_value = os.environ.get(key, default_value)
        status = "✅" if key in os.environ else "📋"
        logger.info(f"  {status} {key}: {current_value}")

if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    logger.info("🇻🇳🚀 Vietnamese STT Configuration Demo")
    
    print_current_config()
    apply_vietnamese_optimizations()
    
    logger.info("\n🇻🇳✅ After applying optimizations:")
    print_current_config()
