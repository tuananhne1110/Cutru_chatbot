from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json
import logging
import asyncio
from typing import Optional
import sys
import os

# Add the current directory to Python path to import stream_speech
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.call_chatbot.stream_speech import SpeechRecognizer
from src.call_chatbot.voice_init import voice_model, voice_cfg, voice_model_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice to Text"])

# Global variable to store the current recognizer instance
current_recognizer: Optional[SpeechRecognizer] = None

@router.post("/start-recording")
async def start_recording():
    """Bắt đầu recording voice-to-text"""
    global current_recognizer
    
    try:
        if current_recognizer:
            # Clean up existing recognizer
            current_recognizer.stop()
        
        # Always use preloaded model - it should be loaded at startup
        if voice_model:
            # Use the preloaded model directly
            current_recognizer = voice_model
            logger.info("Using preloaded voice model")
            
            # Reset the model state for new recording
            current_recognizer.reset_recording()
            
            # Start actual recording in background
            logger.info("Starting audio recording...")
            import threading
            recording_thread = threading.Thread(
                target=current_recognizer.start_recording,
                kwargs={"return_text": False},
                daemon=True
            )
            recording_thread.start()
        else:
            # If no preloaded model, create a new one (this shouldn't happen)
            logger.warning("No preloaded model found, creating new one...")
            try:
                current_recognizer = SpeechRecognizer(
                    model_name=voice_cfg.get("model_name", "vinai/PhoWhisper-medium"),
                    device=voice_cfg.get("device"),
                    batch_size=voice_cfg.get("batch_size", 8),
                    num_workers=voice_cfg.get("num_workers", 1)
                )
            except Exception as audio_error:
                logger.error(f"Audio device error: {audio_error}")
                raise HTTPException(
                    status_code=500, 
                    detail="Không thể khởi tạo microphone. Vui lòng kiểm tra quyền truy cập microphone và thử lại."
                )
        
        return {"status": "success", "message": "Recording started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-recording")
async def stop_recording():
    """Dừng recording và trả về text đã transcribe"""
    global current_recognizer
    
    try:
        if not current_recognizer:
            raise HTTPException(status_code=400, detail="No active recording")
        
        # Stop recording and get transcribed text
        transcribed_text = current_recognizer.stop()
        
        # Clean up
        current_recognizer = None
        
        return {
            "status": "success", 
            "text": transcribed_text,
            "message": "Recording stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_recording_status():
    """Kiểm tra trạng thái recording hiện tại"""
    global current_recognizer
    
    is_recording = current_recognizer is not None
    current_text = ""
    
    if current_recognizer:
        current_text = current_recognizer.get_current_text()
    
    return {
        "is_recording": is_recording,
        "current_text": current_text
    }

@router.post("/get-current-text")
async def get_current_text():
    """Lấy text hiện tại đang được transcribe"""
    global current_recognizer
    
    try:
        if not current_recognizer:
            return {"text": "", "is_recording": False}
        
        current_text = current_recognizer.get_current_text()
        return {
            "text": current_text,
            "is_recording": True
        }
        
    except Exception as e:
        logger.error(f"Error getting current text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-info")
async def get_model_info():
    """Lấy thông tin về voice model configuration"""
    try:
        return {
            "model_info": voice_model_info,
            "preloaded": voice_model is not None
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
