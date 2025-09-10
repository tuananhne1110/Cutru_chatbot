from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import UploadFile, File, Form
from fastapi import Request
from starlette.responses import FileResponse
from datetime import datetime
import uuid
import logging
from models.schemas import ChatRequest, ChatResponse, Source
from agents.workflow import rag_workflow
from agents.utils.message_conversion import create_initial_state, extract_results_from_state
from agents.state import ChatState
from langchain_core.runnables import RunnableConfig
from typing import cast, Optional, Dict, Any
from fastapi.responses import StreamingResponse
import json
from config.settings import settings
import os
import asyncio
import base64
import struct
import time
import threading
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["LangGraph Chat"])

# Import enhanced voice processing modules
try:
    from utils.voice_processing.enhanced_audio_processor import EnhancedAudioProcessor
    from utils.voice_processing.vietnamese_config import apply_vietnamese_optimizations, get_auto_voice_config
    ENHANCED_VOICE_AVAILABLE = True
    logger.info("🎤✅ Enhanced voice processing modules imported successfully")
except ImportError as e:
    ENHANCED_VOICE_AVAILABLE = False
    logger.warning(f"🎤⚠️ Enhanced voice processing not available: {e}")

# Apply Vietnamese optimizations
if ENHANCED_VOICE_AVAILABLE:
    apply_vietnamese_optimizations()

@router.get("/voice/info")
async def voice_chat_info():
    """Thông tin về voice interface cho chatbot."""
    return {
        "description": "Voice interface cho chatbot hiện tại",
        "websocket_endpoint": "/chat/voice",
        "workflow": "Voice Input → STT → Existing Chat Pipeline → TTS → Voice Output",
        "features": [
            "Speech-to-Text integration (models loaded at startup)",
            "Existing LangGraph RAG workflow", 
            "Text-to-Speech output (models loaded at startup)",
            "Real-time conversation",
            "Instant response (models ready immediately)",
            "Server startup initialization"
        ],
        "enhanced_available": ENHANCED_VOICE_AVAILABLE,
        "auto_voice_endpoint": "/chat/auto-voice" if ENHANCED_VOICE_AVAILABLE else None,
        "message_types": {
            "client_to_server": [
                "audio data (binary)",
                "start_listening",
                "stop_listening", 
                "reset"
            ],
            "server_to_client": [
                "listening_started/stopped",
                "response_start",
                "audio_chunk", 
                "response_complete",
                "tts_error"
            ]
        },
        "usage": {
            "websocket": "ws://localhost:8000/chat/voice",
            "audio_format": "PCM 16-bit, header: timestamp(4bytes) + flags(4bytes) + pcm_data"
        }
    }

@router.get("/voice/status")
async def voice_chat_status():
    """Kiểm tra trạng thái voice components."""
    try:
        # Check global voice components
        from main import voice_components
        if voice_components and voice_components.get("models_loaded", False):
            return {
                "status": "available",
                "models_loaded": True,
                "message": "Voice components are ready (loaded at startup)"
            }
        else:
            return {
                "status": "unavailable", 
                "models_loaded": False,
                "message": "Voice components not available or not loaded"
            }
    except Exception as e:
        return {
            "status": "error",
            "models_loaded": False,
            "message": f"Error checking voice components: {str(e)}"
        }

