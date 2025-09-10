"""
Speech Recognition Module for Voice-to-Text
Enhanced SpeechRecognizer with async support and real-time processing.
"""

import sounddevice as sd
import numpy as np
import sys
import torch
import webrtcvad
from transformers import pipeline
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
import gc
import asyncio
import logging
from typing import Optional, Tuple, Callable
from collections import deque

try:
    from scipy.signal import resample_poly as scipy_resample_poly
except Exception:
    scipy_resample_poly = None

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Modern Speech Recognition with async support and callback system.

    Integrates features for better real-time performance,
    async audio processing, and comprehensive callback system.
    """

    _RESAMPLE_RATIO = 3  # Resample ratio from 48kHz to 16kHz

    def __init__(self,
                 model_name: str = "vinai/PhoWhisper-medium",
                 device: Optional[int] = None,
                 batch_size: int = 16,
                 num_workers: int = 2,
                 language: str = "vi",
                 realtime_callback: Optional[Callable[[str], None]] = None,
                 recording_start_callback: Optional[Callable[[], None]] = None,
                 silence_active_callback: Optional[Callable[[bool], None]] = None,
                 pipeline_latency: float = 0.5):

        """
        Khởi tạo SpeechRecognizer với async support:
        - Tải mô hình
        - Thiết lập các hàng đợi và luồng xử lý
        - Bắt đầu luồng transcription
        - Hỗ trợ callback system cho real-time processing

        Args:
            model_name: Tên model Whisper
            device: GPU device index (None để auto-detect)
            batch_size: Kích thước batch cho xử lý
            num_workers: Số worker threads
            language: Ngôn ngữ cho transcription
            realtime_callback: Callback cho kết quả real-time
            recording_start_callback: Callback khi bắt đầu recording
            silence_active_callback: Callback cho trạng thái silence
            pipeline_latency: Độ trễ pipeline ước tính (giây)
        """

        # Xác định thiết bị dùng GPU nếu có
        self.device = device if device is not None else (0 if torch.cuda.is_available() else -1)
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.language = language
        self.pipeline_latency = pipeline_latency

        # Callback system
        self.realtime_callback = realtime_callback
        self.recording_start_callback = recording_start_callback
        self.silence_active_callback = silence_active_callback
        self.last_partial_text: Optional[str] = None

        # Async support
        self.audio_async_queue: Optional[asyncio.Queue] = None
        self._transcription_failed = False
        self.transcription_task: Optional[asyncio.Task] = None
        self.interrupted = False

        # Thiết bị ghi âm và samplerate hiện tại
        self.input_device: Optional[int] = None
        self.current_samplerate: int = 16000

        # Hàng đợi để lưu audio chưa xử lý
        self.audio_queue = queue.Queue(maxsize=10)  # Giới hạn để tránh memory leak
        # Hàng đợi để lưu kết quả text sau khi xử lý
        self.result_queue = queue.Queue()

        # Tạo thread pool để xử lý song song
        self.executor = ThreadPoolExecutor(max_workers=num_workers)

        # Prompt cho mô hình (cần có TRƯỚC khi _load_model_optimized gọi warmup)
        self.initial_prompt = (
            "Tiếng Việt. Chủ đề pháp luật, thủ tục hành chính Việt Nam. Viết có dấu, giữ dấu câu."
        )

        # Load model một lần duy nhất
        print("Đang tải model...")
        self._load_model_optimized(model_name)
        print("Model đã được tải")
        logger.info(f"Model {model_name} loaded successfully on device: {'GPU' if self.device >= 0 else 'CPU'}")

        # Khởi tạo bộ phát hiện giọng nói WebRTC (mode=2)
        self.vad = webrtcvad.Vad(2)

        # Biến dùng để lưu buffer âm thanh
        self.buffer = []
        self.last_audio = np.array([])
        self.silence_counter = 0   # Đếm số lần không phát hiện tiếng nói

        # Theo dõi hiệu suất xử lý
        self.processing_times = []

        # Biến điều khiển luồng (thread)
        self.stop_flag = threading.Event()
        # Bắt đầu một luồng riêng để xử lý transcription
        self.transcribe_thread = threading.Thread(target=self._transcribe_worker, daemon=True)
        self.transcribe_thread.start()

        self.text = ""  # Biến lưu kết quả phiên âm

        # Setup callbacks
        self._setup_callbacks()

        # Tham số phân đoạn/gom gửi (giảm độ trễ)
        self.min_segment_sec = 2.0   # gom tối thiểu ~2s
        self.max_segment_sec = 3.0   # tối đa 3s trước khi buộc gửi
        self.overlap_sec = 0.8       # chồng lấn ~0.8s giữa các lần gửi

        # VAD ring buffer ~ 200ms (khung 30ms → ~7 khung)
        self.vad_ring_ms = 200
        self.vad_ring = deque(maxlen=int(max(1, self.vad_ring_ms / 30)))

        logger.info("👂🚀 SpeechRecognizer with async support initialized.")

    def _setup_callbacks(self) -> None:
        """Sets up internal callbacks for real-time transcription."""
        def partial_transcript_callback(text: str) -> None:
            """Handles partial transcription results."""
            if text != self.last_partial_text:
                self.last_partial_text = text
                if self.realtime_callback:
                    self.realtime_callback(text)

        # Note: This would be set on an actual TranscriptionProcessor

    def _silence_active_callback_internal(self, is_active: bool) -> None:
        """Internal callback relay for silence detection status."""
        if self.silence_active_callback:
            self.silence_active_callback(is_active)

    def _on_recording_start_internal(self) -> None:
        """Internal callback relay triggered when recording starts."""
        if self.recording_start_callback:
            self.recording_start_callback()

    def abort_generation(self) -> None:
        """Signals to abort any ongoing generation process."""
        logger.info("👂🛑 Aborting generation requested.")
        self.interrupted = True

    def _select_input_device(self) -> Optional[int]:
        try:
            devices = sd.query_devices()
            # Windows: ưu tiên WASAPI input
            try:
                hostapis = sd.query_hostapis()
                wasapi_index = None
                for i, ha in enumerate(hostapis):
                    if isinstance(ha, dict) and 'name' in ha and 'wasapi' in ha['name'].lower():
                        wasapi_index = i
                        break
                if wasapi_index is not None:
                    for i, d in enumerate(devices):
                        if isinstance(d, dict) and d.get('hostapi') == wasapi_index and d.get('max_inputs', 0) > 0:
                            return i
            except Exception:
                pass

            # Default input device
            try:
                default_in = sd.query_devices(kind='input')
                if isinstance(sd.default.device, (list, tuple)):
                    return sd.default.device[0]
            except Exception:
                pass

            # Fallback: Chọn device đầu tiên có input
            for i, d in enumerate(devices):
                if isinstance(d, dict) and d.get('max_inputs', 0) > 0:
                    return i
        except Exception:
            return None
        return None

    def _detect_samplerate(self) -> int:
        try:
            if self.input_device is not None:
                info = sd.query_devices(self.input_device)
            else:
                info = sd.query_devices(kind='input')
            sr = int(info.get('default_samplerate', 16000)) if isinstance(info, dict) else 16000
            return sr or 16000
        except Exception:
            return 16000

    def _resample_to_16k(self, audio_chunk: np.ndarray, src_rate: int) -> np.ndarray:
        """Resample audio to 16kHz using scipy for better quality or fallback to interpolation."""
        if src_rate == 16000 or len(audio_chunk) == 0:
            return audio_chunk.astype(np.float32)

        # Use scipy resample_poly for better quality if available
        if scipy_resample_poly is not None and src_rate % 16000 == 0:
            try:
                ratio = src_rate // 16000
                resampled = scipy_resample_poly(audio_chunk.astype(np.float32), 1, ratio)
                return resampled.astype(np.float32)
            except Exception as e:
                logger.warning(f"Scipy resampling failed: {e}, falling back to interpolation")

        # Fallback to linear interpolation
        duration = len(audio_chunk) / float(src_rate)
        num_out = int(duration * 16000)
        if num_out <= 0:
            return audio_chunk.astype(np.float32)
        t_src = np.linspace(0.0, duration, num=len(audio_chunk), endpoint=False, dtype=np.float32)
        t_dst = np.linspace(0.0, duration, num=num_out, endpoint=False, dtype=np.float32)
        resampled = np.interp(t_dst, t_src, audio_chunk.astype(np.float32)).astype(np.float32)
        return resampled

    def process_audio_chunk(self, raw_bytes: bytes) -> np.ndarray:
        """Process raw audio bytes with improved resampling.

        Converts raw audio bytes (int16) to a 16kHz numpy array.
        Uses scipy resample_poly for better quality when available.

        Args:
            raw_bytes: Raw audio data in int16 format.

        Returns:
            Numpy array containing resampled audio at 16kHz.
        """
        raw_audio = np.frombuffer(raw_bytes, dtype=np.int16)

        if np.max(np.abs(raw_audio)) == 0:
            # Calculate expected length after resampling for silence
            expected_len = int(np.ceil(len(raw_audio) / self._RESAMPLE_RATIO))
            return np.zeros(expected_len, dtype=np.float32)

        # Convert to float32 for resampling precision
        audio_float32 = raw_audio.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

        # Use improved resampling method
        if scipy_resample_poly is not None:
            try:
                # Resample using scipy for better quality
                resampled_float = scipy_resample_poly(audio_float32, 1, self._RESAMPLE_RATIO)
                return resampled_float.astype(np.float32)
            except Exception as e:
                logger.warning(f"Scipy resampling failed: {e}, using fallback")

        # Fallback to the existing method
        return self._resample_to_16k(audio_float32, 48000)  # Assume 48kHz input

    def _load_model_optimized(self, model_name: str):
        """
        Tải mô hình speech-to-text với cấu hình tối ưu (dùng GPU nếu có).
        Làm nóng model để giảm độ trễ ban đầu.
        """
        # Sử dụng logic đơn giản như voice.py
        from transformers import WhisperProcessor, WhisperForConditionalGeneration

        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)

        # Chuyển model sang GPU nếu có
        if torch.cuda.is_available():
            self.model = self.model.cuda()
            print("Đang sử dụng GPU")
        else:
            print("Đang sử dụng CPU")

        # Làm nóng model bằng audio giả
        if torch.cuda.is_available():
            dummy_audio = np.random.random(16000).astype(np.float32)
            input_features = self.processor(
                dummy_audio,
                sampling_rate=16000,
                return_tensors="pt"
            ).input_features

            if torch.cuda.is_available():
                input_features = input_features.cuda()

            # Tạo token ids cho tiếng Việt
            forced_decoder_ids = self.processor.get_decoder_prompt_ids(
                language="vi",
                task="transcribe"
            )

            with torch.no_grad():
                _ = self.model.generate(
                    input_features,
                    forced_decoder_ids=forced_decoder_ids,
                    max_length=448,
                    num_beams=5,
                    early_stopping=True
                )
            torch.cuda.empty_cache()

        return None  # Không cần trả về pipe nữa

    def _transcribe_worker(self, timeout=0.1):
        """
        Luồng riêng chạy nền để lấy audio từ queue và xử lý phiên âm theo batch.
        Dùng multithread để tăng throughput.
        """
        pending_futures = []

        while not self.stop_flag.is_set():
            try:
                # Collect multiple audio chunks for batch processing
                batch_audio = []

                # Lấy từng đoạn audio từ queue
                while len(batch_audio) < self.batch_size and not self.stop_flag.is_set():
                    try:
                        audio_data = self.audio_queue.get(timeout=timeout) # Chờ 100ms để lấy dữ liệu
                        if audio_data is None:  # Poison pill
                            break
                        batch_audio.append(audio_data)
                    except queue.Empty:
                        break

                if batch_audio:
                    print(f"Processing batch of {len(batch_audio)} audio chunks")
                    try:
                        # Gửi batch audio để xử lý song song
                        future = self.executor.submit(self._transcribe_batch, batch_audio)
                        pending_futures.append(future)
                        logger.debug(f"Batch of {len(batch_audio)} submitted successfully")
                    except Exception as e:
                        logger.error(f"Error submitting batch: {e}")
                        # Process directly if executor is down
                        try:
                            results = self._transcribe_batch(batch_audio)
                            for result in results:
                                if result and result.strip():
                                    self.result_queue.put(result)
                        except Exception as direct_error:
                            logger.error(f"Direct processing error: {direct_error}")

                # Lấy kết quả từ các job đã hoàn thành
                completed_futures = [f for f in pending_futures if f.done()]
                for future in completed_futures:
                    try:
                        results = future.result()
                        for result in results:
                            if result and result.strip():
                                self.result_queue.put(result)
                    except Exception as e:
                        logger.error(f"Transcription error: {e}")
                    pending_futures.remove(future)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(0.1)

    def _transcribe_batch(self, batch_audio: list) -> list:
        """
        Xử lý một batch audio. Trả về danh sách kết quả text tương ứng.
        Sử dụng logic đơn giản như voice.py
        """
        start_time = time.time()
        results = []

        try:
            for audio_np in batch_audio:
                if audio_np is None or len(audio_np) == 0:
                    results.append("")
                    continue

                # Tiền xử lý audio
                input_features = self.processor(
                    audio_np.astype(np.float32),
                    sampling_rate=16000,
                    return_tensors="pt"
                ).input_features

                # Chuyển sang GPU nếu có
                if torch.cuda.is_available():
                    input_features = input_features.cuda()

                # Tạo token ids cho tiếng Việt
                forced_decoder_ids = self.processor.get_decoder_prompt_ids(
                    language="vi",
                    task="transcribe"
                )

                # Thực hiện transcription
                with torch.no_grad():
                    predicted_ids = self.model.generate(
                        input_features,
                        forced_decoder_ids=forced_decoder_ids,
                        max_length=448,
                        num_beams=5,
                        early_stopping=True
                    )

                # Decode kết quả
                transcription = self.processor.batch_decode(
                    predicted_ids,
                    skip_special_tokens=True
                )[0]

                text = transcription.strip()
                if text:
                    logger.info(f"Transcribed: '{text}'")
                    # Trigger realtime callback for partial results
                    if self.realtime_callback:
                        self.realtime_callback(text)
                results.append(text)

        except Exception as e:
            logger.error(f"Batch transcription error: {e}")
            results = [""] * len(batch_audio)

        # Lưu thời gian xử lý để theo dõi hiệu suất
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)

        # Keep only last 100 measurements
        if len(self.processing_times) > 100:
            self.processing_times = self.processing_times[-100:]

        return results

    def _enhanced_vad(self, audio_chunk: np.ndarray, fs: int) -> bool:
        """
        Phát hiện tiếng nói sử dụng VAD + mức năng lượng fallback.
        Cho phép điều chỉnh ngưỡng năng lượng theo ngữ cảnh gần đây.
        """
        try:
            # Ensure proper frame size
            frame_size = len(audio_chunk)
            audio_int16 = (audio_chunk * 32767).astype(np.int16)

            # WebRTC VAD quyết định chính + bỏ fallback siêu nhạy
            try:
                is_speech = self.vad.is_speech(audio_int16.tobytes(), fs)
            except Exception:
                is_speech = False

            # Cập nhật ring buffer quyết định
            self.vad_ring.append(is_speech)
            if len(self.vad_ring) > 0:
                votes = sum(1 for v in self.vad_ring if v)
                is_speech = votes >= (len(self.vad_ring) // 2 + 1)

            return is_speech

        except Exception as e:
            # Pure energy-based fallback với ngưỡng thấp
            energy = np.mean(audio_chunk ** 2)
            return energy > 0.0001  # Giảm ngưỡng

    def stream_callback(self, indata, frames, time_info, status):
        """
        Callback của InputStream (sounddevice).
        Thực hiện VAD, lưu âm thanh vào buffer và xử lý khi có đủ dữ liệu.
        """
        if status:
            logger.warning(f"Stream status: {status}")

        # Lấy audio từ 1 kênh (mono)
        audio_chunk = indata[:, 0].copy()
        # Nếu samplerate đầu vào khác 16k, resample về 16k cho model
        try:
            fs_in = getattr(self, 'current_samplerate', 16000)
            if fs_in != 16000:
                audio_chunk = self._resample_to_16k(audio_chunk, fs_in)
        except Exception:
            pass

        # Debug: in ra thông tin audio mỗi 100 frames
        if hasattr(self, '_frame_counter'):
            self._frame_counter += 1
        else:
            self._frame_counter = 0

        if self._frame_counter % 100 == 0:
            energy = np.mean(audio_chunk ** 2)
            logger.debug(f"Audio frame {self._frame_counter}: energy={energy:.6f}, max={np.max(np.abs(audio_chunk)):.6f}")

        # Debug: in ra tất cả audio frames để debug
        energy = np.mean(audio_chunk ** 2)
        if energy > 0.00001:  # Rất nhạy cảm
            logger.debug(f"Audio detected: frame={self._frame_counter}, energy={energy:.6f}")

        # Kiểm tra xem có phải tiếng nói không
        is_speech = self._enhanced_vad(audio_chunk, 16000)

        if is_speech:
            self.buffer.append(audio_chunk)
            self.silence_counter = 0
            logger.debug(f"Speech detected! Buffer size: {len(self.buffer)}")
            # Trigger recording start callback if this is the first speech
            if len(self.buffer) == 1:
                self._on_recording_start_internal()
        elif self.buffer:  # Only count silence after speech
            self.silence_counter += 1
            if self.silence_counter <= 10:  # Add some silence after speech
                self.buffer.append(audio_chunk)

            # Quy tắc gom: tối thiểu 2s, tối đa 3s, overlap 0.8s
            seg_sec = len(self.buffer) * 0.03
            if seg_sec >= self.min_segment_sec or len(self.buffer) >= int(self.max_segment_sec/0.03):
                logger.info(f"Processing audio segment: ~{seg_sec:.2f}s")
                # Trigger silence callback
                self._silence_active_callback_internal(False)
                full_chunk = np.concatenate(self.buffer)

                # Combine with previous audio for context
                if len(self.last_audio) > 0:
                    combined = np.concatenate([self.last_audio, full_chunk])
                else:
                    combined = full_chunk

                # Keep last overlap for next iteration
                overlap_size = int(self.overlap_sec * 16000)
                self.last_audio = full_chunk[-overlap_size:] if len(full_chunk) > overlap_size else full_chunk

                # Queue for async processing (non-blocking) with error recovery
                try:
                    if len(combined) >= 16000:  # không gửi < 1s
                        self.audio_queue.put_nowait(combined)
                        logger.debug(f"Audio queued for processing. Queue size: {self.audio_queue.qsize()}")
                except queue.Full:
                    # Drop oldest item if queue full (recovery mechanism)
                    logger.warning("Audio queue full, dropping oldest item")
                    try:
                        self.audio_queue.get_nowait()
                        if len(combined) >= 16000:
                            self.audio_queue.put_nowait(combined)
                    except queue.Empty:
                        logger.error("Queue reported full but get_nowait failed")
                except Exception as e:
                    logger.error(f"Unexpected error queuing audio: {e}")

                self.buffer.clear()
                self.silence_counter = 0
        else:
            # Trigger silence callback when transitioning to silence
            if len(self.buffer) > 0 and self.silence_counter == 1:
                self._silence_active_callback_internal(True)

    def start_recording(self, fs: int = 16000, frame_duration: int = 30, return_text: bool = True):
        """
        Bắt đầu thu âm (real-time).
        Tự động xử lý phiên âm khi có đủ âm thanh được buffer.
        """
        if frame_duration not in [10, 20, 30]:
            frame_duration = 30
            print(f"Frame duration set to {frame_duration}ms")

        self.clear_text()  # Reset text
        self.stop_flag.clear()  # Reset stop flag

        frame_size = int(fs * frame_duration / 1000)
        print(f"Starting optimized recording... Frame size (initial): {frame_size} samples @ {fs} Hz")
        print(f"Device: {'GPU' if self.device >= 0 else 'CPU'}, Workers: {self.num_workers}")
        print("Press Ctrl+C to stop recording...")

        # Thread để thu thập kết quả phiên âm
        def collect_results():
            while not self.stop_flag.is_set():
                try:
                    result = self.result_queue.get(timeout=0.5)
                    if result and result.strip():
                        # Loại bỏ dấu chấm cuối nếu có và thêm khoảng trắng
                        cleaned_result = result.rstrip('.') + " "
                        self.text += cleaned_result
                        print(f" {result}")

                    # Performance info
                    if len(self.processing_times) > 0:
                        avg_time = np.mean(self.processing_times[-10:])
                        if avg_time > 0.5:  # Warn if processing is slow
                            print(f"[Performance] Avg processing time: {avg_time:.2f}s", file=sys.stderr)

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Result collection error: {e}", file=sys.stderr)

        result_thread = threading.Thread(target=collect_results, daemon=True)
        result_thread.start()

        # Khởi tạo audio stream
        try:
            print("Initializing audio stream...")
            # Chọn input device an toàn trong WSL/PulseAudio
            self.input_device = self._select_input_device()
            if self.input_device is not None:
                print(f"Using input device index: {self.input_device}")
            else:
                print("Using default input device")

            # Phát hiện samplerate phù hợp theo device (Windows có thể là 44100/48000)
            detected_fs = self._detect_samplerate()
            self.current_samplerate = detected_fs if detected_fs else fs
            print(f"Input samplerate: {self.current_samplerate}")
            # Tính lại blocksize theo samplerate thực tế để có đúng 30ms frame
            frame_size = int(self.current_samplerate * frame_duration / 1000)
            print(f"Adjusted frame size: {frame_size} samples @ {self.current_samplerate} Hz")

            stream = sd.InputStream(
                callback=self.stream_callback,
                samplerate=self.current_samplerate,
                blocksize=frame_size,
                channels=1,
                dtype=np.float32,
                latency='low',
                device=self.input_device
            )

            print("Starting audio stream...")
            stream.start()

            # Chạy cho đến khi stop_flag được set
            while not self.stop_flag.is_set():
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\nStopping recording due to keyboard interrupt...")
        except Exception as e:
            # Thử fallback: không set device và/hoặc giảm latency
            logger.error(f"Stream error: {e}")
            try:
                logger.info("Retrying audio stream with fallback parameters...")
                stream = sd.InputStream(
                    callback=self.stream_callback,
                    samplerate=self.current_samplerate,
                    blocksize=frame_size,
                    channels=1,
                    dtype=np.float32,
                    # bỏ latency và device để dùng mặc định
                )
                stream.start()
                while not self.stop_flag.is_set():
                    time.sleep(0.1)
            except Exception as e2:
                logger.error(f"Fallback stream error: {e2}")
        finally:
            # Dừng stream
            try:
                if 'stream' in locals():
                    stream.stop()
                    stream.close()
            except:
                pass

            # Xử lý audio còn lại trong buffer ngay lập tức
            if self.buffer:
                logger.info(f"Processing remaining audio buffer: {len(self.buffer)} chunks")
                full_chunk = np.concatenate(self.buffer)

                # Combine with previous audio for context
                if len(self.last_audio) > 0:
                    combined = np.concatenate([self.last_audio, full_chunk])
                else:
                    combined = full_chunk

                # Transcribe ngay lập tức nếu có đủ audio
                if len(combined) >= 16000:  # ít nhất 1 giây
                    try:
                        logger.info("Transcribing remaining audio immediately...")
                        result = self._transcribe_batch([combined])
                        if result and result[0].strip():
                            self.text += result[0].strip() + " "
                            logger.info(f"Final transcription: {result[0]}")
                    except Exception as e:
                        logger.error(f"Error transcribing final audio: {e}")

            # Dừng recording và cleanup
            self._cleanup()

            # Thu thập các kết quả còn lại từ queue
            while not self.result_queue.empty():
                try:
                    result = self.result_queue.get_nowait()
                    if result and result.strip():
                        cleaned_result = result.rstrip('.') + " "
                        self.text += cleaned_result
                        print(f" {result}")
                except queue.Empty:
                    break

            # Làm sạch text cuối cùng
            final_text = self.get_current_text()

            if return_text:
                logger.info(f"\n--- Final transcribed text ---")
                logger.info(f"'{final_text}'")
                logger.info(f"--- End of transcription ---")
                return final_text
            else:
                return None

    def _cleanup(self):
        """Internal cleanup method with improved error handling"""
        logger.info("👂🛑 Starting cleanup process...")
        self.stop_flag.set()
        self.interrupted = True

        # Poison pill to stop worker
        try:
            self.audio_queue.put_nowait(None)
        except queue.Full:
            logger.warning("Could not send poison pill - queue full")
        except Exception as e:
            logger.error(f"Error sending poison pill: {e}")

        # Wait for threads to finish with timeout
        if self.transcribe_thread and self.transcribe_thread.is_alive():
            logger.info("Waiting for transcribe thread to finish...")
            self.transcribe_thread.join(timeout=3)
            if self.transcribe_thread.is_alive():
                logger.warning("Transcribe thread did not finish within timeout")

        # Shutdown executor with error handling
        try:
            self.executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error shutting down executor: {e}")

        # Cleanup GPU memory
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            logger.info("👂✨ Memory cleanup completed")
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")

    def stop(self):
        """Stop recording and return accumulated text with better error handling"""
        logger.info("Stopping recording...")

        # Xử lý audio còn lại trong buffer ngay lập tức
        if self.buffer:
            logger.info(f"Processing remaining audio buffer: {len(self.buffer)} chunks")
            full_chunk = np.concatenate(self.buffer)

            # Combine with previous audio for context
            if len(self.last_audio) > 0:
                combined = np.concatenate([self.last_audio, full_chunk])
            else:
                combined = full_chunk

            # Transcribe ngay lập tức nếu có đủ audio
            if len(combined) >= 16000:  # ít nhất 1 giây
                try:
                    logger.info("Transcribing remaining audio immediately...")
                    result = self._transcribe_batch([combined])
                    if result and result[0].strip():
                        self.text += result[0].strip() + " "
                        logger.info(f"Final transcription: {result[0]}")
                except Exception as e:
                    logger.error(f"Error transcribing final audio: {e}")

        self._cleanup()

        # Thu thập các kết quả còn lại từ queue
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                if result and result.strip():
                    cleaned_result = result.rstrip('.') + " "
                    self.text += cleaned_result
            except queue.Empty:
                break

        logger.info("Cleanup completed.")
        return self.text.strip()

    def reset_recording(self):
        """Reset recording state without destroying the model with better error handling"""
        logger.info("Resetting recording state...")

        # Stop current recording
        self.stop_flag.set()

        # Clear queues
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

        # Reset state
        self.text = ""
        self.buffer = []
        self.last_audio = np.array([])
        self.silence_counter = 0
        self.processing_times = []
        self.stop_flag.clear()

        # Restart transcribe thread
        if self.transcribe_thread.is_alive():
            self.transcribe_thread.join(timeout=1)

        self.transcribe_thread = threading.Thread(target=self._transcribe_worker, daemon=True)
        self.transcribe_thread.start()

        # Recreate ThreadPoolExecutor if it was shutdown
        try:
            if self.executor._shutdown:
                logger.info("Recreating ThreadPoolExecutor...")
                self.executor = ThreadPoolExecutor(max_workers=self.num_workers)
        except Exception as e:
            logger.error(f"Error recreating ThreadPoolExecutor: {e}")
            self.executor = ThreadPoolExecutor(max_workers=self.num_workers)

        logger.info("Recording state reset completed.")

    def get_current_text(self):
        """Lấy text hiện tại mà không dừng recording"""
        return self.text.strip()

    def clear_text(self):
        """Xóa text hiện tại"""
        self.text = ""

    def get_performance_stats(self):
        """Get performance statistics"""
        if not self.processing_times:
            return "No performance data available"

        avg_time = np.mean(self.processing_times)
        min_time = np.min(self.processing_times)
        max_time = np.max(self.processing_times)

        return f"Performance Stats - Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s"
