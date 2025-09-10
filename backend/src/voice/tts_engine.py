"""
Text-to-Speech Engine for Voice Chat
Provides offline TTS functionality with Vietnamese voice support.
"""

import sys
import threading
import time
import queue
from typing import Optional, Callable

try:
    import pyttsx3
    _HAS_PYTTSX3 = True
except Exception:
    _HAS_PYTTSX3 = False

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
        if sys.platform == "win32" and _HAS_PYTHONCOM:
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
            if sys.platform == "win32" and _HAS_PYTHONCOM:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