@router.post("/", response_model=ChatResponse)
async def langgraph_chat(request: ChatRequest):
    """Chat endpoint sử dụng LangGraph workflow"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question
        
        # Build initial state for LangGraph
        initial_state: ChatState = create_initial_state(question, messages, session_id)
        
        # Prepare config with LangSmith metadata
        config_dict = {"configurable": {"thread_id": session_id}}
        
        # Add LangSmith tags and metadata if tracing is enabled
        if settings.langsmith_config.get("tracing_enabled", False):
            config_dict["tags"] = settings.langsmith_config.get("tags", [])
            config_dict["metadata"] = {
                **settings.langsmith_config.get("metadata", {}),
                "session_id": session_id,
                "endpoint": "/chat",
                "timestamp": datetime.now().isoformat(),
                "question_length": len(question) if question else 0,
                "message_count": len(messages)
            }
        
        config = cast(RunnableConfig, config_dict)
        
        # Run LangGraph workflow
        result = await rag_workflow.ainvoke(initial_state, config=config)
        
        # Extract results
        results = extract_results_from_state(result)
        answer = results["answer"]
        sources = results["sources"]
        
        return ChatResponse(
            answer=answer,
            sources=[Source(**src) for src in sources],
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Exception in /langgraph-chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def langgraph_chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint sử dụng LangGraph workflow.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question
        
        # Log the question to debug UTF-8 issues
        logger.info(f"[STREAM] Received question: {repr(question)}")
        
        initial_state: ChatState = create_initial_state(question, messages, session_id)
        
        # Prepare config with LangSmith metadata
        config_dict = {"configurable": {"thread_id": session_id}}
        
        # Add LangSmith tags and metadata if tracing is enabled
        if settings.langsmith_config.get("tracing_enabled", False):
            config_dict["tags"] = settings.langsmith_config.get("tags", []) + ["streaming"]
            config_dict["metadata"] = {
                **settings.langsmith_config.get("metadata", {}),
                "session_id": session_id,
                "endpoint": "/chat/stream",
                "timestamp": datetime.now().isoformat(),
                "question_length": len(question) if question else 0,
                "message_count": len(messages),
                "streaming": True
            }
        
        config = cast(RunnableConfig, config_dict)
        
        # Run workflow to get result
        result = await rag_workflow.ainvoke(initial_state, config=config)
        
        # Kiểm tra nếu guardrails đã chặn
        if result.get("error") == "input_validation_failed":
            answer = result.get("answer", "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam.")
            def guardrails_blocked_stream():
                # Stream từng ký tự của answer
                for char in answer:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': char})}\n\n"
                # Gửi chunk done để báo hiệu kết thúc
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return StreamingResponse(guardrails_blocked_stream(), media_type="text/event-stream; charset=utf-8")
        
        prompt = result.get("prompt")
        sources = result.get("sources", [])
        
        if not prompt:
            answer = result.get("answer", "Xin lỗi, không thể tạo prompt.")
            def fallback_stream():
                for char in answer:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': char})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return StreamingResponse(fallback_stream(), media_type="text/event-stream; charset=utf-8")
        
        # Stream LLM output
        from services.llm_service import call_llm_stream
        def stream_llm():
            # Yield một chuỗi dummy lớn để phá buffer
            yield " " * 2048 + "\n"
            for chunk in call_llm_stream(prompt, model="llama"):
                if chunk:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            # Gửi sources cho frontend
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            # Gửi chunk done để báo hiệu kết thúc
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(stream_llm(), media_type="text/event-stream; charset=utf-8", headers={"Content-Encoding": "utf-8"})
    except Exception as e:
        logger.error(f"Exception in /chat/stream endpoint: {e}",exc_info=True)
        def error_stream(e=e):
            yield f"data: {{\"type\": \"error\", \"content\": \"Đã xảy ra lỗi: {str(e)}\"}}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream; charset=utf-8")

@router.post("/upload")
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(..., description="Các tệp tài liệu để tải lên tạm thời"),
    session_id: str = Form(None),
):
    """Upload tài liệu tạm thời để sử dụng trong phiên chat.

    Lưu vào thư mục tạm cục bộ: /tmp/cutru_uploads/{session_id}/
    Trả về danh sách metadata (filename, content_type, path) để client tham chiếu trong các tin nhắn tiếp theo.
    """
    try:
        sid = session_id or str(uuid.uuid4())
        base_dir = os.path.join("/tmp", "cutru_uploads", sid)
        os.makedirs(base_dir, exist_ok=True)

        saved = []
        for f in files:
            original_name = f.filename or f"file_{uuid.uuid4().hex}"
            safe_name = os.path.basename(original_name)
            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            dest_path = os.path.join(base_dir, unique_name)

            content = await f.read()
            with open(dest_path, "wb") as out:
                out.write(content)

            saved.append({
                "filename": safe_name,
                "stored_name": unique_name,
                "content_type": f.content_type,
                "session_id": sid,
                "path": dest_path,
                "size": len(content),
            })

        return {"session_id": sid, "files": saved}
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/upload/clear")
async def clear_session_uploads(session_id: str):
    """Xóa toàn bộ tài liệu tạm thời của một phiên trong /tmp/cutru_uploads/{session_id}."""
    try:
        base_dir = os.path.join("/tmp", "cutru_uploads", session_id)
        if os.path.isdir(base_dir):
            import shutil
            shutil.rmtree(base_dir)
            return {"session_id": session_id, "cleared": True}
        return {"session_id": session_id, "cleared": False, "reason": "not_found"}
    except Exception as e:
        logger.error(f"Error clearing uploads for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/upload/download")
async def download_uploaded_file(session_id: str, file: str, filename: Optional[str] = None):
    """Tải xuống một tệp đã upload tạm thời theo phiên.

    - session_id: phiên chat
    - file: tên file đã lưu (stored_name) trả về từ /chat/upload
    - filename: tên gợi ý khi tải xuống (tùy chọn)
    """
    try:
        # Chặn traversal
        safe_stored = os.path.basename(file)
        base_dir = os.path.join("/tmp", "cutru_uploads", session_id)
        path = os.path.join(base_dir, safe_stored)
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="File not found")

        download_name = filename or safe_stored
        return FileResponse(path, media_type="application/octet-stream", filename=download_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Voice interface for existing chatbot
@router.websocket("/voice")
async def voice_chat_websocket(websocket: WebSocket):
    """
    Voice interface cho chatbot hiện tại.
    
    Workflow: Voice Input → STT → Existing Chat Pipeline → TTS → Voice Output
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"🎤💬 Voice chat session started: {session_id}")
    
    # Get global voice components (already loaded at startup)
    from main import voice_components
    if not voice_components or not voice_components.get("models_loaded", False):
        await websocket.close(code=1008, reason="Voice components not available")
        return
    
    try:
        # Create message queues
        audio_input_queue = asyncio.Queue()
        text_output_queue = asyncio.Queue() 
        audio_output_queue = asyncio.Queue()
        
        # Start voice processing tasks
        tasks = [
            asyncio.create_task(handle_voice_input(websocket, audio_input_queue, voice_components)),
            asyncio.create_task(process_voice_to_text(audio_input_queue, text_output_queue, voice_components)),
            asyncio.create_task(process_text_through_chatbot(text_output_queue, audio_output_queue, session_id)),
            asyncio.create_task(handle_voice_output(websocket, audio_output_queue, voice_components))
        ]
        
        # Wait for any task to complete
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
        
        await asyncio.gather(*pending, return_exceptions=True)
        
    except WebSocketDisconnect:
        logger.info(f"🎤💬 Voice chat session ended: {session_id}")
    except Exception as e:
        logger.error(f"🎤💬 Error in voice chat: {e}")
        await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
    finally:
        # No need to cleanup global components
        logger.info(f"🎤💬 Voice chat session ended: {session_id}")

