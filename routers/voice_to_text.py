from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
import json
import logging
import asyncio
from typing import Optional
import sys
import os
from io import BytesIO

# Add the current directory to Python path to import stream_speech
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech.stream_speech import SpeechRecognizer
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice to Text"])

# Global variable to store the current recognizer instance
current_recognizer: Optional[SpeechRecognizer] = None

@router.post("/start-recording")
async def start_recording(request: Request):
    """Bắt đầu recording voice-to-text"""
    global current_recognizer
    
    try:
        if current_recognizer:
            # Stop any ongoing run but keep the preloaded model
            try:
                current_recognizer.stop()
            except Exception:
                pass

        # Reuse preloaded recognizer from main
        # Prefer app.state to avoid duplicate module import issues
        voice_components = getattr(request.app.state, "voice_components", None)
        if not voice_components or not voice_components.get("stt"):
            logger.error("Preloaded STT not found in voice_components")
            raise HTTPException(status_code=503, detail="STT model not initialized at startup")

        current_recognizer = voice_components["stt"]

        # Reset lightweight state and start recording without reloading model
        try:
            current_recognizer.reset_recording()
        except Exception:
            logger.warning("Failed to reset recording state; continuing")

        # Start actual recording in background
        logger.info("Starting audio recording with preloaded STT...")
        import threading
        recording_thread = threading.Thread(
            target=current_recognizer.start_recording,
            kwargs={"return_text": False},
            daemon=True
        )
        recording_thread.start()

        return {"status": "success", "message": "Recording started (preloaded)"}
        
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

@router.post("/get-transcription")
async def get_transcription(request: Request):
    """Lấy kết quả transcription từ audio file upload"""
    
    try:
        # Get voice components from app state
        voice_components = getattr(request.app.state, "voice_components", None)
        if not voice_components or not voice_components.get("stt"):
            raise HTTPException(status_code=503, detail="STT model not initialized")
        
        stt = voice_components["stt"]
        
        # For uploaded audio files, we process them directly
        form = await request.form()
        audio_file = form.get("audio")
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Read audio data
        audio_data = await audio_file.read()
        
        # Process audio through STT
        success = stt.feed_audio_bytes(audio_data, metadata={"source": "upload", "format": "webm"})
        
        if success:
            # Get transcription result
            transcribed_text = stt.get_current_text()
            
            # Clear for next input
            stt.clear_text()
            
            return {
                "status": "success",
                "text": transcribed_text or "",
                "message": "Audio processed successfully"
            }
        else:
            return {
                "status": "error", 
                "text": "",
                "message": "Failed to process audio"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-info")
async def get_model_info(request: Request):
    """Lấy thông tin về voice model configuration"""
    try:
        voice_config = settings.voice_config
        voice_components = getattr(request.app.state, "voice_components", None)
        stt_loaded = bool(voice_components and voice_components.get("stt"))
        return {
                    "model_info": {
            "model_name": voice_config.model_name if voice_config else "vinai/PhoWhisper-medium",
            "device": voice_config.device if voice_config else None,
            "batch_size": voice_config.batch_size if voice_config else 8,
            "num_workers": voice_config.num_workers if voice_config else 1,
            "preload_model": voice_config.preload_model if voice_config else False
        },
        "preloaded": bool(voice_config and voice_config.preload_model),
        "ready": stt_loaded
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def synthesize_tts(payload: dict, request: Request):
    """Synthesize speech for given text using preloaded TTS (gTTS by default).

    Returns MP3 audio.
    """
    try:
        text = (payload or {}).get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Missing 'text'")

        # Use global voice components loaded at startup
        voice_components = getattr(request.app.state, "voice_components", None)
        if not voice_components or not voice_components.get("tts"):
            raise HTTPException(status_code=503, detail="TTS not initialized")

        tts = voice_components["tts"]

        # Fast path for gTTS: generate MP3 directly
        if getattr(tts, "engine_name", "") == "gtts":
            try:
                from gtts import gTTS  # type: ignore
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"gTTS unavailable: {e}")

            mp3_buf = BytesIO()
            lang = getattr(tts, "gtts_lang", "vi")
            tld = getattr(tts, "gtts_tld", "com.vn")
            slow = getattr(tts, "gtts_slow", False)
            gTTS(text=text, lang=lang, tld=tld, slow=slow).write_to_fp(mp3_buf)
            mp3_buf.seek(0)

            return StreamingResponse(mp3_buf, media_type="audio/mpeg")

        # Generic path via AudioProcessor queue
        import threading
        import asyncio as _asyncio
        audio_queue: _asyncio.Queue = _asyncio.Queue()
        stop_event = threading.Event()
        audio_collected = BytesIO()
        success_flag = {"done": False, "ok": False}

        def run_synthesis():
            ok = tts.synthesize(text, audio_queue, stop_event, generation_string="TTS")
            success_flag["done"], success_flag["ok"] = True, ok

        synth_thread = threading.Thread(target=run_synthesis, daemon=True)
        synth_thread.start()

        # Collect chunks while synthesis runs
        try:
            while not success_flag["done"] or not audio_queue.empty():
                try:
                    chunk = await _asyncio.wait_for(audio_queue.get(), timeout=0.5)
                    if chunk:
                        audio_collected.write(chunk)
                except _asyncio.TimeoutError:
                    # keep waiting until synthesis done
                    if success_flag["done"] and audio_queue.empty():
                        break
                    continue
        finally:
            stop_event.set()

        audio_collected.seek(0)
        if audio_collected.getbuffer().nbytes == 0:
            raise HTTPException(status_code=500, detail="No audio produced by TTS")

        return StreamingResponse(audio_collected, media_type="audio/mpeg")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synthesizing TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))
