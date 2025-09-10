"""
Voice Router - FastAPI endpoints for voice operations
Provides REST API for voice-to-text, text-to-speech, and voice chatbot functionality.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from ..voice.voice_service import VoiceService
from ..voice.voice_chatbot import VoiceChatbot
from ..langgraph_rag.utils.llm_utils import TextChatMessage
from ..langgraph_rag.utils.config_utils import BaseConfig

logger = logging.getLogger(__name__)

# Request/Response models
class VoiceConfig(BaseModel):
    model_name: str = "vinai/PhoWhisper-medium"
    device: Optional[int] = None
    batch_size: int = 16
    num_workers: int = 2
    tts_rate: int = 180
    tts_volume: float = 1.0

class VoiceChatRequest(BaseModel):
    session_id: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None

class VoiceResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

# Global voice service instance
voice_service: Optional[VoiceService] = None
voice_chatbot: Optional[VoiceChatbot] = None

router = APIRouter(prefix="/voice", tags=["Voice"])

async def get_voice_service() -> VoiceService:
    """Get or create voice service instance."""
    global voice_service
    if voice_service is None:
        # Load configuration from BaseConfig
        try:
            global_config = BaseConfig()
            # Add voice config from YAML to global_config
            voice_yaml_config = global_config.__dict__.get('services', {}).get('voice', {})
            global_config.voice_config = voice_yaml_config
        except Exception as e:
            logger.warning(f"Failed to load global config: {e}")
            global_config = None

        voice_service = VoiceService(global_config=global_config)
        await voice_service.initialize()
    return voice_service

async def get_voice_chatbot() -> VoiceChatbot:
    """Get or create voice chatbot instance."""
    global voice_chatbot
    if voice_chatbot is None:
        service = await get_voice_service()

        # Load global config for chatbot
        try:
            global_config = BaseConfig()
        except Exception as e:
            logger.warning(f"Failed to load global config for chatbot: {e}")
            global_config = None

        voice_chatbot = VoiceChatbot(
            voice_service=service,
            global_config=global_config,
            conversation_history=[]
        )
        await voice_chatbot.initialize()
    return voice_chatbot

@router.post("/initialize", response_model=VoiceResponse)
async def initialize_voice_service(config: VoiceConfig):
    """Initialize voice service with custom configuration."""
    global voice_service, voice_chatbot

    try:
        # Shutdown existing instances
        if voice_service:
            await voice_service.shutdown_async()
        if voice_chatbot:
            await voice_chatbot.shutdown()

        # Create new instances with config
        voice_service = VoiceService(
            model_name=config.model_name,
            device=config.device,
            batch_size=config.batch_size,
            num_workers=config.num_workers,
            tts_rate=config.tts_rate,
            tts_volume=config.tts_volume
        )
        await voice_service.initialize()

        voice_chatbot = VoiceChatbot(
            voice_service=voice_service,
            conversation_history=[]
        )
        await voice_chatbot.initialize()

        return VoiceResponse(
            status="success",
            message="Voice service initialized successfully",
            data={
                "model_name": config.model_name,
                "device": config.device,
                "batch_size": config.batch_size
            }
        )

    except Exception as e:
        logger.error(f"Failed to initialize voice service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start-recording", response_model=VoiceResponse)
async def start_recording():
    """Start voice recording and transcription."""
    try:
        service = await get_voice_service()

        if service.is_recording():
            return VoiceResponse(
                status="error",
                message="Recording already in progress"
            )

        # Start recording asynchronously
        transcribed_text = await service.start_recording_async()

        return VoiceResponse(
            status="success",
            message="Recording completed",
            data={
                "transcribed_text": transcribed_text,
                "text_length": len(transcribed_text)
            }
        )

    except Exception as e:
        logger.error(f"Error in recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-recording", response_model=VoiceResponse)
async def stop_recording():
    """Stop current recording and return transcribed text."""
    try:
        service = await get_voice_service()

        if not service.is_recording():
            current_text = service.get_current_text()
            return VoiceResponse(
                status="success",
                message="No active recording",
                data={"transcribed_text": current_text}
            )

        final_text = await service.stop_recording_async()

        return VoiceResponse(
            status="success",
            message="Recording stopped",
            data={
                "transcribed_text": final_text,
                "text_length": len(final_text)
            }
        )

    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current-text", response_model=VoiceResponse)
async def get_current_text():
    """Get current transcribed text without stopping recording."""
    try:
        service = await get_voice_service()
        current_text = service.get_current_text()

        return VoiceResponse(
            status="success",
            message="Current text retrieved",
            data={
                "transcribed_text": current_text,
                "text_length": len(current_text)
            }
        )

    except Exception as e:
        logger.error(f"Error getting current text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/speak", response_model=VoiceResponse)
async def speak_text(text: str):
    """Convert text to speech."""
    try:
        service = await get_voice_service()

        if not text.strip():
            return VoiceResponse(
                status="error",
                message="Text cannot be empty"
            )

        await service.speak_async(text)

        return VoiceResponse(
            status="success",
            message="Text sent to TTS",
            data={"text": text}
        )

    except Exception as e:
        logger.error(f"Error in TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=VoiceResponse)
async def get_voice_status():
    """Get current voice service status."""
    try:
        service = await get_voice_service()
        stats = service.get_performance_stats()

        return VoiceResponse(
            status="success",
            message="Voice status retrieved",
            data={
                "is_recording": service.is_recording(),
                "is_speaking": service.is_tts_speaking(),
                "performance_stats": stats
            }
        )

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=VoiceResponse)
async def voice_chat():
    """Process voice input and return voice response."""
    try:
        chatbot = await get_voice_chatbot()
        response_text = await chatbot.process_voice_input()

        return VoiceResponse(
            status="success",
            message="Voice chat completed",
            data={
                "response_text": response_text,
                "text_length": len(response_text)
            }
        )

    except Exception as e:
        logger.error(f"Error in voice chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-text", response_model=VoiceResponse)
async def clear_text():
    """Clear current transcribed text."""
    try:
        service = await get_voice_service()
        service.clear_text()

        return VoiceResponse(
            status="success",
            message="Text cleared"
        )

    except Exception as e:
        logger.error(f"Error clearing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/chat")
async def voice_chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time voice chat."""
    await websocket.accept()

    try:
        # Initialize services
        service = await get_voice_service()
        chatbot = await get_voice_chatbot()

        # Set up callbacks
        def on_text_callback(text: str):
            asyncio.create_task(websocket.send_json({
                "type": "transcription",
                "data": {"text": text}
            }))

        def on_status_callback(status: str):
            asyncio.create_task(websocket.send_json({
                "type": "status",
                "data": {"status": status}
            }))

        def on_response_callback(response: str):
            asyncio.create_task(websocket.send_json({
                "type": "response",
                "data": {"text": response}
            }))

        service.set_callbacks(on_text=on_text_callback, on_status=on_status_callback)
        chatbot.set_callbacks(on_response=on_response_callback, on_status=on_status_callback)

        # Send ready signal
        await websocket.send_json({
            "type": "ready",
            "data": {"message": "Voice chat WebSocket connected"}
        })

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "start_chat":
                # Start voice chat loop
                await websocket.send_json({
                    "type": "status",
                    "data": {"status": "chat_started"}
                })

                try:
                    await chatbot.chat_loop()
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Chat error: {str(e)}"}
                    })

            elif data.get("action") == "stop":
                await websocket.send_json({
                    "type": "status",
                    "data": {"status": "stopped"}
                })
                break

    except WebSocketDisconnect:
        logger.info("Voice chat WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice chat WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except:
            pass

@router.on_event("shutdown")
async def shutdown_voice_service():
    """Shutdown voice service on application shutdown."""
    global voice_service, voice_chatbot

    if voice_chatbot:
        await voice_chatbot.shutdown()

    if voice_service:
        await voice_service.shutdown_async()

    logger.info("Voice service shutdown completed")