async def initialize_voice_components() -> Optional[Dict[str, Any]]:
    """Initialize STT and TTS components."""
    try:
        # Import voice components lazily
        from speech.stream_speech import SpeechRecognizer
        from voice.audio_module import AudioProcessor
        
        logger.info("🎤💬 Initializing voice components...")
        
        # Initialize STT with model loading
        stt = SpeechRecognizer(
            model_name="vinai/PhoWhisper-medium",
            language="vi",
            batch_size=8,
            num_workers=1
        )
        
        # Start STT recording to load model
        logger.info("🎤💬 Loading STT model...")
        stt.start_recording()
        await asyncio.sleep(1)  # Give time for model to load
        stt.stop()
        logger.info("🎤💬 STT model loaded successfully")
        
        # Initialize TTS
        logger.info("🎤💬 Loading TTS model...")
        tts = AudioProcessor(engine="coqui")
        
        # Test TTS initialization
        test_text = "Xin chào"
        logger.info("🎤💬 Testing TTS with sample text...")
        # Note: We don't actually synthesize here, just ensure TTS is ready
        
        logger.info("🎤💬 Voice components initialized successfully")
        return {
            "stt": stt,
            "tts": tts,
            "stt_active": False,
            "current_audio_buffer": [],
            "models_loaded": True,
        }
        
    except ImportError as e:
        logger.warning(f"🎤💬 Voice components not available: {e}")
        return None
    except Exception as e:
        logger.error(f"🎤💬 Error initializing voice components: {e}")
        return None

