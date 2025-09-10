"""
Voice Service - Central manager for all voice operations
Provides unified interface for speech recognition, TTS, and voice chat functionality.
"""

import asyncio
import logging
import threading
from typing import Optional, Dict, Any, Callable
from contextlib import asynccontextmanager

from .speech_recognizer import SpeechRecognizer
from .tts_engine import TTSEngine

logger = logging.getLogger(__name__)

class VoiceService:
    """Central service for managing voice operations including ASR, TTS, and voice chat."""

    def __init__(self,
                 global_config: Optional[Any] = None,
                 model_name: Optional[str] = None,
                 device: Optional[int] = None,
                 batch_size: Optional[int] = None,
                 num_workers: Optional[int] = None,
                 tts_rate: Optional[int] = None,
                 tts_volume: Optional[float] = None):

        # Load configuration
        if global_config:
            # Try to load from global config (e.g., BaseConfig with voice settings)
            try:
                voice_config = getattr(global_config, 'voice_config', {}) or {}
                self.model_name = model_name or voice_config.get('model_name', 'vinai/PhoWhisper-medium')
                self.device = device if device is not None else voice_config.get('device')
                self.batch_size = batch_size or voice_config.get('batch_size', 16)
                self.num_workers = num_workers or voice_config.get('num_workers', 2)
                self.tts_rate = tts_rate if tts_rate is not None else voice_config.get('tts_rate', 180)
                self.tts_volume = tts_volume if tts_volume is not None else voice_config.get('tts_volume', 1.0)
            except:
                # Fallback to defaults if config loading fails
                self.model_name = model_name or 'vinai/PhoWhisper-medium'
                self.device = device
                self.batch_size = batch_size or 16
                self.num_workers = num_workers or 2
                self.tts_rate = tts_rate or 180
                self.tts_volume = tts_volume or 1.0
        else:
            # Use provided parameters or defaults
            self.model_name = model_name or 'vinai/PhoWhisper-medium'
            self.device = device
            self.batch_size = batch_size or 16
            self.num_workers = num_workers or 2
            self.tts_rate = tts_rate or 180
            self.tts_volume = tts_volume or 1.0

        # Initialize components
        self._speech_recognizer: Optional[SpeechRecognizer] = None
        self._tts_engine: Optional[TTSEngine] = None

        # State management
        self._is_recording = False
        self._current_text = ""
        self._recording_thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_text_callback: Optional[Callable[[str], None]] = None
        self._on_status_callback: Optional[Callable[[str], None]] = None

        logger.info("VoiceService initialized")

    async def initialize(self) -> None:
        """Async initialization of voice components."""
        try:
            # Initialize speech recognizer (heavy operation)
            def _init_speech():
                self._speech_recognizer = SpeechRecognizer(
                    model_name=self.model_name,
                    device=self.device,
                    batch_size=self.batch_size,
                    num_workers=self.num_workers,
                    realtime_callback=self._on_realtime_transcript
                )

            # Initialize TTS engine (lighter operation)
            def _init_tts():
                self._tts_engine = TTSEngine(
                    rate=self.tts_rate,
                    volume=self.tts_volume
                )

            # Run heavy initialization in thread pool
            loop = asyncio.get_event_loop()
            await asyncio.gather(
                loop.run_in_executor(None, _init_speech),
                loop.run_in_executor(None, _init_tts)
            )

            logger.info("VoiceService components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize VoiceService: {e}")
            raise

    def _on_realtime_transcript(self, text: str) -> None:
        """Handle real-time transcription updates."""
        self._current_text = text
        if self._on_text_callback:
            self._on_text_callback(text)

    def _on_recording_start(self) -> None:
        """Handle recording start event."""
        self._is_recording = True
        if self._on_status_callback:
            self._on_status_callback("recording_started")

    def _on_silence_detected(self, is_active: bool) -> None:
        """Handle silence detection."""
        if self._on_status_callback:
            status = "speech_detected" if is_active else "silence_detected"
            self._on_status_callback(status)

    def set_callbacks(self,
                     on_text: Optional[Callable[[str], None]] = None,
                     on_status: Optional[Callable[[str], None]] = None) -> None:
        """Set callback functions for text and status updates."""
        self._on_text_callback = on_text
        self._on_status_callback = on_status

    async def start_recording_async(self) -> str:
        """Start voice recording asynchronously."""
        if not self._speech_recognizer:
            raise RuntimeError("SpeechRecognizer not initialized")

        if self._is_recording:
            raise RuntimeError("Recording already in progress")

        # Update callbacks
        self._speech_recognizer.recording_start_callback = self._on_recording_start
        self._speech_recognizer.silence_active_callback = self._on_silence_detected

        # Start recording in thread pool
        loop = asyncio.get_event_loop()
        transcribed_text = await loop.run_in_executor(
            None,
            lambda: self._speech_recognizer.start_recording(return_text=True)
        )

        self._is_recording = False
        return transcribed_text or ""

    def start_recording_sync(self) -> str:
        """Start voice recording synchronously."""
        if not self._speech_recognizer:
            raise RuntimeError("SpeechRecognizer not initialized")

        if self._is_recording:
            raise RuntimeError("Recording already in progress")

        # Update callbacks
        self._speech_recognizer.recording_start_callback = self._on_recording_start
        self._speech_recognizer.silence_active_callback = self._on_silence_detected

        # Start recording
        transcribed_text = self._speech_recognizer.start_recording(return_text=True)
        self._is_recording = False
        return transcribed_text or ""

    async def stop_recording_async(self) -> str:
        """Stop voice recording asynchronously."""
        if not self._speech_recognizer:
            raise RuntimeError("SpeechRecognizer not initialized")

        if not self._is_recording:
            return self._current_text

        # Stop recording in thread pool
        loop = asyncio.get_event_loop()
        final_text = await loop.run_in_executor(
            None,
            self._speech_recognizer.stop
        )

        self._is_recording = False
        return final_text or ""

    def stop_recording_sync(self) -> str:
        """Stop voice recording synchronously."""
        if not self._speech_recognizer:
            raise RuntimeError("SpeechRecognizer not initialized")

        if not self._is_recording:
            return self._current_text

        final_text = self._speech_recognizer.stop()
        self._is_recording = False
        return final_text or ""

    def get_current_text(self) -> str:
        """Get current transcribed text."""
        if self._speech_recognizer:
            return self._speech_recognizer.get_current_text()
        return self._current_text

    def clear_text(self) -> None:
        """Clear current transcribed text."""
        if self._speech_recognizer:
            self._speech_recognizer.clear_text()
        self._current_text = ""

    async def speak_async(self, text: str) -> None:
        """Speak text asynchronously."""
        if not self._tts_engine:
            raise RuntimeError("TTSEngine not initialized")

        if not text.strip():
            return

        # Speak in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._tts_engine.speak, text)

    def speak_sync(self, text: str) -> None:
        """Speak text synchronously."""
        if not self._tts_engine:
            raise RuntimeError("TTSEngine not initialized")

        if not text.strip():
            return

        self._tts_engine.speak(text)

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def is_tts_speaking(self) -> bool:
        """Check if TTS is currently speaking."""
        if self._tts_engine:
            return self._tts_engine.speaking_event.is_set()
        return False

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self._speech_recognizer:
            return {"error": "SpeechRecognizer not initialized"}

        stats = {
            "is_recording": self._is_recording,
            "current_text_length": len(self._current_text),
            "tts_available": self._tts_engine is not None,
            "speech_recognizer_stats": self._speech_recognizer.get_performance_stats()
        }
        return stats

    async def shutdown_async(self) -> None:
        """Shutdown voice service asynchronously."""
        logger.info("Shutting down VoiceService...")

        # Stop recording if active
        if self._is_recording:
            await self.stop_recording_async()

        # Stop TTS
        if self._tts_engine:
            def _stop_tts():
                self._tts_engine.stop()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _stop_tts)

        # Cleanup speech recognizer
        if self._speech_recognizer:
            def _cleanup_speech():
                self._speech_recognizer.stop()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _cleanup_speech)

        logger.info("VoiceService shutdown complete")

    def shutdown_sync(self) -> None:
        """Shutdown voice service synchronously."""
        logger.info("Shutting down VoiceService...")

        # Stop recording if active
        if self._is_recording:
            self.stop_recording_sync()

        # Stop TTS
        if self._tts_engine:
            self._tts_engine.stop()

        # Cleanup speech recognizer
        if self._speech_recognizer:
            self._speech_recognizer.stop()

        logger.info("VoiceService shutdown complete")

    @asynccontextmanager
    async def session(self):
        """Context manager for voice service session."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.shutdown_async()
