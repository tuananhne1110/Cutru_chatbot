import asyncio
import logging
import os
import struct
import threading
import time
from collections import namedtuple
from queue import Queue
from typing import Callable, Generator, Optional
import torch

import numpy as np
# VietVoice-TTS integration
from torch.serialization import add_safe_globals
try:
    from TTS.tts.models.xtts import XttsAudioConfig
    add_safe_globals([XttsAudioConfig])
except ImportError:
    pass
# RealtimeTTS integration for TextToAudioStream
try:
    from RealtimeTTS import TextToAudioStream
    REALTIMETTS_AVAILABLE = True
except ImportError:
    TextToAudioStream = None
    REALTIMETTS_AVAILABLE = False

# Optional VietVoice-TTS integration
try:
    # Prefer function API; class API is optional
    from vietvoicetts import synthesize as vietvoice_synthesize  # type: ignore
    try:
        from vietvoicetts import TTSApi, ModelConfig  # type: ignore
    except Exception:
        TTSApi, ModelConfig = None, None  # type: ignore
    VIETVOICE_AVAILABLE = True
except Exception:
    VIETVOICE_AVAILABLE = False

# Optional pyttsx3 integration (offline, cross-platform TTS)
try:
    import pyttsx3  # type: ignore
    PYTTSX3_AVAILABLE = True
except Exception:
    pyttsx3 = None  # type: ignore
    PYTTSX3_AVAILABLE = False

# Optional gTTS integration (Google Text-to-Speech, online)
try:
    from gtts import gTTS  # type: ignore
    GTTS_AVAILABLE = True
except Exception:
    gTTS = None  # type: ignore
    GTTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default configuration constants
START_ENGINE = "gtts"
Silence = namedtuple("Silence", ("comma", "sentence", "default"))
ENGINE_SILENCES = {
    "vietvoice": Silence(comma=0.3, sentence=0.6, default=0.3),
    "coqui": Silence(comma=0.2, sentence=0.4, default=0.2),
    "pyttsx3": Silence(comma=0.2, sentence=0.4, default=0.2),
    "gtts": Silence(comma=0.2, sentence=0.4, default=0.2),
}
# Stream chunk sizes influence latency vs. throughput trade-offs
QUICK_ANSWER_STREAM_CHUNK_SIZE = 2  # Giảm hơn nữa để tăng tốc độ
FINAL_ANSWER_STREAM_CHUNK_SIZE = 8  # Giảm hơn nữa để tăng tốc độ

 