async def cleanup_voice_components(components: Dict[str, Any]):
    """Clean up voice components."""
    try:
        if "stt" in components:
            components["stt"].stop()
            components["stt"].reset_recording()
            logger.info("🎤💬 STT stopped and reset")
            
        if "tts" in components:
            # Cleanup TTS if needed
            logger.info("🎤💬 TTS cleaned up")
            
        components["models_loaded"] = False
        logger.info("🎤💬 Voice components cleaned up")
    except Exception as e:
        logger.error(f"🎤💬 Error cleaning up voice components: {e}")

async def handle_voice_input(websocket: WebSocket, audio_queue: asyncio.Queue, components: Dict[str, Any]):
    """Handle incoming voice data from WebSocket."""
    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                # Audio data
                raw_audio = message["bytes"]
                
                # Parse header (timestamp + flags)
                if len(raw_audio) >= 8:
                    timestamp_ms, flags = struct.unpack("!II", raw_audio[:8])
                    pcm_data = raw_audio[8:]
                    
                    audio_metadata = {
                        "timestamp": timestamp_ms,
                        "flags": flags,
                        "pcm": pcm_data,
                        "is_speech": bool(flags & 1)  # Assume bit 0 indicates speech
                    }
                    
                    await audio_queue.put(audio_metadata)
                    
            elif "text" in message and message["text"]:
                # Control messages
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "start_listening":
                        components["stt_active"] = True
                        await websocket.send_json({"type": "listening_started"})
                        logger.info("🎤💬 Started listening (models already loaded)")
                        
                    elif msg_type == "stop_listening":
                        components["stt_active"] = False 
                        await websocket.send_json({"type": "listening_stopped"})
                        logger.info("🎤💬 Stopped listening")
                        
                    elif msg_type == "reset":
                        components["current_audio_buffer"].clear()
                        await websocket.send_json({"type": "reset_done"})
                        logger.info("🎤💬 Reset audio buffer")
                        
                except json.JSONDecodeError:
                    logger.warning("🎤💬 Invalid JSON in text message")
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"🎤💬 Error handling voice input: {e}")

async def process_voice_to_text(audio_queue: asyncio.Queue, text_queue: asyncio.Queue, components: Dict[str, Any]):
    """Process audio to text using STT."""
    import numpy as np
    
    try:
        audio_buffer = []
        silence_frames = 0
        min_speech_frames = 10  # Minimum frames for speech
        max_silence_frames = 20  # Max silence before processing
        
        while True:
            try:
                # Get audio data
                audio_data = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                
                if not components["stt_active"]:
                    continue
                    
                # Convert PCM bytes to numpy array
                pcm_bytes = audio_data["pcm"]
                if len(pcm_bytes) > 0:
                    # Convert to float32 and normalize
                    audio_samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    audio_buffer.append(audio_samples)
                    
                    # Check for speech
                    if audio_data.get("is_speech", False):
                        silence_frames = 0
                    else:
                        silence_frames += 1
                    
                    # Process audio when we have enough speech and hit silence
                    if len(audio_buffer) >= min_speech_frames and silence_frames >= max_silence_frames:
                        await process_audio_buffer(audio_buffer, text_queue, components)
                        audio_buffer.clear()
                        silence_frames = 0
                        
            except asyncio.TimeoutError:
                # Process any remaining audio buffer
                if len(audio_buffer) >= min_speech_frames:
                    await process_audio_buffer(audio_buffer, text_queue, components)
                    audio_buffer.clear()
                continue
                
    except Exception as e:
        logger.error(f"🎤💬 Error in voice to text processing: {e}")

