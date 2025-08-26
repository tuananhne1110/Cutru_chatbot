import logging
import asyncio
logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health
from routers.langgraph_chat import router as langgraph_chat_router
from routers.ct01 import router as ct01_router
from routers.voice_to_text import router as voice_to_text_router
from routers.reader import router as reader_router

# Giảm log spam cho các module phụ
logging.getLogger("agents.context_manager").setLevel(logging.WARNING)

logging.getLogger("prompt.prompt_templates").setLevel(logging.WARNING)
logging.getLogger("services.qdrant_service").setLevel(logging.WARNING)
logging.getLogger("services.reranker_service").setLevel(logging.WARNING)

# Global voice components
voice_components = None

async def startup_event():
    """Khởi động voice components ngay khi server start."""
    global voice_components
    
    logging.info("🚀 Starting Legal Assistant API...")
    
    # Apply Vietnamese STT optimizations early
    try:
        import sys
        import os
        voice_dir = os.path.join(os.path.dirname(__file__), 'voice')
        if voice_dir not in sys.path:
            sys.path.insert(0, voice_dir)
        from voice.vietnamese_stt_config import apply_vietnamese_optimizations
        apply_vietnamese_optimizations()
        logging.info("🇻🇳✅ Vietnamese STT optimizations applied in main.py")
    except ImportError:
        logging.warning("🇻🇳⚠️ Vietnamese STT config not found, using defaults")
    except Exception as e:
        logging.warning(f"🇻🇳⚠️ Error applying Vietnamese STT config: {e}")
    
    try:
        # Import voice components
        from speech.stream_speech import SpeechRecognizer
        from voice.audio_module import AudioProcessor
        
        logging.info("🎤💬 Initializing voice components at startup...")
        
        # Initialize STT with model loading
        logging.info("🎤💬 Loading STT model...")
        stt = SpeechRecognizer(
            model_name="vinai/PhoWhisper-small",
            language="vi",
            batch_size=8,
            num_workers=1
        )
        
        # Model is loaded during initialization; skip audio stream warmup to avoid ALSA issues
        logging.info("🎤💬 STT model loaded successfully (no mic warmup)")
        
        # Initialize TTS
        logging.info("🎤💬 Loading TTS model...")
        tts = AudioProcessor(engine="gtts")
        logging.info("🎤💬 TTS model loaded successfully")
        
        # Store globally
        voice_components = {
            "stt": stt,
            "tts": tts,
            "models_loaded": True,
        }
        # Also store on app.state for cross-module access
        try:
            app.state.voice_components = voice_components
        except Exception:
            pass
        logging.info("🎤💬 Voice components initialized successfully at startup")
        
    except ImportError as e:
        logging.warning(f"🎤💬 Voice components not available: {e}")
        voice_components = None
        try:
            app.state.voice_components = None
        except Exception:
            pass
    except Exception as e:
        logging.error(f"🎤💬 Error initializing voice components: {e}")
        voice_components = None
        try:
            app.state.voice_components = None
        except Exception:
            pass

async def shutdown_event():
    """Cleanup voice components khi server shutdown."""
    global voice_components
    
    if voice_components:
        try:
            if "stt" in voice_components:
                voice_components["stt"].stop()
                voice_components["stt"].reset_recording()
                logging.info("🎤💬 STT stopped and reset")
                
            if "tts" in voice_components:
                logging.info("🎤💬 TTS cleaned up")
                
            voice_components["models_loaded"] = False
            logging.info("🎤💬 Voice components cleaned up")
        except Exception as e:
            logging.error(f"🎤💬 Error cleaning up voice components: {e}")
    try:
        app.state.voice_components = None
    except Exception:
        pass

app = FastAPI(title="Legal Assistant API", version="2.0.0")

# Add startup and shutdown events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use LangGraph as the main chat endpoint (now includes voice interface)
app.include_router(langgraph_chat_router)
app.include_router(health.router)
app.include_router(ct01_router)
app.include_router(voice_to_text_router)
app.include_router(reader_router)

logging.info("🎤💬 Voice interface integrated into chat endpoints")

if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Starting Legal Assistant API with Voice Chatbot Pipeline support")
    uvicorn.run(app, host="0.0.0.0", port=8000) 