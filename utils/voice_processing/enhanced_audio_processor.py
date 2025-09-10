import logging
import threading
import time
import asyncio
import numpy as np
from queue import Queue, Empty
from typing import Optional, Callable, Dict, Any
from .turn_detection import SimpleTurnDetection, SentenceEndDetector
from .text_similarity import TextSimilarity

logger = logging.getLogger(__name__)

class EnhancedAudioProcessor:
    """
    Enhanced audio processor with automatic turn detection and voice activity detection.
    
    This processor combines the existing AudioProcessor functionality with intelligent
    turn detection to automatically determine when a user has finished speaking.
    """
    
    def __init__(self, base_audio_processor, 
                 silence_threshold: float = 1.5,
                 enable_turn_detection: bool = True,
                 enable_sentence_detection: bool = True):
        """
        Initialize the enhanced audio processor.
        
        Args:
            base_audio_processor: The base AudioProcessor instance
            silence_threshold: Base silence duration before considering speech ended
            enable_turn_detection: Enable automatic turn detection
            enable_sentence_detection: Enable sentence end detection
        """
        self.base_processor = base_audio_processor
        self.silence_threshold = silence_threshold
        self.enable_turn_detection = enable_turn_detection
        self.enable_sentence_detection = enable_sentence_detection
        
        # Voice activity detection state
        self.is_listening = False
        self.is_processing = False
        self.last_audio_time = 0.0
        self.silence_start_time = 0.0
        self.current_text = ""
        self.final_text = ""
        
        # Text processing
        self.text_similarity = TextSimilarity(focus='end', n_words=3)
        
        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_partial_text: Optional[Callable[[str], None]] = None
        self.on_final_text: Optional[Callable[[str], None]] = None
        self.on_silence_detected: Optional[Callable] = None
        
        # Turn detection
        self.turn_detector = None
        if self.enable_turn_detection:
            self.turn_detector = SimpleTurnDetection(
                on_new_waiting_time=self._on_new_waiting_time,
                base_silence_duration=silence_threshold,
                pipeline_latency=0.3
            )
        
        # Sentence detection
        self.sentence_detector = None
        if self.enable_sentence_detection:
            self.sentence_detector = SentenceEndDetector(
                potential_sentence_callback=self._on_potential_sentence_end
            )
        
        # Audio monitoring thread
        self.monitoring_active = False
        self.monitor_thread = None
        
        logger.info("🎤🔧 Enhanced Audio Processor initialized")
    
    def _on_new_waiting_time(self, waiting_time: float, text: Optional[str] = None):
        """Handle new waiting time from turn detection."""
        self.silence_threshold = waiting_time
        logger.debug(f"🎤⏰ Updated silence threshold to {waiting_time:.2f}s")
    
    def _on_potential_sentence_end(self, text: str):
        """Handle potential sentence end detection."""
        logger.info(f"🎤📝 Potential sentence end: {text}")
        # Could trigger earlier processing here if needed
    
    def start_listening(self) -> bool:
        """
        Start listening for voice input.
        
        Returns:
            True if successfully started, False otherwise
        """
        if self.is_listening:
            logger.warning("🎤⚠️ Already listening")
            return False
        
        try:
            self.is_listening = True
            self.is_processing = False
            self.current_text = ""
            self.final_text = ""
            self.last_audio_time = time.time()
            self.silence_start_time = 0.0
            
            # Reset detectors
            if self.turn_detector:
                self.turn_detector.reset()
            if self.sentence_detector:
                self.sentence_detector.reset()
            
            # Start monitoring thread
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_voice_activity, daemon=True)
            self.monitor_thread.start()
            
            logger.info("🎤▶️ Started listening for voice input")
            # Don't call callbacks from threads - will be handled externally
            
            return True
            
        except Exception as e:
            logger.error(f"🎤💥 Error starting voice listening: {e}")
            self.is_listening = False
            return False
    
    def stop_listening(self) -> Optional[str]:
        """
        Stop listening and return final text.
        
        Returns:
            Final transcribed text or None if no text
        """
        if not self.is_listening:
            return self.final_text
        
        logger.info("🎤⏹️ Stopping voice listening")
        self.is_listening = False
        self.monitoring_active = False
        
        # Wait for monitoring thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        # Process any remaining text
        if self.current_text and not self.final_text:
            self.final_text = self.current_text.strip()
        
        # Note: callbacks will be handled by caller, just set flags
        self._speech_ended = True
        self._final_text_ready = bool(self.final_text)
        
        logger.info(f"🎤✅ Voice listening stopped. Final text: '{self.final_text}'")
        return self.final_text
    
    def simulate_transcription(self, text: str, is_final: bool = False):
        """
        Simulate transcription result for testing purposes.
        """
        if is_final:
            self.final_text = text
            logger.info(f"🎤✅ Simulated final text: '{text}'")
        else:
            self.current_text = text
            logger.debug(f"🎤📝 Simulated partial text: '{text}'")
    
    def process_audio_chunk(self, audio_data: bytes, 
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Process incoming audio chunk.
        
        Args:
            audio_data: Raw audio data
            metadata: Optional metadata about the audio
        """
        logger.debug(f"🎤📥 Received audio chunk: {len(audio_data)} bytes")
        
        if not self.is_listening:
            logger.warning("🎤❌ Not listening, ignoring audio chunk") 
            return
        
        try:
            # Update last audio time
            self.last_audio_time = time.time()
            
            # Check for voice activity (simple energy-based detection)
            has_voice = self._has_voice_activity(audio_data)
            logger.debug(f"🎤👁️ Voice activity detected: {has_voice}")
            
            if has_voice:
                # Reset silence timer when voice is detected
                self.silence_start_time = 0.0
                logger.debug("🎤🔊 Voice detected - resetting silence timer")
            else:
                # Start silence timer if not already started
                if self.silence_start_time == 0.0:
                    self.silence_start_time = time.time()
            
        except Exception as e:
            logger.error(f"🎤💥 Error processing audio chunk: {e}")
    
    def process_text_update(self, text: str, is_final: bool = False) -> None:
        """
        Process text update from STT.
        
        Args:
            text: Transcribed text
            is_final: Whether this is final transcription
        """
        if not self.is_listening and not is_final:
            return
        
        try:
            if is_final:
                self.final_text = text.strip()
                logger.info(f"🎤✅ Final text received: '{self.final_text}'")
                # Don't call callbacks from threads - will be handled externally
                self.stop_listening()
            else:
                # Update current text
                old_text = self.current_text
                self.current_text = text.strip()
                
                # Check if text changed significantly
                if old_text != self.current_text:
                    logger.debug(f"🎤📝 Text update: '{self.current_text}'")
                    
                    # Process with turn detection
                    if self.turn_detector and self.current_text:
                        self.turn_detector.calculate_waiting_time(self.current_text)
                    
                    # Process with sentence detection
                    if self.sentence_detector and self.current_text:
                        self.sentence_detector.detect_sentence_end(self.current_text)
                    
                    # Don't call callbacks from threads - will be handled externally
            
        except Exception as e:
            logger.error(f"🎤💥 Error processing text update: {e}")
    
    def _has_voice_activity(self, audio_data: bytes, threshold: float = 500.0) -> bool:
        """
        Simple voice activity detection based on audio energy.
        For WebM/Opus data, we use a simple heuristic.
        
        Args:
            audio_data: Raw audio data (WebM/Opus or PCM)
            threshold: Energy threshold for voice detection
            
        Returns:
            True if voice activity detected
        """
        try:
            if len(audio_data) < 2:
                return False
            
            # For WebM/Opus data, use size-based heuristic
            # Larger chunks typically indicate voice activity
            if len(audio_data) > 1000:  # WebM chunks with voice are usually larger
                return True
            
            # For PCM data, try energy calculation
            try:
                # Check if data length is compatible with int16
                if len(audio_data) % 2 == 0:
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    if audio_array.size > 0:
                        energy = np.abs(audio_array).mean()
                        return energy > threshold
            except (ValueError, TypeError):
                # Not PCM data, fallback to size heuristic
                pass
            
            return len(audio_data) > 500  # Fallback heuristic
            
        except Exception as e:
            logger.error(f"🎤💥 Error in voice activity detection: {e}")
            return False
    
    def _monitor_voice_activity(self) -> None:
        """Monitor voice activity and detect speech end."""
        logger.info("🎤👁️ Voice activity monitoring started")
        
        while self.monitoring_active and self.is_listening:
            try:
                current_time = time.time()
                
                # Check for silence timeout
                if (self.silence_start_time > 0.0 and 
                    current_time - self.silence_start_time >= self.silence_threshold):
                    
                    logger.info(f"🎤🤫 Silence detected for {self.silence_threshold:.1f}s - ending speech")
                    
                    # Force final transcription if we have current text
                    if self.current_text:
                        self.final_text = self.current_text.strip()
                        if self.sentence_detector:
                            self.sentence_detector.detect_sentence_end(self.final_text, force_yield=True)
                    
                    # Don't call callbacks from threads - will be handled externally
                    
                    # Stop listening
                    threading.Thread(target=self.stop_listening, daemon=True).start()
                    break
                
                # Check for overall timeout (safety measure)
                if current_time - self.last_audio_time > 10.0:  # 10 second timeout
                    logger.warning("🎤⏰ Voice listening timeout - stopping")
                    threading.Thread(target=self.stop_listening, daemon=True).start()
                    break
                
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                logger.error(f"🎤💥 Error in voice monitoring: {e}")
                break
        
        logger.info("🎤👁️ Voice activity monitoring stopped")
    
    def is_active(self) -> bool:
        """Check if processor is actively listening."""
        return self.is_listening
    
    def get_current_text(self) -> str:
        """Get current transcribed text."""
        return self.current_text
    
    def get_final_text(self) -> str:
        """Get final transcribed text."""
        return self.final_text