async def process_audio_buffer(audio_buffer: list, text_queue: asyncio.Queue, components: Dict[str, Any]):
    """Process accumulated audio buffer to extract text."""
    try:
        import numpy as np
        
        if not audio_buffer:
            return
            
        # Concatenate audio samples
        full_audio = np.concatenate(audio_buffer)
        
        # Ensure minimum length (1 second at 16kHz)
        if len(full_audio) < 16000:
            return
            
        # Run STT in thread to avoid blocking
        def run_stt():
            try:
                stt = components["stt"]
                
                # Check if models are loaded
                if not components.get("models_loaded", False):
                    logger.warning("🎤💬 Models not loaded, skipping transcription")
                    return ""
                
                # Reset and prepare for new audio
                stt.clear_text()
                
                # Feed audio data to STT (using the loaded model)
                # Convert audio to the format expected by STT
                audio_bytes = full_audio.tobytes()
                
                # Use STT's feed_audio_bytes method if available
                if hasattr(stt, 'feed_audio_bytes'):
                    stt.feed_audio_bytes(audio_bytes)
                    # Get transcription result
                    text = stt.get_transcription() or ""
                else:
                    # Fallback: simulate transcription
                    logger.warning("🎤💬 STT feed_audio_bytes not available, using placeholder")
                    text = "Placeholder transcribed text"  # TODO: Integrate with actual STT
                
                return text.strip()
            except Exception as e:
                logger.error(f"🎤💬 STT error: {e}")
                return ""
        
        # Run STT in thread pool
        text = await asyncio.to_thread(run_stt)
        
        if text:
            logger.info(f"🎤💬 Transcribed: {text}")
            await text_queue.put({
                "type": "transcription",
                "text": text,
                "timestamp": time.time()
            })
            
    except Exception as e:
        logger.error(f"🎤💬 Error processing audio buffer: {e}")

async def process_text_through_chatbot(text_queue: asyncio.Queue, audio_queue: asyncio.Queue, session_id: str):
    """Process transcribed text through existing chatbot pipeline."""
    try:
        while True:
            # Get transcribed text
            text_data = await text_queue.get()
            
            if text_data["type"] != "transcription":
                continue
                
            user_text = text_data["text"]
            if not user_text.strip():
                continue
                
            logger.info(f"🎤💬 Processing: {user_text}")
            
            try:
                # Create ChatState for LangGraph workflow
                initial_state: ChatState = create_initial_state(user_text, [], session_id)
                
                # Run through existing chatbot pipeline
                config = cast(RunnableConfig, {"configurable": {"thread_id": session_id}})
                result = await rag_workflow.ainvoke(initial_state, config=config)
                
                # Extract answer
                results = extract_results_from_state(result)
                answer = results["answer"]
                sources = results.get("sources", [])
                
                if answer:
                    logger.info(f"🎤💬 Chatbot response: {answer[:100]}...")
                    
                    # Send to TTS
                    await audio_queue.put({
                        "type": "tts_request",
                        "text": answer,
                        "user_text": user_text,
                        "sources": sources,
                        "timestamp": time.time()
                    })
                else:
                    logger.warning("🎤💬 Empty response from chatbot")
                    
            except Exception as e:
                logger.error(f"🎤💬 Error in chatbot processing: {e}")
                # Send error response
                await audio_queue.put({
                    "type": "tts_request", 
                    "text": "Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn.",
                    "user_text": user_text,
                    "sources": [],
                    "timestamp": time.time()
                })
                
    except Exception as e:
        logger.error(f"🎤💬 Error in text processing: {e}")

async def handle_voice_output(websocket: WebSocket, audio_queue: asyncio.Queue, components: Dict[str, Any]):
    """Handle TTS and send audio back to client."""
    try:
        while True:
            # Get TTS request
            tts_data = await audio_queue.get()
            
            if tts_data["type"] != "tts_request":
                continue
                
            text_to_speak = tts_data["text"]
            user_text = tts_data.get("user_text", "")
            sources = tts_data.get("sources", [])
            
            logger.info(f"🎤💬 TTS: {text_to_speak[:50]}...")
            
            # Send response metadata first
            await websocket.send_json({
                "type": "response_start",
                "user_text": user_text,
                "response_text": text_to_speak,
                "sources": sources
            })
            
            try:
                # Generate TTS audio
                audio_chunks = await generate_tts_audio(text_to_speak, components)
                
                # Send audio chunks
                for chunk in audio_chunks:
                    if chunk:
                        # Encode audio chunk as base64
                        audio_b64 = base64.b64encode(chunk).decode('utf-8')
                        await websocket.send_json({
                            "type": "audio_chunk",
                            "data": audio_b64
                        })
                
                # Send completion signal
                await websocket.send_json({
                    "type": "response_complete"
                })
                
                logger.info("🎤💬 TTS completed")
                
            except Exception as e:
                logger.error(f"🎤💬 TTS error: {e}")
                await websocket.send_json({
                    "type": "tts_error",
                    "error": str(e)
                })
                
    except Exception as e:
        logger.error(f"🎤💬 Error in voice output: {e}")

