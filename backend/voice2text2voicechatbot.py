import sys
import time
import queue
import threading
import collections
from typing import Callable, Optional, List, Dict, Tuple
import os
import numpy as np
import sounddevice as sd
import webrtcvad
import torch
from transformers import pipeline

# ====== (LangGraph RAG) dùng workflow sẵn trong repo ======
try:
    from src.langgraph_rag.workflows import create_rag_workflow
    from src.langgraph_rag.utils.config_utils import BaseConfig
    from src.langgraph_rag.nodes import RAGWorkflowNodes, create_default_rag_state
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False


# ====== (Tuỳ chọn) TTS offline bằng pyttsx3 ======
try:
    import pyttsx3
    _HAS_PYTTSX3 = True
except Exception:
    _HAS_PYTTSX3 = False

TextChatMessage = Dict[str, str]

try:
    import pythoncom
    _HAS_PYTHONCOM = True
except Exception:
    _HAS_PYTHONCOM = False

# Ép voice tiếng Việt (MSTTS - An)
DEFAULT_VI_VOICE_ID = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_viVN_An"

class TTSEngine:
    """TTS chạy nền (pyttsx3/SAPI), ép giọng tiếng Việt 'An' theo ID cố định.
       Có speaking_event để báo ASR biết khi TTS đang phát (anti-echo).
       Sử dụng iterate() để tránh lỗi hàng đợi."""
    def __init__(self, rate: Optional[int] = 180, volume: Optional[float] = 1.0):
        if not _HAS_PYTTSX3:
            raise RuntimeError("pyttsx3 chưa được cài. Chạy: pip install pyttsx3")

        self.rate = rate
        self.volume = volume

        self._q: "queue.Queue[str]" = queue.Queue(maxsize=100)
        self._stop = threading.Event()
        self.speaking_event = threading.Event()

        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def speak(self, text: str):
        if not text:
            return
        try:
            self._q.put_nowait(text)
        except queue.Full:
            pass

    def stop(self):
        self._stop.set()
        try:
            self._q.put_nowait("")
        except Exception:
            pass
        if self._t.is_alive():
            self._t.join(timeout=2.0)

    def _run(self):
        # Windows: khởi tạo COM trong thread dùng SAPI
        if os.name == "nt" and _HAS_PYTHONCOM:
            try:
                pythoncom.CoInitialize()
            except Exception as e:
                print(f"[TTS] CoInitialize lỗi: {e}", file=sys.stderr)

        engine = None
        try:
            engine = pyttsx3.init()
            if self.rate is not None:
                engine.setProperty("rate", self.rate)
            if self.volume is not None:
                engine.setProperty("volume", self.volume)

            # --- ÉP GIỌNG VIỆT THEO ID CỐ ĐỊNH ---
            try:
                voices = engine.getProperty("voices") or []
                if any((v.id or "").lower() == DEFAULT_VI_VOICE_ID.lower() for v in voices):
                    engine.setProperty("voice", DEFAULT_VI_VOICE_ID)
                    print(f"[TTS] Đã chọn giọng tiếng Việt: {DEFAULT_VI_VOICE_ID}")
                else:
                    print(f"[TTS] Không thấy giọng VI '{DEFAULT_VI_VOICE_ID}'. Dùng voice mặc định.",
                          file=sys.stderr)
                    for v in voices:
                        print(f"   - name='{getattr(v,'name','')}' id='{getattr(v,'id','')}' "
                              f"langs={getattr(v,'languages',None)}", file=sys.stderr)
            except Exception as e:
                print(f"[TTS] Lỗi chọn voice VI: {e}", file=sys.stderr)

            # Đăng ký callback để theo dõi trạng thái
            def on_end(name, completed):
                if completed:
                    print(f"[TTS] Finished speaking", file=sys.stderr)
                    self.speaking_event.clear()

            engine.connect('finished-utterance', on_end)

            # Xử lý hàng đợi TTS
            while not self._stop.is_set():
                try:
                    text = self._q.get(timeout=0.1)
                except queue.Empty:
                    continue
                if text == "":
                    continue
                try:
                    self.speaking_event.set()
                    engine.say(text)  # Bỏ utterance_id
                    engine.startLoop(False)
                    while engine.isBusy():
                        engine.iterate()
                        time.sleep(0.01)
                    engine.endLoop()
                except Exception as e:
                    print(f"[TTS] error: {e}", file=sys.stderr)
                    self.speaking_event.clear()
                time.sleep(0.3)  # Thời gian chờ giữa các câu

        except Exception as e:
            print(f"[TTS] init error: {e}", file=sys.stderr)
        finally:
            try:
                if engine:
                    engine.stop()
            except Exception:
                pass
            if os.name == "nt" and _HAS_PYTHONCOM:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