class AudioProcessor:
    """
    Manages Text-to-Speech (TTS) synthesis using VietVoice engine.

    This class initializes the VietVoice TTS engine,
    configures it for streaming output, measures initial latency (TTFT),
    and provides methods to synthesize audio from text strings or generators,
    placing the resulting audio chunks into a queue. It handles dynamic
    stream parameter adjustments and manages the synthesis lifecycle, including
    optional callbacks upon receiving the first audio chunk.
    """
    def __init__(
            self,
            engine: str = START_ENGINE,
            orpheus_model: str = "orpheus-3b-0.1-ft-Q8_0-GGUF/orpheus-3b-0.1-ft-q8_0.gguf",
        ) -> None:
        """
        Initializes the AudioProcessor with VietVoice TTS engine.

        Sets up the VietVoice engine and performs an initial synthesis to measure Time To First Audio chunk (TTFA).

        Args:
            engine: The name of the TTS engine to use (only "vietvoice" supported).
            orpheus_model: Not used (kept for compatibility).
        """
        self.engine_name = engine
        self.stop_event = threading.Event()
        self.finished_event = threading.Event()
        self.audio_chunks = asyncio.Queue() # Queue for synthesized audio output


        # Initialize tts_inference_time early to prevent AttributeError
        self.tts_inference_time = 0

        # Pick silence profile; default to coqui-like timing if unknown
        self.silence = ENGINE_SILENCES.get(engine, Silence(comma=0.2, sentence=0.4, default=0.2))
        self.current_stream_chunk_size = QUICK_ANSWER_STREAM_CHUNK_SIZE # Initial chunk size

        logger.info(f"👄⚙️ AudioProcessor initializing with engine='{engine}'")

        # Dynamically load and configure the selected TTS engine
        if engine == "vietvoice":
            # VietVoice uses offline file synthesis via its Python API.
            # No realtime engine object is created here; synthesis happens in synthesize().
            if VIETVOICE_AVAILABLE:
                self.engine = None
                self.engine_name = "vietvoice"
            else:
                # VietVoice not available
                logger.error("👄💥 VietVoice-TTS not installed. Please install https://github.com/nguyenvulebinh/VietVoice-TTS")
                raise RuntimeError("VietVoice-TTS not available")
        elif engine == "coqui":
            # Coqui TTS initialization
            try:
                # Work around PyTorch 2.6+ safe-loading by allowlisting XTTS config class
                try:
                    from torch.serialization import add_safe_globals  # type: ignore
                    from TTS.tts.configs.xtts_config import XttsConfig  # type: ignore
                    add_safe_globals([XttsConfig])
                except Exception:
                    pass
                from TTS.api import TTS  # type: ignore  # Lazy import to avoid static warning if package missing
                # Use multilingual XTTS v2 (supports Vietnamese via language parameter)
                self.engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
                self.engine_name = "coqui"
                # Configure default language and speaker settings from environment
                self.coqui_language = os.getenv("COQUI_LANGUAGE", "vi").strip() or "vi"
                self.coqui_speaker_wav = os.getenv("COQUI_SPEAKER_WAV", "").strip() or None
                self.coqui_speaker = os.getenv("COQUI_SPEAKER", "").strip() or None
                if not (self.coqui_speaker_wav or self.coqui_speaker):
                    logger.warning("👄⚠️ Coqui XTTS v2 requires a speaker. Set COQUI_SPEAKER_WAV (recommended) or COQUI_SPEAKER. Using no speaker will likely fail.")
                logger.info("👄🚀 Coqui TTS initialized with XTTS v2 (multilingual)")
            except Exception as e:
                logger.error(f"👄💥 Coqui TTS initialization failed: {e}")
                raise RuntimeError("Coqui TTS not available")
        elif engine == "pyttsx3":
            # pyttsx3 TTS initialization
            try:
                if not PYTTSX3_AVAILABLE:
                    raise RuntimeError("pyttsx3 not installed")
                driver_name = os.getenv("PYTTSX3_DRIVER", "").strip() or None
                self.engine = pyttsx3.init(driver_name)
                self.engine_name = "pyttsx3"
                # Configure voice, rate, volume via env
                desired_voice = os.getenv("PYTTSX3_VOICE", "").strip()
                try:
                    voices = self.engine.getProperty("voices")
                except Exception:
                    voices = []
                chosen_voice_id = None
                if voices:
                    if desired_voice:
                        dv_lower = desired_voice.lower()
                        for v in voices:
                            vid = getattr(v, "id", "")
                            vname = getattr(v, "name", "")
                            langs = getattr(v, "languages", [])
                            if dv_lower in (vid or "").lower() or dv_lower in (vname or "").lower():
                                chosen_voice_id = vid
                                break
                            # Also allow matching language code substrings
                            if any(isinstance(l, (bytes, bytearray)) and dv_lower in l.decode(errors="ignore").lower() for l in (langs or [])):
                                chosen_voice_id = vid
                                break
                    else:
                        # Auto-select Vietnamese voice if available
                        prefer_lang = (os.getenv("PYTTSX3_PREFER_LANG", "vi").strip() or "vi").lower()
                        preferred_ids = ["vi", f"{prefer_lang}-vn-x-central", f"{prefer_lang}-vn-x-south"]
                        # Try match by id/name first
                        for code in preferred_ids:
                            code = code.lower()
                            for v in voices:
                                vid = getattr(v, "id", "") or ""
                                vname = getattr(v, "name", "") or ""
                                if code in vid.lower() or code in vname.lower():
                                    chosen_voice_id = vid
                                    break
                                # Also check language metadata
                                langs = getattr(v, "languages", []) or []
                                for l in langs:
                                    if isinstance(l, (bytes, bytearray)):
                                        ls = l.decode(errors="ignore").lower()
                                    else:
                                        ls = str(l).lower()
                                    if code in ls:
                                        chosen_voice_id = vid
                                        break
                                if chosen_voice_id:
                                    break
                            if chosen_voice_id:
                                break
                self.pyttsx3_selected_voice_id = None
                if chosen_voice_id:
                    try:
                        self.engine.setProperty("voice", chosen_voice_id)
                        self.pyttsx3_selected_voice_id = chosen_voice_id
                        logger.info(f"👄🔤 pyttsx3 selected voice id='{chosen_voice_id}'.")
                    except Exception:
                        logger.warning(f"👄⚠️ pyttsx3 could not set voice id '{chosen_voice_id}'.")
                elif desired_voice:
                    logger.warning(f"👄⚠️ pyttsx3 voice '{desired_voice}' not found. Using default voice.")

                try:
                    rate_env = os.getenv("PYTTSX3_RATE", "").strip()
                    if rate_env:
                        self.engine.setProperty("rate", int(rate_env))
                except Exception:
                    logger.warning("👄⚠️ pyttsx3 could not set rate from PYTTSX3_RATE.")

                try:
                    volume_env = os.getenv("PYTTSX3_VOLUME", "").strip()
                    if volume_env:
                        vol = float(volume_env)
                        vol = max(0.0, min(1.0, vol))
                        self.engine.setProperty("volume", vol)
                except Exception:
                    logger.warning("👄⚠️ pyttsx3 could not set volume from PYTTSX3_VOLUME.")

                logger.info("👄🚀 pyttsx3 TTS initialized")
            except Exception as e:
                logger.error(
                    "👄💥 pyttsx3 TTS initialization failed: %s. On Linux/WSL, install eSpeak-ng (e.g., 'sudo apt-get install -y espeak-ng libespeak-ng1 libespeak-ng-dev') and optionally set PYTTSX3_DRIVER=espeak.",
                    e,
                )
                raise RuntimeError("pyttsx3 TTS not available")
        elif engine == "gtts":
            # gTTS TTS initialization (no persistent engine object)
            try:
                if not GTTS_AVAILABLE:
                    raise RuntimeError("gTTS not installed")
                self.engine = None
                self.engine_name = "gtts"
                # Configure gTTS params via env
                self.gtts_lang = os.getenv("GTTS_LANG", "vi").strip() or "vi"
                self.gtts_tld = os.getenv("GTTS_TLD", "com.vn").strip() or "com.vn"  # regional voice
                self.gtts_slow = os.getenv("GTTS_SLOW", "false").strip().lower() in ("1", "true", "yes", "y", "on")
                logger.info(f"👄🚀 gTTS initialized (lang='{self.gtts_lang}', tld='{self.gtts_tld}', slow={self.gtts_slow})")
            except Exception as e:
                logger.error(f"👄💥 gTTS initialization failed: {e}")
                raise RuntimeError("gTTS not available")
        else:
            raise ValueError(f"Unsupported engine: {engine}")


        # Initialize the RealtimeTTS stream 
        if self.engine_name not in ("vietvoice", "coqui", "pyttsx3", "gtts"):
            if not REALTIMETTS_AVAILABLE:
                logger.error("👄💥 RealtimeTTS not installed. Please install https://github.com/Erutaner/RealtimeTTS")
                raise RuntimeError("RealtimeTTS not available")
            self.stream = TextToAudioStream(
                self.engine,
                muted=True, # Do not play audio directly
                playout_chunk_size=4096, # Internal chunk size for processing
                on_audio_stream_stop=self.on_audio_stream_stop,
            )

        # No streaming engine initialization for VietVoice

        # Prewarm the engine (not applicable for VietVoice/Coqui/pyttsx3)
        if self.engine_name not in ("vietvoice", "coqui", "pyttsx3", "gtts"):
            self.stream.feed("prewarm")
            play_kwargs = dict(
                log_synthesized_text=False, # Don't log prewarm text
                muted=True,
                fast_sentence_fragment=False,
                comma_silence_duration=self.silence.comma,
                sentence_silence_duration=self.silence.sentence,
                default_silence_duration=self.silence.default,
                force_first_fragment_after_words=999999, 
            )
            self.stream.play(**play_kwargs) # Synchronous play for prewarm
            # Wait for prewarm to finish (indicated by on_audio_stream_stop)
            while self.stream.is_playing():
                time.sleep(0.01)
            self.finished_event.wait() # Wait for stop callback
            self.finished_event.clear()

        # Measure Time To First Audio (TTFA)
        if self.engine_name not in ("vietvoice", "coqui", "pyttsx3", "gtts"):
            start_time = time.time()
            ttfa = None
            def on_audio_chunk_ttfa(chunk: bytes):
                nonlocal ttfa
                if ttfa is None:
                    ttfa = time.time() - start_time
                    logger.debug(f"👄⏱️ TTFA measurement first chunk arrived, TTFA: {ttfa:.2f}s.")

            self.stream.feed("This is a test sentence to measure the time to first audio chunk.")
            play_kwargs_ttfa = dict(
                on_audio_chunk=on_audio_chunk_ttfa,
                log_synthesized_text=False, 
                muted=True,
                fast_sentence_fragment=False,
                comma_silence_duration=self.silence.comma,
                sentence_silence_duration=self.silence.sentence,
                default_silence_duration=self.silence.default,
                force_first_fragment_after_words=999999,
            )
            self.stream.play_async(**play_kwargs_ttfa)

            # Wait until the first chunk arrives or stream finishes
            while ttfa is None and (self.stream.is_playing() or not self.finished_event.is_set()):
                time.sleep(0.01)
            self.stream.stop() # Ensure stream stops cleanly

            # Wait for stop callback if it hasn't fired yet
            if not self.finished_event.is_set():
                self.finished_event.wait(timeout=2.0) # Add timeout for safety
            self.finished_event.clear()

            if ttfa is not None:
                logger.debug(f"👄⏱️ TTFA measurement complete. TTFA: {ttfa:.2f}s.")
                self.tts_inference_time = ttfa * 1000  # Store as ms
            else:
                logger.warning("👄⚠️ TTFA measurement failed (no audio chunk received).")
                self.tts_inference_time = 0
        
        else:
            # Static TTFA estimates for non-streaming engines
            if self.engine_name == "vietvoice":
                self.tts_inference_time = 800
            elif self.engine_name == "coqui":
                self.tts_inference_time = 500
            elif self.engine_name == "pyttsx3":
                self.tts_inference_time = 600
            elif self.engine_name == "gtts":
                self.tts_inference_time = 900

        # Callbacks to be set externally if needed
        self.on_first_audio_chunk_synthesize: Optional[Callable[[], None]] = None

    def on_audio_stream_stop(self) -> None:
        """
        Callback executed when the RealtimeTTS audio stream stops processing.

        Logs the event and sets the `finished_event` to signal completion or stop.
        """
        logger.info("👄🛑 Audio stream stopped.")
        self.finished_event.set()

    def synthesize(
            self,
            text: str,
            audio_chunks: Queue, 
            stop_event: threading.Event,
            generation_string: str = "",
        ) -> bool:
        """
        Synthesizes audio from a complete text string and puts chunks into a queue.

        Feeds the entire text string to the TTS engine. As audio chunks are generated,
        they are potentially buffered initially for smoother streaming and then put
        into the provided queue. Synthesis can be interrupted via the stop_event.
        Triggers the
        `on_first_audio_chunk_synthesize` callback when the first valid audio chunk is queued.

        Args:
            text: The text string to synthesize.
            audio_chunks: The queue to put the resulting audio chunks (bytes) into.
                          This should typically be the instance's `self.audio_chunks`.
            stop_event: A threading.Event to signal interruption of the synthesis.
                        This should typically be the instance's `self.stop_event`.
            generation_string: An optional identifier string for logging purposes.

        Returns:
            True if synthesis completed fully, False if interrupted by stop_event.
        """


        if self.engine_name == "vietvoice":
            # VietVoice: synthesize to WAV file then stream PCM chunks
            if not VIETVOICE_AVAILABLE:
                logger.error("👄💥 VietVoice engine requested but not available")
                return False
            try:
                import tempfile
                import os as _os
                import onnxruntime
                import numpy as _np
                # Optional configuration via env vars
                vv_gender = _os.getenv("VIETVOICE_GENDER")
                vv_area = _os.getenv("VIETVOICE_AREA")
                vv_emotion = _os.getenv("VIETVOICE_EMOTION")
                vv_ref_audio = _os.getenv("VIETVOICE_REFERENCE_AUDIO")
                vv_ref_text = _os.getenv("VIETVOICE_REFERENCE_TEXT")

                # Log available providers
                available_providers = onnxruntime.get_available_providers()
                logger.info(f"👄🔧 Available ONNX providers: {available_providers}")
                
                # Try GPU first, fallback to CPU if needed
                if 'TensorrtExecutionProvider' in available_providers:
                    logger.info("👄🚀 VietVoice-TTS will use GPU (CUDA)")
                    os.environ["ONNXRUNTIME_PROVIDER"] = "TensorrtExecutionProvider"
                else:
                    logger.info("👄💻 VietVoice-TTS will use CPU")
                    os.environ["ONNXRUNTIME_PROVIDER"] = "CPUExecutionProvider"

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                    synth_kwargs = {}
                    if vv_gender: synth_kwargs["gender"] = vv_gender
                    if vv_area: synth_kwargs["area"] = vv_area
                    if vv_emotion: synth_kwargs["emotion"] = vv_emotion
                    if vv_ref_audio: synth_kwargs["reference_audio"] = vv_ref_audio
                    if vv_ref_text: synth_kwargs["reference_text"] = vv_ref_text
                    
                    try:
                        logger.info(f"👄▶️ {generation_string} VietVoice synthesizing to file…")
                        duration = vietvoice_synthesize(text, tmp.name, **synth_kwargs)  # returns seconds
                    except Exception as e:
                        logger.error(f"👄💥 VietVoice synthesis error: {e}")
                        return False
                    logger.info(f"👄✅ {generation_string} VietVoice synthesized {duration:.2f}s of audio.")

                    # Read WAV to PCM int16 mono 24k
                    try:
                        import soundfile as sf  # type: ignore
                        audio_np, sr = sf.read(tmp.name, dtype='float32', always_2d=False)
                    except Exception:
                        import wave
                        with wave.open(tmp.name, 'rb') as wf:
                            sr = wf.getframerate()
                            nframes = wf.getnframes()
                            nch = wf.getnchannels()
                            sw = wf.getsampwidth()
                            raw = wf.readframes(nframes)
                        if sw == 2:
                            audio_np = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
                        elif sw == 4:
                            audio_np = _np.frombuffer(raw, dtype=_np.int32).astype(_np.float32) / (2**31)
                        else:
                            audio_np = _np.frombuffer(raw, dtype=_np.uint8).astype(_np.float32)
                            audio_np = (audio_np - 128.0) / 128.0
                        if nch == 2:
                            audio_np = audio_np.reshape(-1, 2).mean(axis=1)

                    if audio_np.ndim > 1:
                        audio_np = audio_np.mean(axis=1)

                    target_sr = 24000
                    if sr != target_sr and len(audio_np) > 0:
                        # Simple linear resample
                        target_len = int(round(len(audio_np) * target_sr / sr))
                        x_old = _np.linspace(0.0, 1.0, num=len(audio_np), endpoint=False)
                        x_new = _np.linspace(0.0, 1.0, num=target_len, endpoint=False)
                        audio_np = _np.interp(x_new, x_old, audio_np).astype(_np.float32)

                    # Float32 [-1,1] -> int16
                    audio_int16 = _np.clip(audio_np, -1.0, 1.0)
                    audio_int16 = (audio_int16 * 32767.0).astype(_np.int16)
                    pcm_bytes = audio_int16.tobytes()
                        
                    # Stream as chunks - smaller chunks for lower latency
                    BPS = 2
                    chunk_samples = 512  # Giảm chunk size hơn nữa để giảm độ trễ
                    pos = 0
                    first_fired = False
                    while pos < len(pcm_bytes):
                            if stop_event.is_set():
                                logger.info(f"👄🛑 {generation_string} VietVoice synthesis aborted by stop_event.")
                                break
                            end = min(pos + chunk_samples * BPS, len(pcm_bytes))
                            chunk = pcm_bytes[pos:end]
                            pos = end
                            try:
                                audio_chunks.put_nowait(chunk)
                                if not first_fired and self.on_first_audio_chunk_synthesize:
                                    self.on_first_audio_chunk_synthesize()
                                    first_fired = True
                            except asyncio.QueueFull:
                                logger.warning(f"👄⚠️ {generation_string} VietVoice audio queue full, dropping chunk.")
                    return not stop_event.is_set()
            except Exception as e:
                logger.error(f"👄💥 VietVoice synthesis error: {e}")
                return False


        elif self.engine_name == "coqui":
            # Coqui TTS: synthesize to WAV per sentence and stream
            try:
                import tempfile
                import os as _os
                import numpy as _np
                import re as _re
                
                # Split text into sentence-like chunks for faster first audio
                sentences = _re.findall(r"[^.!?…]+[.!?…]?\s*", text, flags=_re.UNICODE) or [text]
                first_fired = False
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                    for idx, sentence in enumerate(sentences, start=1):
                        if stop_event.is_set():
                            logger.info(f"👄🛑 {generation_string} Coqui synthesis aborted before sentence {idx}.")
                            break
                        s = sentence.strip()
                        if not s:
                            continue
                        try:
                            logger.info(f"👄▶️ {generation_string} Coqui synthesizing sentence {idx}/{len(sentences)}…")
                            # Build kwargs for XTTS v2 call
                            _tts_kwargs = {"text": s, "file_path": tmp.name}
                            # Prefer configured language, fallback handled in __init__
                            if getattr(self, "coqui_language", None):
                                _tts_kwargs["language"] = self.coqui_language
                            # Provide speaker for multi-speaker model
                            if getattr(self, "coqui_speaker_wav", None):
                                _tts_kwargs["speaker_wav"] = self.coqui_speaker_wav
                            elif getattr(self, "coqui_speaker", None):
                                _tts_kwargs["speaker"] = self.coqui_speaker
                            # Call TTS with assembled kwargs, try fallback without language if needed
                            try:
                                self.engine.tts_to_file(**_tts_kwargs)
                            except TypeError:
                                _tts_kwargs.pop("language", None)
                                self.engine.tts_to_file(**_tts_kwargs)
                        except Exception as e:
                            logger.error(f"👄💥 Coqui synthesis error (sentence {idx}): {e}")
                            return False
                        # Read WAV and stream
                        try:
                            import soundfile as sf  # type: ignore
                            audio_np, sr = sf.read(tmp.name, dtype='float32', always_2d=False)
                        except Exception:
                            import wave
                            with wave.open(tmp.name, 'rb') as wf:
                                sr = wf.getframerate()
                                nframes = wf.getnframes()
                                nch = wf.getnchannels()
                                sw = wf.getsampwidth()
                                raw = wf.readframes(nframes)
                            if sw == 2:
                                audio_np = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
                            elif sw == 4:
                                audio_np = _np.frombuffer(raw, dtype=_np.int32).astype(_np.float32) / (2**31)
                            else:
                                audio_np = _np.frombuffer(raw, dtype=_np.uint8).astype(_np.float32)
                                audio_np = (audio_np - 128.0) / 128.0
                            if nch == 2:
                                audio_np = audio_np.reshape(-1, 2).mean(axis=1)
                        if audio_np.ndim > 1:
                            audio_np = audio_np.mean(axis=1)
                        target_sr = 24000
                        if sr != target_sr and len(audio_np) > 0:
                            target_len = int(round(len(audio_np) * target_sr / sr))
                            x_old = _np.linspace(0.0, 1.0, num=len(audio_np), endpoint=False)
                            x_new = _np.linspace(0.0, 1.0, num=target_len, endpoint=False)
                            audio_np = _np.interp(x_new, x_old, audio_np).astype(_np.float32)
                        audio_int16 = _np.clip(audio_np, -1.0, 1.0)
                        audio_int16 = (audio_int16 * 32767.0).astype(_np.int16)
                        pcm_bytes = audio_int16.tobytes()
                        BPS = 2
                        chunk_samples = 512
                        pos = 0
                        while pos < len(pcm_bytes):
                            if stop_event.is_set():
                                logger.info(f"👄🛑 {generation_string} Coqui synthesis aborted by stop_event during sentence {idx}.")
                                break
                            end = min(pos + chunk_samples * BPS, len(pcm_bytes))
                            chunk = pcm_bytes[pos:end]
                            pos = end
                            try:
                                audio_chunks.put_nowait(chunk)
                                if not first_fired and self.on_first_audio_chunk_synthesize:
                                    self.on_first_audio_chunk_synthesize()
                                    first_fired = True
                            except asyncio.QueueFull:
                                logger.warning(f"👄⚠️ {generation_string} Coqui audio queue full, dropping chunk.")
                return not stop_event.is_set()
            except Exception as e:
                logger.error(f"👄💥 Coqui synthesis error: {e}")
                return False
        elif self.engine_name == "pyttsx3":
            # pyttsx3: synthesize to WAV per sentence and stream
            try:
                import tempfile
                import os as _os
                import numpy as _np
                import re as _re
                # Split text into sentence-like chunks
                sentences = _re.findall(r"[^.!?…]+[.!?…]?\s*", text, flags=_re.UNICODE) or [text]
                first_fired = False
                # Create a closed temp file path to avoid write failures
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
                _os.close(tmp_fd)
                try:
                    for idx, sentence in enumerate(sentences, start=1):
                        if stop_event.is_set():
                            logger.info(f"👄🛑 {generation_string} pyttsx3 synthesis aborted before sentence {idx}.")
                            break
                        s = sentence.strip()
                        if not s:
                            continue
                        try:
                            logger.info(f"👄▶️ {generation_string} pyttsx3 synthesizing sentence {idx}/{len(sentences)}…")
                            # Remove leftover file if exists
                            try:
                                if _os.path.exists(tmp_path):
                                    _os.remove(tmp_path)
                            except Exception:
                                pass
                            # Save to file and wait for completion
                            self.engine.save_to_file(s, tmp_path)
                            self.engine.runAndWait()
                            # Ensure file exists and non-empty
                            if not _os.path.exists(tmp_path) or _os.path.getsize(tmp_path) == 0:
                                raise RuntimeError("pyttsx3 produced no audio; will fallback to espeak-ng CLI")
                        except Exception as e:
                            # Fallback: try espeak-ng CLI to synthesize WAV
                            try:
                                import subprocess, shlex
                                espeak_voice = os.getenv("PYTTSX3_VOICE", "").strip() or (
                                    self.pyttsx3_selected_voice_id or "vi"
                                )
                                rate_env = os.getenv("PYTTSX3_RATE", "").strip()
                                rate_opt = f"-s {int(rate_env)}" if rate_env else ""
                                # espeak-ng writes WAV with -w
                                cmd = f"espeak-ng {rate_opt} -v {shlex.quote(espeak_voice)} -w {shlex.quote(tmp_path)} {shlex.quote(s)}"
                                logger.warning(f"👄⚠️ Falling back to espeak-ng CLI: {cmd}")
                                subprocess.run(cmd, shell=True, check=True)
                                if not _os.path.exists(tmp_path) or _os.path.getsize(tmp_path) == 0:
                                    logger.error(f"👄💥 espeak-ng CLI also failed to produce audio (sentence {idx}).")
                                    return False
                            except Exception as e2:
                                logger.error(f"👄💥 pyttsx3/espeak fallback error (sentence {idx}): {e2}")
                                return False
                        # Read WAV and stream
                        try:
                            import soundfile as sf  # type: ignore
                            audio_np, sr = sf.read(tmp_path, dtype='float32', always_2d=False)
                        except Exception:
                            import wave
                            with wave.open(tmp_path, 'rb') as wf:
                                sr = wf.getframerate()
                                nframes = wf.getnframes()
                                nch = wf.getnchannels()
                                sw = wf.getsampwidth()
                                raw = wf.readframes(nframes)
                            if sw == 2:
                                audio_np = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
                            elif sw == 4:
                                audio_np = _np.frombuffer(raw, dtype=_np.int32).astype(_np.float32) / (2**31)
                            else:
                                audio_np = _np.frombuffer(raw, dtype=_np.uint8).astype(_np.float32)
                                audio_np = (audio_np - 128.0) / 128.0
                            if nch == 2:
                                audio_np = audio_np.reshape(-1, 2).mean(axis=1)
                        if audio_np.ndim > 1:
                            audio_np = audio_np.mean(axis=1)
                        target_sr = 24000
                        if sr != target_sr and len(audio_np) > 0:
                            target_len = int(round(len(audio_np) * target_sr / sr))
                            x_old = _np.linspace(0.0, 1.0, num=len(audio_np), endpoint=False)
                            x_new = _np.linspace(0.0, 1.0, num=target_len, endpoint=False)
                            audio_np = _np.interp(x_new, x_old, audio_np).astype(_np.float32)
                        audio_int16 = _np.clip(audio_np, -1.0, 1.0)
                        audio_int16 = (audio_int16 * 32767.0).astype(_np.int16)
                        pcm_bytes = audio_int16.tobytes()
                        BPS = 2
                        chunk_samples = 512
                        pos = 0
                        while pos < len(pcm_bytes):
                            if stop_event.is_set():
                                logger.info(f"👄🛑 {generation_string} pyttsx3 synthesis aborted by stop_event during sentence {idx}.")
                                break
                            end = min(pos + chunk_samples * BPS, len(pcm_bytes))
                            chunk = pcm_bytes[pos:end]
                            pos = end
                            try:
                                audio_chunks.put_nowait(chunk)
                                if not first_fired and self.on_first_audio_chunk_synthesize:
                                    self.on_first_audio_chunk_synthesize()
                                    first_fired = True
                            except asyncio.QueueFull:
                                logger.warning(f"👄⚠️ {generation_string} pyttsx3 audio queue full, dropping chunk.")
                finally:
                    try:
                        if _os.path.exists(tmp_path):
                            _os.remove(tmp_path)
                    except Exception:
                        pass
                return not stop_event.is_set()
            except Exception as e:
                logger.error(f"👄💥 pyttsx3 synthesis error: {e}")
                return False
        elif self.engine_name == "gtts":
            # gTTS: synthesize MP3 per sentence and stream as PCM
            try:
                import tempfile
                import os as _os
                import numpy as _np
                import re as _re
                # Split text into sentence-like chunks
                sentences = _re.findall(r"[^.!?…]+[.!?…]?\s*", text, flags=_re.UNICODE) or [text]
                first_fired = False
                # Prepare temp files
                mp3_fd, mp3_path = tempfile.mkstemp(suffix=".mp3")
                _os.close(mp3_fd)
                wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
                _os.close(wav_fd)
                try:
                    for idx, sentence in enumerate(sentences, start=1):
                        if stop_event.is_set():
                            logger.info(f"👄🛑 {generation_string} gTTS synthesis aborted before sentence {idx}.")
                            break
                        s = sentence.strip()
                        if not s:
                            continue
                        try:
                            logger.info(f"👄▶️ {generation_string} gTTS synthesizing sentence {idx}/{len(sentences)}…")
                            # Remove leftovers
                            try:
                                if _os.path.exists(mp3_path): _os.remove(mp3_path)
                            except Exception:
                                pass
                            try:
                                if _os.path.exists(wav_path): _os.remove(wav_path)
                            except Exception:
                                pass
                            # Generate MP3 via gTTS
                            tts = gTTS(text=s, lang=self.gtts_lang, tld=self.gtts_tld, slow=self.gtts_slow)  # type: ignore
                            tts.save(mp3_path)
                        except Exception as e:
                            logger.error(f"👄💥 gTTS synthesis error (sentence {idx}): {e}")
                            return False
                        # Decode MP3 -> PCM 24k mono
                        audio_np = None
                        sr = 24000
                        try:
                            from pydub import AudioSegment  # type: ignore
                            seg = AudioSegment.from_file(mp3_path, format='mp3')
                            seg = seg.set_channels(1).set_frame_rate(sr).set_sample_width(2)
                            pcm_bytes = seg.raw_data
                            # stream pcm_bytes directly
                            BPS = 2
                            chunk_samples = 512
                            pos = 0
                            while pos < len(pcm_bytes):
                                if stop_event.is_set():
                                    logger.info(f"👄🛑 {generation_string} gTTS synthesis aborted by stop_event during sentence {idx}.")
                                    break
                                end = min(pos + chunk_samples * BPS, len(pcm_bytes))
                                chunk = pcm_bytes[pos:end]
                                pos = end
                                try:
                                    audio_chunks.put_nowait(chunk)
                                    if not first_fired and self.on_first_audio_chunk_synthesize:
                                        self.on_first_audio_chunk_synthesize()
                                        first_fired = True
                                except asyncio.QueueFull:
                                    logger.warning(f"👄⚠️ {generation_string} gTTS audio queue full, dropping chunk.")
                            continue
                        except Exception:
                            # Fallback to ffmpeg CLI to decode to WAV
                            try:
                                import subprocess, shlex
                                cmd = f"ffmpeg -y -hide_banner -loglevel error -i {shlex.quote(mp3_path)} -ac 1 -ar {sr} {shlex.quote(wav_path)}"
                                subprocess.run(cmd, shell=True, check=True)
                            except Exception as e2:
                                logger.error(f"👄💥 gTTS decode error (ffmpeg) for sentence {idx}: {e2}")
                                return False
                        # Read WAV and stream
                        try:
                            import soundfile as sf  # type: ignore
                            audio_np, sr = sf.read(wav_path, dtype='float32', always_2d=False)
                        except Exception:
                            import wave
                            with wave.open(wav_path, 'rb') as wf:
                                sr = wf.getframerate()
                                nframes = wf.getnframes()
                                nch = wf.getnchannels()
                                sw = wf.getsampwidth()
                                raw = wf.readframes(nframes)
                            if sw == 2:
                                audio_np = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
                            elif sw == 4:
                                audio_np = _np.frombuffer(raw, dtype=_np.int32).astype(_np.float32) / (2**31)
                            else:
                                audio_np = _np.frombuffer(raw, dtype=_np.uint8).astype(_np.float32)
                                audio_np = (audio_np - 128.0) / 128.0
                            if nch == 2:
                                audio_np = audio_np.reshape(-1, 2).mean(axis=1)
                        if audio_np.ndim > 1:
                            audio_np = audio_np.mean(axis=1)
                        target_sr = 24000
                        if sr != target_sr and len(audio_np) > 0:
                            target_len = int(round(len(audio_np) * target_sr / sr))
                            x_old = _np.linspace(0.0, 1.0, num=len(audio_np), endpoint=False)
                            x_new = _np.linspace(0.0, 1.0, num=target_len, endpoint=False)
                            audio_np = _np.interp(x_new, x_old, audio_np).astype(_np.float32)
                        audio_int16 = _np.clip(audio_np, -1.0, 1.0)
                        audio_int16 = (audio_int16 * 32767.0).astype(_np.int16)
                        pcm_bytes = audio_int16.tobytes()
                        BPS = 2
                        chunk_samples = 512
                        pos = 0
                        while pos < len(pcm_bytes):
                            if stop_event.is_set():
                                logger.info(f"👄🛑 {generation_string} gTTS synthesis aborted by stop_event during sentence {idx}.")
                                break
                            end = min(pos + chunk_samples * BPS, len(pcm_bytes))
                            chunk = pcm_bytes[pos:end]
                            pos = end
                            try:
                                audio_chunks.put_nowait(chunk)
                                if not first_fired and self.on_first_audio_chunk_synthesize:
                                    self.on_first_audio_chunk_synthesize()
                                    first_fired = True
                            except asyncio.QueueFull:
                                logger.warning(f"👄⚠️ {generation_string} gTTS audio queue full, dropping chunk.")
                finally:
                    try:
                        if _os.path.exists(mp3_path): _os.remove(mp3_path)
                    except Exception:
                        pass
                    try:
                        if _os.path.exists(wav_path): _os.remove(wav_path)
                    except Exception:
                        pass
                return not stop_event.is_set()
            except Exception as e:
                logger.error(f"👄💥 gTTS synthesis error: {e}")
                return False
        else:
            # For engines with TextToAudioStream
            if not REALTIMETTS_AVAILABLE:
                logger.error("👄💥 RealtimeTTS not available for synthesis")
                return False
            self.stream.feed(text)
            self.finished_event.clear() # Reset finished event before starting

        # Buffering state variables
        buffer: list[bytes] = []
        good_streak: int = 0
        buffering: bool = True
        buf_dur: float = 0.0
        SR, BPS = 24000, 2 # Assumed Sample Rate and Bytes Per Sample (16-bit)
        start = time.time()
        self._quick_prev_chunk_time: float = 0.0 # Track time of previous chunk

        def on_audio_chunk(chunk: bytes):
            nonlocal buffer, good_streak, buffering, buf_dur, start
            # Check for interruption signal
            if stop_event.is_set():
                logger.info(f"👄🛑 {generation_string} Quick audio stream interrupted by stop_event. Text: {text[:50]}...")
                # We should not put more chunks, let the main loop handle stream stop
                return

            now = time.time()
            samples = len(chunk) // BPS
            play_duration = samples / SR # Duration of the current chunk



            # --- Timing and Logging ---
            if on_audio_chunk.first_call:
                on_audio_chunk.first_call = False
                self._quick_prev_chunk_time = now
                ttfa_actual = now - start
                logger.info(f"👄🚀 {generation_string} Quick audio start. TTFA: {ttfa_actual:.2f}s. Text: {text[:50]}...")
            else:
                gap = now - self._quick_prev_chunk_time
                self._quick_prev_chunk_time = now
                if gap <= play_duration * 1.1: # Allow small tolerance
                    # logger.debug(f"👄✅ {generation_string} Quick chunk ok (gap={gap:.3f}s ≤ {play_duration:.3f}s). Text: {text[:50]}...")
                    good_streak += 1
                else:
                    logger.warning(f"👄❌ {generation_string} Quick chunk slow (gap={gap:.3f}s > {play_duration:.3f}s). Text: {text[:50]}...")
                    good_streak = 0 # Reset streak on slow chunk

            put_occurred_this_call = False # Track if put happened in this specific call

            # --- Buffering Logic ---
            buffer.append(chunk) # Always append the received chunk first
            buf_dur += play_duration # Update buffer duration

            if buffering:
                # Check conditions to flush buffer and stop buffering - reduce buffering time
                if good_streak >= 1 or buf_dur >= 0.05: # Flush even faster for lower latency
                    logger.info(f"👄➡️ {generation_string} Quick Flushing buffer (streak={good_streak}, dur={buf_dur:.2f}s).")
                    for c in buffer:
                        try:
                            audio_chunks.put_nowait(c)
                            put_occurred_this_call = True
                        except asyncio.QueueFull:
                            logger.warning(f"👄⚠️ {generation_string} Quick audio queue full, dropping chunk.")
                    buffer.clear()
                    buf_dur = 0.0 # Reset buffer duration
                    buffering = False # Stop buffering mode
            else: # Not buffering, put chunk directly
                try:
                    audio_chunks.put_nowait(chunk)
                    put_occurred_this_call = True
                except asyncio.QueueFull:
                    logger.warning(f"👄⚠️ {generation_string} Quick audio queue full, dropping chunk.")


            # --- First Chunk Callback ---
            if put_occurred_this_call and not on_audio_chunk.callback_fired:
                if self.on_first_audio_chunk_synthesize:
                    try:
                        logger.info(f"👄🚀 {generation_string} Quick Firing on_first_audio_chunk_synthesize.")
                        self.on_first_audio_chunk_synthesize()
                    except Exception as e:
                        logger.error(f"👄💥 {generation_string} Quick Error in on_first_audio_chunk_synthesize callback: {e}", exc_info=True)
                # Ensure callback fires only once per synthesize call
                on_audio_chunk.callback_fired = True

        # Initialize callback state for this run
        on_audio_chunk.first_call = True
        on_audio_chunk.callback_fired = False

        play_kwargs = dict(
            log_synthesized_text=True, # Log the text being synthesized
            on_audio_chunk=on_audio_chunk,
            muted=True, # We handle audio via the queue
            fast_sentence_fragment=False, # Standard processing
            comma_silence_duration=self.silence.comma,
            sentence_silence_duration=self.silence.sentence,
            default_silence_duration=self.silence.default,
            force_first_fragment_after_words=999999, # Don't force early fragments
        )

        logger.info(f"👄▶️ {generation_string} Quick Starting synthesis. Text: {text[:50]}...")
        self.stream.play_async(**play_kwargs)

        # Wait loop for completion or interruption
        while self.stream.is_playing() or not self.finished_event.is_set():
            if stop_event.is_set():
                self.stream.stop()
                logger.info(f"👄🛑 {generation_string} Quick answer synthesis aborted by stop_event. Text: {text[:50]}...")
                # Drain remaining buffer if any? Decided against it to stop faster.
                buffer.clear()
                # Wait briefly for stop confirmation? The finished_event handles this.
                self.finished_event.wait(timeout=1.0) # Wait for stream stop confirmation
                return False # Indicate interruption
            time.sleep(0.01)

        # # If loop exited normally, check if buffer still has content (stream finished before flush)
        if buffering and buffer and not stop_event.is_set():
            logger.info(f"👄➡️ {generation_string} Quick Flushing remaining buffer after stream finished.")
            for c in buffer:
                 try:
                    audio_chunks.put_nowait(c)
                 except asyncio.QueueFull:
                    logger.warning(f"👄⚠️ {generation_string} Quick audio queue full on final flush, dropping chunk.")
            buffer.clear()

        logger.info(f"👄✅ {generation_string} Quick answer synthesis complete. Text: {text[:50]}...")
        return True # Indicate successful completion

    def synthesize_generator(
            self,
            generator: Generator[str, None, None],
            audio_chunks: Queue, # Should match self.audio_chunks type
            stop_event: threading.Event,
            generation_string: str = "",
        ) -> bool:
        """
        Synthesizes audio from a generator yielding text chunks and puts audio into a queue.

        Feeds text chunks yielded by the generator to the TTS engine. As audio chunks
        are generated, they are potentially buffered initially and then put into the
        provided queue. Synthesis can be interrupted via the stop_event.
        Triggers the
       `on_first_audio_chunk_synthesize` callback when the first valid audio chunk is queued.


        Args:
            generator: A generator yielding text chunks (strings) to synthesize.
            audio_chunks: The queue to put the resulting audio chunks (bytes) into.
                          This should typically be the instance's `self.audio_chunks`.
            stop_event: A threading.Event to signal interruption of the synthesis.
                        This should typically be the instance's `self.stop_event`.
            generation_string: An optional identifier string for logging purposes.

        Returns:
            True if synthesis completed fully, False if interrupted by stop_event.
        """


        if self.engine_name == "vietvoice":
            try:
                full_text = "".join(list(generator))
                return self.synthesize(full_text, audio_chunks, stop_event, generation_string)
            except Exception as e:
                logger.error(f"👄💥 VietVoice generator synthesis error: {e}")
                return False
        elif self.engine_name == "coqui":
            try:
                full_text = "".join(list(generator))
                return self.synthesize(full_text, audio_chunks, stop_event, generation_string)
            except Exception as e:
                logger.error(f"👄💥 Coqui generator synthesis error: {e}")
                return False
        elif self.engine_name == "pyttsx3":
            try:
                full_text = "".join(list(generator))
                return self.synthesize(full_text, audio_chunks, stop_event, generation_string)
            except Exception as e:
                logger.error(f"👄💥 pyttsx3 generator synthesis error: {e}")
                return False
        elif self.engine_name == "gtts":
            try:
                full_text = "".join(list(generator))
                return self.synthesize(full_text, audio_chunks, stop_event, generation_string)
            except Exception as e:
                logger.error(f"👄💥 gTTS generator synthesis error: {e}")
                return False

        # Feed the generator to the stream
        if not REALTIMETTS_AVAILABLE:
            logger.error("👄💥 RealtimeTTS not available for generator synthesis")
            return False
        self.stream.feed(generator)
        self.finished_event.clear() # Reset finished event

        # Buffering state variables
        buffer: list[bytes] = []
        good_streak: int = 0
        buffering: bool = True
        buf_dur: float = 0.0
        SR, BPS = 24000, 2 # Assumed Sample Rate and Bytes Per Sample
        start = time.time()
        self._final_prev_chunk_time: float = 0.0 # Separate timer for generator synthesis

        def on_audio_chunk(chunk: bytes):
            nonlocal buffer, good_streak, buffering, buf_dur, start
            if stop_event.is_set():
                logger.info(f"👄🛑 {generation_string} Final audio stream interrupted by stop_event.")
                return

            now = time.time()
            samples = len(chunk) // BPS
            play_duration = samples / SR



            # --- Timing and Logging ---
            if on_audio_chunk.first_call:
                on_audio_chunk.first_call = False
                self._final_prev_chunk_time = now
                ttfa_actual = now-start
                logger.info(f"👄🚀 {generation_string} Final audio start. TTFA: {ttfa_actual:.2f}s.")
            else:
                gap = now - self._final_prev_chunk_time
                self._final_prev_chunk_time = now
                if gap <= play_duration * 1.1:
                    # logger.debug(f"👄✅ {generation_string} Final chunk ok (gap={gap:.3f}s ≤ {play_duration:.3f}s).")
                    good_streak += 1
                else:
                    logger.warning(f"👄❌ {generation_string} Final chunk slow (gap={gap:.3f}s > {play_duration:.3f}s).")
                    good_streak = 0

            put_occurred_this_call = False

            # --- Buffering Logic ---
            buffer.append(chunk)
            buf_dur += play_duration
            if buffering:
                if good_streak >= 1 or buf_dur >= 0.05: # Same flush logic as synthesize - reduce buffering
                    logger.info(f"👄➡️ {generation_string} Final Flushing buffer (streak={good_streak}, dur={buf_dur:.2f}s).")
                    for c in buffer:
                        try:
                           audio_chunks.put_nowait(c)
                           put_occurred_this_call = True
                        except asyncio.QueueFull:
                            logger.warning(f"👄⚠️ {generation_string} Final audio queue full, dropping chunk.")
                    buffer.clear()
                    buf_dur = 0.0
                    buffering = False
            else: # Not buffering
                try:
                    audio_chunks.put_nowait(chunk)
                    put_occurred_this_call = True
                except asyncio.QueueFull:
                    logger.warning(f"👄⚠️ {generation_string} Final audio queue full, dropping chunk.")


            # --- First Chunk Callback --- (Using the same callback as synthesize)
            if put_occurred_this_call and not on_audio_chunk.callback_fired:
                if self.on_first_audio_chunk_synthesize:
                    try:
                        logger.info(f"👄🚀 {generation_string} Final Firing on_first_audio_chunk_synthesize.")
                        self.on_first_audio_chunk_synthesize()
                    except Exception as e:
                        logger.error(f"👄💥 {generation_string} Final Error in on_first_audio_chunk_synthesize callback: {e}", exc_info=True)
                on_audio_chunk.callback_fired = True

        # Initialize callback state
        on_audio_chunk.first_call = True
        on_audio_chunk.callback_fired = False

        play_kwargs = dict(
            log_synthesized_text=True, # Log text from generator
            on_audio_chunk=on_audio_chunk,
            muted=True,
            fast_sentence_fragment=False,
            comma_silence_duration=self.silence.comma,
            sentence_silence_duration=self.silence.sentence,
            default_silence_duration=self.silence.default,
            force_first_fragment_after_words=999999,
        )

        # These encourage waiting for more text before synthesizing, potentially better for generators
        play_kwargs["minimum_sentence_length"] = 20  # Giảm để bắt đầu synthesis sớm hơn
        play_kwargs["minimum_first_fragment_length"] = 20  # Giảm để bắt đầu synthesis sớm hơn

        logger.info(f"👄▶️ {generation_string} Final Starting synthesis from generator.")
        self.stream.play_async(**play_kwargs)

        # Wait loop for completion or interruption
        while self.stream.is_playing() or not self.finished_event.is_set():
            if stop_event.is_set():
                self.stream.stop()
                logger.info(f"👄🛑 {generation_string} Final answer synthesis aborted by stop_event.")
                buffer.clear()
                self.finished_event.wait(timeout=1.0) # Wait for stream stop confirmation
                return False # Indicate interruption
            time.sleep(0.01)

        # Flush remaining buffer if stream finished before flush condition met
        if buffering and buffer and not stop_event.is_set():
            logger.info(f"👄➡️ {generation_string} Final Flushing remaining buffer after stream finished.")
            for c in buffer:
                try:
                   audio_chunks.put_nowait(c)
                except asyncio.QueueFull:
                   logger.warning(f"👄⚠️ {generation_string} Final audio queue full on final flush, dropping chunk.")
            buffer.clear()

        logger.info(f"👄✅ {generation_string} Final answer synthesis complete.")
        return True # Indicate successful completion