async def generate_tts_audio(text: str, components: Dict[str, Any]) -> list:
    """Generate TTS audio chunks."""
    try:
        import threading
        from queue import Queue, Empty
        
        tts = components["tts"]
        audio_chunks = Queue()
        stop_event = threading.Event()
        
        # Run TTS in thread
        def run_tts():
            try:
                # Check if models are loaded
                if not components.get("models_loaded", False):
                    logger.warning("🎤💬 TTS models not loaded")
                    return False
                
                return tts.synthesize(
                    text=text,
                    audio_chunks=audio_chunks,
                    stop_event=stop_event,
                    generation_string="VoiceChat"
                )
            except Exception as e:
                logger.error(f"🎤💬 TTS synthesis error: {e}")
                return False
        
        # Start TTS
        success = await asyncio.to_thread(run_tts)
        
        # Collect audio chunks
        chunks = []
        while not audio_chunks.empty():
            try:
                chunk = audio_chunks.get_nowait()
                chunks.append(chunk)
            except Empty:
                break
        
        return chunks
        
    except Exception as e:
        logger.error(f"🎤💬 Error generating TTS audio: {e}")
        return []

# Enhanced Auto Voice Chat WebSocket with Turn Detection
@router.websocket("/auto-voice")
async def auto_voice_chat(websocket: WebSocket):
    """
    Enhanced Voice Chat WebSocket với tự động phát hiện kết thúc câu nói.
    
    Chỉ cần click một lần để bắt đầu - không cần nhấn nút gì thêm!
    Hệ thống sẽ tự động:
    - Phát hiện khi người dùng bắt đầu nói
    - Phát hiện khi người dùng kết thúc câu nói
    - Xử lý và trả lời tự động
    """
    if not ENHANCED_VOICE_AVAILABLE:
        await websocket.close(code=4001, reason="Enhanced voice processing not available")
        return
    
    await websocket.accept()
    logger.info("🎤🤖 Auto Voice Chat WebSocket connected")
    
    # Initialize voice components
    voice_components = getattr(websocket.app.state, 'voice_components', None)
    if not voice_components or not voice_components.get("models_loaded", False):
        await websocket.send_json({
            "type": "error",
            "message": "Voice models not loaded. Please restart the server."
        })
        await websocket.close()
        return
    
    # Create enhanced audio processor
    enhanced_processor = None
    try:
        enhanced_processor = EnhancedAudioProcessor(
            base_audio_processor=voice_components["tts"],
            silence_threshold=1.2,  # 1.2 seconds of silence to end speech
            enable_turn_detection=True,
            enable_sentence_detection=True
        )
        
        # Set up callbacks
        async def on_speech_start():
            await websocket.send_json({"type": "speech_started"})
        
        async def on_speech_end():
            await websocket.send_json({"type": "speech_ended"})
        
        async def on_partial_text(text: str):
            await websocket.send_json({
                "type": "partial_transcription",
                "text": text
            })
        
        async def on_final_text(text: str):
            await websocket.send_json({
                "type": "final_transcription", 
                "text": text
            })
            # Automatically process the text through chat pipeline
            await process_auto_voice_input(websocket, text, voice_components)
        
        async def on_silence_detected():
            await websocket.send_json({"type": "silence_detected"})
        
        # Assign callbacks
        enhanced_processor.on_speech_start = on_speech_start
        enhanced_processor.on_speech_end = on_speech_end 
        enhanced_processor.on_partial_text = on_partial_text
        enhanced_processor.on_final_text = on_final_text
        enhanced_processor.on_silence_detected = on_silence_detected
        
        # Call speech start callback immediately after starting
        await on_speech_start()
        
        # Send ready signal
        await websocket.send_json({
            "type": "ready",
            "message": "Auto voice chat ready. Click to start speaking!",
            "features": {
                "auto_turn_detection": True,
                "vietnamese_optimized": True,
                "sentence_detection": True,
                "silence_detection": True
            }
        })
        
        # Main message loop
        while True:
            try:
                # Receive message
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    break
                
                # Handle text messages (commands)
                if message["type"] == "websocket.receive" and "text" in message:
                    data = json.loads(message["text"])
                    logger.info(f"🎤📨 Received command: {data.get('type', 'unknown')}")
                    await handle_auto_voice_command(websocket, data, enhanced_processor)
                
                # Handle binary messages (audio data)
                elif message["type"] == "websocket.receive" and "bytes" in message:
                    audio_data = message["bytes"]
                    logger.debug(f"🎤📥 Received audio data: {len(audio_data)} bytes")
                    
                    # Process audio if we're listening
                    if enhanced_processor.is_active():
                        try:
                            # Simple gating to reduce false positives
                            min_total_bytes = 30000
                            # Update a simple counter on the processor instance
                            total_bytes = getattr(enhanced_processor, "_session_total_bytes", 0) + len(audio_data)
                            setattr(enhanced_processor, "_session_total_bytes", total_bytes)

                            # Heuristic voice activity check
                            has_voice = False
                            try:
                                has_voice = enhanced_processor._has_voice_activity(audio_data)  # type: ignore[attr-defined]
                            except Exception:
                                has_voice = len(audio_data) > 6000

                            if has_voice and total_bytes >= min_total_bytes:
                                logger.debug(f"🎤🔄 Processing WebM audio chunk: {len(audio_data)} bytes (voice detected)")
                                transcribed_text = await process_voice_audio_enhanced(
                                    audio_data, enhanced_processor, voice_components
                                )
                                
                                # If we got a complete transcription, process it
                                if transcribed_text:
                                    logger.info(f"🎤✅ Processing transcribed text: '{transcribed_text}'")
                                    await process_auto_voice_input(websocket, transcribed_text, voice_components)
                                    
                                    # Stop listening after processing one complete phrase
                                    enhanced_processor.stop_listening()
                                    await websocket.send_json({
                                        "type": "listening_stopped",
                                        "message": "Processing complete. Click to speak again."
                                    })
                            else:
                                logger.debug("🎤🔇 Skipping chunk (insufficient voice activity or not enough data yet)")
                            
                        except Exception as e:
                            logger.error(f"🎤💥 Error processing audio: {e}")
                            await websocket.send_json({
                                "type": "error", 
                                "message": f"Audio processing error: {str(e)}"
                            })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"🎤🤖💥 Auto voice chat error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                })
    
    except Exception as e:
        logger.error(f"🎤🤖💥 Auto voice chat initialization error: {e}")
        await websocket.send_json({
            "type": "error", 
            "message": f"Initialization error: {str(e)}"
        })
    
    finally:
        # Cleanup
        if enhanced_processor and enhanced_processor.is_active():
            enhanced_processor.stop_listening()
        logger.info("🎤🤖 Auto Voice Chat WebSocket disconnected")