class StreamingASR:
    """
    Thu âm → VAD → cắt câu → ASR (PhoWhisper) → RAG → TTS.
    - Có thể dùng RAG/TTS mặc định (Bedrock + pyttsx3) hoặc cung cấp callable riêng.
    """
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        vad_mode: int = 2,
        max_silence_ms: int = 600,
        pre_speech_ms: int = 300,
        post_speech_ms: int = 300,
        model_name: str = "vinai/PhoWhisper-small",
        device_index: Optional[int] = None,
        stream_blocksize: Optional[int] = None,
        print_debug: bool = True,
        llm_func: Optional[Callable[[List[TextChatMessage]], str]] = None,
        use_tts: bool = True,
        tts_func: Optional[Callable[[str], None]] = None,
        tts_rate: Optional[int] = None,
        tts_voice: Optional[str] = None,
        tts_volume: Optional[float] = None,
        min_speech_ms: int = 300,
        energy_threshold: float = 0.008,
        mute_while_tts: bool = True,
    ):
        # ====== Audio / ASR ======
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.frame_bytes = int(sample_rate * frame_ms / 1000) * 2  # int16 -> 2 bytes
        self.vad_mode = vad_mode
        self.max_silence_ms = max_silence_ms
        self.pre_speech_frames = max(1, pre_speech_ms // frame_ms)
        self.post_speech_frames = max(1, post_speech_ms // frame_ms)

        self.device_index = device_index
        self.stream_blocksize = stream_blocksize or (self.frame_bytes // 2)
        self.print_debug = print_debug

        # PhoWhisper pipeline
        self._torch_device = 0 if torch.cuda.is_available() else -1
        self.asr = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=self._torch_device
        )
        self.vad = webrtcvad.Vad(self.vad_mode)

        # Threading
        self._audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=100)
        self._stop = threading.Event()
        self._t_rec = None
        self._t_consume = None
        self._stream: Optional[sd.InputStream] = None

        # ====== LLM (LangGraph RAG) ======
        self._llm_func = llm_func

        self._use_langgraph = _HAS_LANGGRAPH
        self._rag_app = None
        if self._use_langgraph:
            try:
                self._global_config = BaseConfig()
                _nodes = RAGWorkflowNodes(global_config=self._global_config)
                self._rag_app = create_rag_workflow(_nodes)
            except Exception as e:
                print(f"[RAG] Không khởi tạo được LangGraph workflow: {e}", file=sys.stderr)
                self._use_langgraph = False


        self.min_speech_frames = max(1, min_speech_ms // frame_ms)
        self.energy_threshold = float(energy_threshold)
        self.mute_while_tts = bool(mute_while_tts)
        
        # ====== TTS ======
        self._use_tts = use_tts
        self._tts_func = tts_func
        self._tts_engine: Optional[TTSEngine] = None

        if self._use_tts and self._tts_func is None:
            if not _HAS_PYTTSX3:
                print("[TTS] pyttsx3 chưa cài, TTS sẽ tắt.", file=sys.stderr)
                self._use_tts = False
            else:
                self._tts_engine = TTSEngine(rate=tts_rate, volume=tts_volume)

        # Bộ nhớ hội thoại
        self._history: List[TextChatMessage] = []

    @staticmethod
    def _rms_from_bytes(frame_bytes: bytes) -> float:
        if not frame_bytes:
            return 0.0
        x = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(x * x)) + 1e-9)

    def start(self) -> None:
        if self._t_rec or self._t_consume:
            raise RuntimeError("StreamingASR đang chạy.")
        self._stop.clear()
        self._t_rec = threading.Thread(target=self._record_stream, daemon=True)
        self._t_consume = threading.Thread(target=self._consumer, daemon=True)
        self._t_rec.start()
        self._t_consume.start()
        if self.print_debug:
            print("🎙️ Đang lắng nghe... (Ctrl+C để dừng)")

    def stop(self, join_timeout: float = 1.5) -> None:
        self._stop.set()
        try:
            if self._stream:
                self._stream.close()
        except Exception:
            pass
        self._stream = None
        try:
            self._audio_q.put_nowait(b"")
        except Exception:
            pass
        for t in (self._t_rec, self._t_consume):
            if t and t.is_alive():
                t.join(timeout=join_timeout)
        self._t_rec = None
        self._t_consume = None

        if self._tts_engine:
            self._tts_engine.stop()
            self._tts_engine = None

        if self.print_debug:
            print("⏹️ Đã dừng.")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        pcm16 = (indata[:, 0] * 32767).astype(np.int16)
        try:
            self._audio_q.put_nowait(pcm16.tobytes())
        except queue.Full:
            pass

    def _record_stream(self):
        dtype = "float32"
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=dtype,
                blocksize=self.stream_blocksize,
                device=self.device_index,
                callback=self._audio_callback,
            ) as stream:
                self._stream = stream
                while not self._stop.is_set():
                    time.sleep(0.05)
        except Exception as e:
            print(f"[Audio] Error: {e}", file=sys.stderr)
            self._stop.set()

    def _consumer(self):
        ring_pre = collections.deque(maxlen=self.pre_speech_frames)
        speech_frames: List[bytes] = []
        in_speech = False
        silence_ms = 0
        buf = bytearray()

        while not self._stop.is_set():
            try:
                chunk = self._audio_q.get(timeout=0.1)
            except queue.Empty:
                continue

            if self.mute_while_tts and self._tts_engine and self._tts_engine.speaking_event.is_set():
                ring_pre.clear()
                speech_frames.clear()
                in_speech = False
                silence_ms = 0
                continue

            if not chunk:
                break

            buf.extend(chunk)
            while len(buf) >= self.frame_bytes:
                frame = bytes(buf[: self.frame_bytes])
                del buf[: self.frame_bytes]

                energy_ok = self._rms_from_bytes(frame) >= self.energy_threshold
                try:
                    vad_ok = self.vad.is_speech(frame, self.sample_rate)
                except Exception:
                    vad_ok = False

                is_speech = vad_ok and energy_ok

                if not in_speech:
                    ring_pre.append(frame)
                    if is_speech:
                        in_speech = True
                        silence_ms = 0
                        speech_frames = list(ring_pre)
                else:
                    speech_frames.append(frame)
                    if is_speech:
                        silence_ms = 0
                    else:
                        silence_ms += self.frame_ms

                    if silence_ms >= self.max_silence_ms:
                        if len(speech_frames) >= self.min_speech_frames:
                            post_frames = self._drain_post_frames()
                            speech_frames.extend(post_frames[: self.post_speech_frames])
                            utter_bytes = b"".join(speech_frames)

                            in_speech = False
                            silence_ms = 0
                            ring_pre.clear()
                            speech_frames = []

                            if self.print_debug:
                                print("🛑 Kết thúc câu. Đang nhận dạng...")
                            self._pipeline_after_segment(utter_bytes)
                        else:
                            in_speech = False
                            silence_ms = 0
                            ring_pre.clear()
                            speech_frames = []

    def _drain_post_frames(self) -> List[bytes]:
        frames = []
        need_bytes = self.post_speech_frames * self.frame_bytes
        grabbed = bytearray()
        while need_bytes > 0:
            try:
                chunk = self._audio_q.get_nowait()
            except queue.Empty:
                break
            if not chunk:
                break
            grabbed.extend(chunk)
            if len(grabbed) >= need_bytes:
                break
        while len(grabbed) >= self.frame_bytes and len(frames) < self.post_speech_frames:
            frames.append(bytes(grabbed[: self.frame_bytes]))
            del grabbed[: self.frame_bytes]
        return frames

    def _pipeline_after_segment(self, utter_bytes: bytes):
        try:
            audio_np = np.frombuffer(utter_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            asr_result = self.asr(audio_np, generate_kwargs={"language": "vi"})
            user_text = (asr_result.get("text") or "").strip()
            if not user_text:
                if self.print_debug:
                    print("👉 (rỗng)") 
                return
            if self.print_debug:
                print(f"🗣️ User: {user_text}")

            reply_text = self._run_llm(user_text)
            if self.print_debug:
                print(f"🤖 LLM: {reply_text}")

            if self._use_tts and reply_text:
                self._speak(reply_text)

        except Exception as e:
            print(f"[Pipeline] error: {e}", file=sys.stderr)

    def _run_llm(self, user_text: str) -> str:
        # Nếu người dùng cung cấp hàm LLM tùy biến thì ưu tiên dùng
        if self._llm_func is not None:
            msgs = self._history + [{"role": "user", "content": user_text}]
            reply = self._llm_func(msgs)
            self._append_history(user_text, reply)
            return reply

        # Dùng LangGraph RAG nếu có
        if self._use_langgraph and self._rag_app is not None:
            # Loại system message ra khỏi conversation_history để đưa vào state
            conv_hist = [m for m in self._history if m.get("role") != "system"]
            try:
                state = create_default_rag_state(
                    question=user_text,
                    conversation_history=conv_hist  # list[{"role","content"}]
                )
                result = self._rag_app.invoke(state)
                reply_text = (result.get("final_response") or "").strip()
                if not reply_text:
                    reply_text = "Mình chưa có câu trả lời phù hợp. Bạn mô tả cụ thể hơn nhé?"
            except Exception as e:
                print(f"[RAG] invoke error: {e}", file=sys.stderr)
                reply_text = "Xin lỗi, mình đang gặp sự cố khi truy vấn tri thức."

            self._append_history(user_text, reply_text)
            return reply_text

        # Fallback (không có RAG)
        reply = f"Bạn nói: {user_text}"
        self._append_history(user_text, reply)
        return reply


    def _append_history(self, user_text: str, reply_text: str):
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": reply_text})
        if len(self._history) > 12:
            self._history = [self._history[0]] + self._history[-10:]

    def _speak(self, text: str):
        if self._tts_func is not None:
            try:
                self._tts_func(text)
            except Exception as e:
                print(f"[TTS] custom error: {e}", file=sys.stderr)
            return

        if self._tts_engine is not None:
            self._tts_engine.speak(text)

if __name__ == "__main__":
    asr = StreamingASR(
        sample_rate=16000,
        frame_ms=30,
        vad_mode=1,
        max_silence_ms=1000,
        pre_speech_ms=300,
        post_speech_ms=300,
        print_debug=True,
        llm_func=None,
        use_tts=True,
        tts_func=None,
        tts_rate=180,
        tts_voice=None,
        tts_volume=1.0,

        min_speech_ms=500,
    )

    try:
        asr.start()
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⏹️ Dừng.")
    finally:
        asr.stop()