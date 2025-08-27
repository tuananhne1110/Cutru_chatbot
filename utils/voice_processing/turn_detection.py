import logging
import time
import re
from typing import Optional, Callable

logger = logging.getLogger(__name__)

def strip_ending_punctuation(text: str) -> str:
    """
    Removes trailing punctuation marks.
    """
    sentence_end_marks = ['.', '!', '?', '。']
    text = text.rstrip()
    for char in sentence_end_marks:
        while text.endswith(char):
            text = text.rstrip(char)
    return text

def ends_with_string(text: str, s: str) -> bool:
    """
    Checks if a string ends with a specific substring, allowing for one trailing character.
    """
    if text.endswith(s):
        return True
    if len(text) > 1 and text[:-1].endswith(s):
        return True
    return False

class SimpleTurnDetection:
    """
    Simplified turn detection for Vietnamese speech.
    
    This version uses simple heuristics instead of ML models for better performance
    and easier deployment.
    """
    
    def __init__(
        self,
        on_new_waiting_time: Callable[[float, Optional[str]], None],
        base_silence_duration: float = 1.5,
        punctuation_bonus: float = 0.3,
        pipeline_latency: float = 0.5
    ):
        """
        Initialize the turn detection system.
        
        Args:
            on_new_waiting_time: Callback for when new waiting time is calculated
            base_silence_duration: Base silence duration in seconds
            punctuation_bonus: Additional time for punctuation marks
            pipeline_latency: Pipeline processing latency
        """
        self.on_new_waiting_time = on_new_waiting_time
        self.base_silence_duration = base_silence_duration
        self.punctuation_bonus = punctuation_bonus
        self.pipeline_latency = pipeline_latency
        self.current_waiting_time = -1.0
        
        # Vietnamese specific settings
        self.sentence_endings = [".", "!", "?", "。"]
        self.pause_indicators = ["...", "…"]
        
        logger.info("🎤🇻🇳 SimpleTurnDetection initialized for Vietnamese")
    
    def calculate_waiting_time(self, text: str) -> None:
        """
        Calculate appropriate waiting time based on text content.
        
        Args:
            text: The input text to analyze
        """
        if not text or not text.strip():
            return
            
        waiting_time = self.base_silence_duration
        text_stripped = text.strip()
        
        # Check for sentence endings
        has_sentence_ending = any(text_stripped.endswith(mark) for mark in self.sentence_endings)
        
        # Check for pause indicators
        has_pause_indicator = any(indicator in text_stripped for indicator in self.pause_indicators)
        
        # Adjust waiting time based on content
        if has_sentence_ending:
            if text_stripped.endswith('.'):
                waiting_time = self.base_silence_duration + 0.2  # Period: slightly longer
            elif text_stripped.endswith('!'):
                waiting_time = self.base_silence_duration + 0.1  # Exclamation: medium
            elif text_stripped.endswith('?'):
                waiting_time = self.base_silence_duration + 0.3  # Question: longer for response
        elif has_pause_indicator:
            waiting_time = self.base_silence_duration + 0.5  # Pause indicators: much longer
        else:
            # No clear ending - shorter wait
            waiting_time = self.base_silence_duration * 0.8
        
        # Ensure minimum time for pipeline processing
        min_time = self.pipeline_latency + 0.2
        waiting_time = max(waiting_time, min_time)
        
        # Only update if significantly different
        if abs(waiting_time - self.current_waiting_time) > 0.1:
            self.current_waiting_time = waiting_time
            logger.info(f"🎤⏰ New waiting time: {waiting_time:.2f}s for text: '{text[:50]}...'")
            if self.on_new_waiting_time:
                self.on_new_waiting_time(waiting_time, text)
    
    def reset(self) -> None:
        """Reset the turn detection state."""
        self.current_waiting_time = -1.0
        logger.info("🎤🔄 Turn detection reset")

class SentenceEndDetector:
    """
    Detects potential sentence endings for better voice interaction flow.
    """
    
    def __init__(self, 
                 potential_sentence_callback: Optional[Callable[[str], None]] = None,
                 similarity_threshold: float = 0.95):
        """
        Initialize sentence end detector.
        
        Args:
            potential_sentence_callback: Callback when potential sentence end is detected
            similarity_threshold: Threshold for considering texts similar
        """
        self.potential_sentence_callback = potential_sentence_callback
        self.similarity_threshold = similarity_threshold
        self.sentence_cache = []
        self.yielded_sentences = []
        
        # Vietnamese sentence endings
        self.sentence_endings = [".", "!", "?", "。"]
        self.cache_max_age = 2.0  # seconds
        self.trigger_count = 2  # number of similar detections needed
        
        logger.info("🎤📝 Sentence end detector initialized")
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        text = text.lower().strip()
        # Remove punctuation but keep alphanumeric and spaces
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are similar."""
        from difflib import SequenceMatcher
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        if not norm1 and not norm2:
            return True
        if not norm1 or not norm2:
            return False
            
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= self.similarity_threshold
    
    def detect_sentence_end(self, text: str, force_yield: bool = False) -> None:
        """
        Detect potential sentence endings.
        
        Args:
            text: Text to analyze
            force_yield: Force yielding regardless of other conditions
        """
        if not text or not text.strip():
            return
            
        text_stripped = text.strip()
        now = time.time()
        
        # Check for sentence endings
        has_ending = any(text_stripped.endswith(mark) for mark in self.sentence_endings)
        
        if not has_ending and not force_yield:
            return
        
        normalized = self._normalize_text(text_stripped)
        if not normalized:
            return
        
        # Clean old cache entries
        self.sentence_cache = [
            entry for entry in self.sentence_cache 
            if now - entry['timestamp'] <= self.cache_max_age
        ]
        
        # Find similar entry in cache
        similar_entry = None
        for entry in self.sentence_cache:
            if self._is_similar(entry['text'], normalized):
                similar_entry = entry
                break
        
        if similar_entry:
            similar_entry['count'] += 1
            similar_entry['timestamp'] = now
        else:
            similar_entry = {
                'text': normalized,
                'original': text_stripped,
                'count': 1,
                'timestamp': now
            }
            self.sentence_cache.append(similar_entry)
        
        # Check if we should yield
        should_yield = force_yield or (has_ending and similar_entry['count'] >= self.trigger_count)
        
        if should_yield:
            # Check if already yielded
            already_yielded = any(
                self._is_similar(yielded['text'], normalized)
                for yielded in self.yielded_sentences
            )
            
            if not already_yielded:
                # Add to yielded list
                self.yielded_sentences.append({
                    'text': normalized,
                    'timestamp': now
                })
                
                # Clean old yielded entries
                self.yielded_sentences = [
                    entry for entry in self.yielded_sentences
                    if now - entry['timestamp'] <= self.cache_max_age * 2
                ]
                
                logger.info(f"🎤✅ Sentence end detected: '{text_stripped}'")
                if self.potential_sentence_callback:
                    self.potential_sentence_callback(text_stripped)
    
    def reset(self) -> None:
        """Reset the detector state."""
        self.sentence_cache.clear()
        self.yielded_sentences.clear()
        logger.info("🎤🔄 Sentence end detector reset")