async def handle_auto_voice_command(websocket: WebSocket, data: dict, enhanced_processor: EnhancedAudioProcessor):
    """Handle commands for auto voice chat."""
    command = data.get("type")
    
    if command == "start_listening":
        if enhanced_processor.start_listening():
            # Clear any residual STT text to avoid stale output
            try:
                from main import voice_components as _vc
                if _vc and _vc.get("stt"):
                    _vc["stt"].clear_text()
            except Exception:
                pass
            await websocket.send_json({
                "type": "listening_started",
                "message": "Listening started. Speak now - system will auto-detect when you finish!"
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Failed to start listening"
            })
    
    elif command == "stop_listening":
        final_text = enhanced_processor.stop_listening()
        await websocket.send_json({
            "type": "listening_stopped",
            "final_text": final_text or ""
        })
    
    elif command == "reset":
        enhanced_processor.stop_listening()
        await websocket.send_json({
            "type": "reset_complete"
        })
    
    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown command: {command}"
        })

async def process_voice_audio_enhanced(audio_data: bytes, enhanced_processor: EnhancedAudioProcessor, voice_components: dict):
    """Process audio through enhanced STT system with voice activity detection."""
    try:
        stt = voice_components.get("stt")
        if not stt:
            logger.warning("🎤⚠️ STT component not available")
            return
        
        # Skip processing for small audio chunks (likely noise)
        if len(audio_data) < 1000:  # Skip chunks smaller than 1KB
            return
        
        # For WebM/Opus audio, we need basic voice activity detection
        # Since we can't easily decode WebM here, we'll use size and patterns as heuristics
        
        # Simple heuristic: WebM chunks with actual speech tend to be larger and more variable
        # Silent/noise chunks are usually smaller and more uniform
        
        # Check if this looks like meaningful audio content
        if len(audio_data) < 3000:  # Very small chunks are likely silence/noise
            logger.debug(f"🎤🔇 Skipping small audio chunk: {len(audio_data)} bytes")
            return
            
        logger.debug(f"🎤📡 Processing audio chunk: {len(audio_data)} bytes")
        
        # Feed audio bytes to STT system
        success = stt.feed_audio_bytes(audio_data, metadata={"source": "websocket", "format": "webm"})
        
        if success:
            # Get current transcription result
            current_text = stt.get_current_text()
            
            if current_text and current_text.strip():
                # Filter out obvious nonsense/repeated patterns
                text_clean = current_text.strip().lower()
                
                # Check for repetitive patterns that indicate false positives
                words = text_clean.split()
                if len(words) > 3:
                    # Check if it's mostly repetitive (like "tháng đến tháng đến...")
                    unique_words = set(words)
                    repetition_ratio = len(words) / len(unique_words)
                    
                    if repetition_ratio > 3:  # Too repetitive, likely false positive
                        logger.debug(f"🎤🚫 Filtering repetitive transcription: '{current_text}'")
                        stt.clear_text()  # Clear the false positive
                        return
                
                logger.info(f"🎤📝 STT output: '{current_text}'")
                
                # Check if this looks like a complete sentence/phrase
                is_final = any(current_text.strip().endswith(punct) for punct in ['.', '!', '?']) or \
                          len(current_text.strip()) > 50  # Long enough to be complete
                
                if is_final:
                    # Clear STT text for next input
                    stt.clear_text()
                    logger.info(f"🎤✅ Final transcription: '{current_text}'")
                    return current_text.strip()
                else:
                    logger.debug(f"🎤🔄 Partial transcription: '{current_text}'")
        else:
            logger.debug("🎤❌ Failed to feed audio to STT")
    
    except Exception as e:
        logger.error(f"🎤🤖💥 Enhanced audio processing error: {e}")
    
    return None

