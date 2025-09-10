"""
Voice Chatbot - Integration of Voice Service with LangGraph RAG
Provides voice-to-voice conversation capabilities.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from contextlib import asynccontextmanager

from .voice_service import VoiceService
from ..langgraph_rag.utils.llm_utils import TextChatMessage

try:
    from ..langgraph_rag.workflows import create_rag_workflow
    from ..langgraph_rag.utils.config_utils import BaseConfig
    from ..langgraph_rag.nodes import RAGWorkflowNodes, create_default_rag_state
    _HAS_LANGGRAPH = True
except Exception as e:
    logging.warning(f"LangGraph not available: {e}")
    _HAS_LANGGRAPH = False

logger = logging.getLogger(__name__)

class VoiceChatbot:
    """Voice-to-voice chatbot with LangGraph RAG integration."""

    def __init__(self,
                 voice_service: VoiceService,
                 global_config: Optional[Any] = None,
                 conversation_history: Optional[List[TextChatMessage]] = None):

        self.voice_service = voice_service
        self.global_config = global_config or {}
        self.conversation_history = conversation_history or []

        # LangGraph components
        self._rag_workflow = None
        self._rag_nodes = None

        # Callbacks
        self._on_response_callback: Optional[Callable[[str], None]] = None
        self._on_status_callback: Optional[Callable[[str], None]] = None

        logger.info("VoiceChatbot initialized")

    async def initialize(self) -> None:
        """Initialize chatbot components."""
        if _HAS_LANGGRAPH and self.global_config:
            try:
                self._rag_nodes = RAGWorkflowNodes(self.global_config)
                self._rag_workflow = create_rag_workflow(self._rag_nodes)
                logger.info("LangGraph RAG workflow initialized")
            except Exception as e:
                logger.error(f"Failed to initialize LangGraph: {e}")
                self._rag_workflow = None
        else:
            logger.warning("LangGraph not available, using fallback mode")

    def set_callbacks(self,
                     on_response: Optional[Callable[[str], None]] = None,
                     on_status: Optional[Callable[[str], None]] = None) -> None:
        """Set callback functions."""
        self._on_response_callback = on_response
        self._on_status_callback = on_status

    async def process_voice_input(self) -> str:
        """Process voice input and return response."""
        try:
            # Notify status
            if self._on_status_callback:
                self._on_status_callback("listening")

            # Start recording
            user_text = await self.voice_service.start_recording_async()

            if not user_text.strip():
                return "Xin lỗi, tôi không nghe rõ. Bạn có thể nói lại không?"

            logger.info(f"User said: {user_text}")

            # Add to conversation history
            self._add_to_history("user", user_text)

            # Generate response
            if self._on_status_callback:
                self._on_status_callback("processing")

            response_text = await self._generate_response(user_text)

            # Add response to history
            self._add_to_history("assistant", response_text)

            # Speak response
            if self._on_status_callback:
                self._on_status_callback("speaking")

            await self.voice_service.speak_async(response_text)

            # Notify response
            if self._on_response_callback:
                self._on_response_callback(response_text)

            return response_text

        except Exception as e:
            logger.error(f"Error in voice processing: {e}")
            error_msg = "Xin lỗi, có lỗi xảy ra khi xử lý. Vui lòng thử lại."
            if self._on_response_callback:
                self._on_response_callback(error_msg)
            return error_msg

    async def _generate_response(self, user_text: str) -> str:
        """Generate response using LangGraph RAG or fallback."""
        if self._rag_workflow and self._rag_nodes:
            try:
                # Use LangGraph RAG
                state = create_default_rag_state(
                    question=user_text,
                    conversation_history=self.conversation_history
                )

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._rag_workflow.invoke,
                    state
                )

                response = result.get("final_response", "").strip()
                if response:
                    return response

            except Exception as e:
                logger.error(f"LangGraph error: {e}")

        # Fallback response
        return f"Bạn nói: {user_text}. Đây là chế độ fallback vì hệ thống RAG chưa sẵn sàng."

    def _add_to_history(self, role: str, content: str) -> None:
        """Add message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})

        # Keep only last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    async def chat_loop(self) -> None:
        """Main chat loop - continuously listen and respond."""
        logger.info("Starting voice chat loop...")

        try:
            while True:
                await self.process_voice_input()

                # Small delay to prevent immediate re-listening
                await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("Chat loop interrupted by user")
        except Exception as e:
            logger.error(f"Error in chat loop: {e}")

    def get_conversation_history(self) -> List[TextChatMessage]:
        """Get current conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    async def shutdown(self) -> None:
        """Shutdown chatbot."""
        logger.info("Shutting down VoiceChatbot...")
        # Voice service shutdown is handled by the service itself
        logger.info("VoiceChatbot shutdown complete")

    @asynccontextmanager
    async def session(self):
        """Context manager for chatbot session."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.shutdown()