async def process_auto_voice_input(websocket: WebSocket, text: str, voice_components: dict):
    """Process voice input through the chat pipeline automatically."""
    try:
        await websocket.send_json({
            "type": "processing_started",
            "text": text
        })
        
        # Process through existing chat pipeline
        session_id = f"auto_voice_{int(time.time())}"
        
        # Create chat request
        request = ChatRequest(
            question=text,
            session_id=session_id
        )
        
        # Process through RAG workflow
        initial_state = create_initial_state(request.question, request.messages or [], request.session_id)
        config = RunnableConfig(configurable={"thread_id": session_id})
        
        # Stream response
        await websocket.send_json({
            "type": "response_start"
        })
        
        response_text = ""
        async for chunk in rag_workflow.astream(initial_state, config=config):
            state = cast(ChatState, chunk)
            result = extract_results_from_state(state)
            
            if result and result.get("answer"):
                chunk_text = result["answer"]
                if chunk_text != response_text:
                    new_content = chunk_text[len(response_text):]
                    response_text = chunk_text
                    
                    await websocket.send_json({
                        "type": "response_chunk",
                        "text": new_content
                    })
        
        # Generate TTS audio
        if response_text:
            await websocket.send_json({
                "type": "tts_start"
            })
            
            audio_chunks = await generate_tts_audio(response_text, voice_components)
            
            for chunk in audio_chunks:
                await websocket.send_bytes(chunk)
            
            await websocket.send_json({
                "type": "response_complete",
                "final_text": response_text
            })
        
    except Exception as e:
        logger.error(f"🎤🤖💥 Auto voice input processing error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Processing error: {str(e)}"
        }) 