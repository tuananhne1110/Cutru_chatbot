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
from typing import Optional, Tuple

class SpeechRecognizer:
    def __init__(self, 
                 model_name: str = "vinai/PhoWhisper-medium",
                 device: Optional[int] = None,
                 batch_size: int = 16,
                 num_workers: int = 2):
        
        """
        Khởi tạo SpeechRecognizer:
        - Tải mô hình 
        - Thiết lập các hàng đợi và luồng xử lý
        - Bắt đầu luồng transcription
        """
        
        
        # Xác định thiết bị dùng GPU nếu có
        self.device = device if device is not None else (0 if torch.cuda.is_available() else -1)
        self.batch_size = batch_size
        self.num_workers = num_workers
        
        # Hàng đợi để lưu audio chưa xử lý
        self.audio_queue = queue.Queue(maxsize=10)  # Giới hạn để tránh memory leak
        # Hàng đợi để lưu kết quả text sau khi xử lý
        self.result_queue = queue.Queue()
        
        # Tạo thread pool để xử lý song song
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        
        # Load model một lần duy nhất
        print("Đang tải model...")
        self.pipe = self._load_model_optimized(model_name)
        print("Model đã được tải ")
        
        # Khởi tạo bộ phát hiện giọng nói WebRTC
        self.vad = webrtcvad.Vad(3)
        
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
        
    def _load_model_optimized(self, model_name: str):
        """
        Tải mô hình speech-to-text với cấu hình tối ưu (dùng GPU nếu có).
        Làm nóng model để giảm độ trễ ban đầu.
        """
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=self.device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            model_kwargs={
                "use_cache": True,
                "low_cpu_mem_usage": True,
            }
        )
        
        # Làm nóng model bằng audio giả
        if torch.cuda.is_available():
            dummy_audio = np.random.random(16000).astype(np.float32)
            _ = pipe({"raw": dummy_audio, "sampling_rate": 16000}, batch_size=1)
            torch.cuda.empty_cache()
            
        return pipe
    # ----------------------------------------
    # Luồng xử lý audio: nhận từ queue → transcribe
    # ----------------------------------------
    def _transcribe_worker(self, timeout = 0.1):
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
                        print(f"Batch submitted successfully")
                    except Exception as e:
                        print(f"Error submitting batch: {e}")
                        # Process directly if executor is down
                        try:
                            results = self._transcribe_batch(batch_audio)
                            for result in results:
                                if result and result.strip():
                                    self.result_queue.put(result)
                        except Exception as direct_error:
                            print(f"Direct processing error: {direct_error}")
                
                # Lấy kết quả từ các job đã hoàn thành
                completed_futures = [f for f in pending_futures if f.done()]
                for future in completed_futures:
                    try:
                        results = future.result()
                        for result in results:
                            if result and result.strip():
                                self.result_queue.put(result)
                    except Exception as e:
                        print(f"Transcription error: {e}", file=sys.stderr)
                    pending_futures.remove(future)
                    
            except Exception as e:
                print(f"Worker error: {e}", file=sys.stderr)
                time.sleep(0.1)
    # ----------------------------------------
    # Hàm xử lý một batch audio và trả kết quả
    # ----------------------------------------
    def _transcribe_batch(self, batch_audio: list) -> list:
        """
        Xử lý một batch audio. Trả về danh sách kết quả text tương ứng.
        Theo dõi thời gian xử lý để đánh giá hiệu suất.
        """
        start_time = time.time()
        results = []
        
        try:
            for audio_np in batch_audio:
                if audio_np is None or len(audio_np) == 0:
                    results.append("")
                    continue
                    
                # Optimize input format
                audio_input = {
                    "raw": audio_np.astype(np.float32), 
                    "sampling_rate": 16000
                }
                
                result = self.pipe(audio_input, batch_size=1, return_timestamps=False)
                transcribed_text = result["text"] if result else ""
                if transcribed_text.strip():
                    print(f"Transcribed: '{transcribed_text}'")
                results.append(transcribed_text)
                
        except Exception as e:
            print(f"Batch transcription error: {e}", file=sys.stderr)
            results = [""] * len(batch_audio)
        
        # Lưu thời gian xử lý để theo dõi hiệu suất
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        # Keep only last 100 measurements
        if len(self.processing_times) > 100:
            self.processing_times = self.processing_times[-100:]
            
        return results
    # ----------------------------------------
    # Phát hiện tiếng nói (VAD) kết hợp thông minh
    # ----------------------------------------
    def _enhanced_vad(self, audio_chunk: np.ndarray, fs: int) -> bool:
        """
        Phát hiện tiếng nói sử dụng VAD + mức năng lượng fallback.
        Cho phép điều chỉnh ngưỡng năng lượng theo ngữ cảnh gần đây.
        """
        try:
            # Ensure proper frame size
            frame_size = len(audio_chunk)
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
            
            # WebRTC VAD - giảm độ nghiêm ngặt
            try:
                is_speech = self.vad.is_speech(audio_int16.tobytes(), fs)
            except:
                is_speech = False
            
            # Luôn kiểm tra năng lượng để đảm bảo không bỏ sót
            energy = np.mean(audio_chunk ** 2)
            
            # Ngưỡng năng lượng rất thấp để nhạy cảm hơn
            energy_threshold = 0.00001  # Giảm từ 0.0001 xuống 0.00001
            
            # Nếu VAD không phát hiện, dùng năng lượng để kiểm tra
            if not is_speech:
                # Adaptive threshold based on recent history
                if self.buffer:
                    recent_energy = np.mean([np.mean(b**2) for b in self.buffer[-5:]])
                    adaptive_threshold = max(energy_threshold, recent_energy * 0.01)  # Giảm từ 0.05 xuống 0.01
                else:
                    adaptive_threshold = energy_threshold
                is_speech = energy > adaptive_threshold
            
            # Debug: in ra thông tin năng lượng
            if energy > 0.0001:  # Giảm ngưỡng debug để thấy nhiều hơn
                print(f"Energy: {energy:.6f}, VAD: {is_speech}, Threshold: {energy_threshold:.6f}")
                
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
            print(f"Stream status: {status}", file=sys.stderr)
        
        # Lấy audio từ 1 kênh (mono)
        audio_chunk = indata[:, 0].copy()
        
        # Debug: in ra thông tin audio mỗi 100 frames
        if hasattr(self, '_frame_counter'):
            self._frame_counter += 1
        else:
            self._frame_counter = 0
            
        if self._frame_counter % 100 == 0:
            energy = np.mean(audio_chunk ** 2)
            print(f"Audio frame {self._frame_counter}: energy={energy:.6f}, max={np.max(np.abs(audio_chunk)):.6f}")
        
        # Debug: in ra tất cả audio frames để debug
        energy = np.mean(audio_chunk ** 2)
        if energy > 0.00001:  # Rất nhạy cảm
            print(f"Audio detected: frame={self._frame_counter}, energy={energy:.6f}")
        
        # Kiểm tra xem có phải tiếng nói không
        is_speech = self._enhanced_vad(audio_chunk, 16000)
        
        if is_speech:
            self.buffer.append(audio_chunk)
            self.silence_counter = 0
            print(f"Speech detected! Buffer size: {len(self.buffer)}")
        elif self.buffer:  # Only count silence after speech
            self.silence_counter += 1
            if self.silence_counter <= 10:  # Add some silence after speech
                self.buffer.append(audio_chunk)
            
            # Process when we have enough audio or too much silence
            if len(self.buffer) >= 20:  # ~600ms of audio
                print(f"Processing audio chunk: {len(self.buffer)} frames")
                full_chunk = np.concatenate(self.buffer)
                
                # Combine with previous audio for context
                if len(self.last_audio) > 0:
                    combined = np.concatenate([self.last_audio, full_chunk])
                else:
                    combined = full_chunk
                
                # Keep last part for next iteration
                overlap_size = min(len(full_chunk), 5 * len(audio_chunk))
                self.last_audio = full_chunk[-overlap_size:] if len(full_chunk) > overlap_size else full_chunk
                
                # Queue for async processing (non-blocking)
                try:
                    self.audio_queue.put_nowait(combined)
                    print(f"Audio queued for processing. Queue size: {self.audio_queue.qsize()}")
                except queue.Full:
                    # Drop oldest item if queue is full
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.put_nowait(combined)
                    except queue.Empty:
                        pass
                
                self.buffer.clear()
                self.silence_counter = 0
    
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
        print(f"Starting optimized recording... Frame size: {frame_size} samples")
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
            stream = sd.InputStream(
                callback=self.stream_callback,
                samplerate=fs,
                blocksize=frame_size,
                channels=1,
                dtype=np.float32,
                latency='low'
            )
            
            print("Starting audio stream...")
            stream.start()
            
            # Chạy cho đến khi stop_flag được set
            while not self.stop_flag.is_set():
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nStopping recording...")
        except Exception as e:
            print(f"Stream error: {e}", file=sys.stderr)
        finally:
            # Dừng stream
            try:
                if 'stream' in locals():
                    stream.stop()
                    stream.close()
            except:
                pass
            
            # Dừng recording và cleanup
            self._cleanup()
            
            # Chờ một chút để xử lý các audio còn lại trong queue
            time.sleep(1.0)
            
            # Thu thập các kết quả còn lại
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
                print(f"\n--- Final transcribed text ---")
                print(f"'{final_text}'")
                print(f"--- End of transcription ---")
                return final_text
            else:
                return None
    
    def _cleanup(self):
        """Internal cleanup method"""
        self.stop_flag.set()
        
        # Poison pill to stop worker
        try:
            self.audio_queue.put_nowait(None)
        except queue.Full:
            pass
        
        # Wait for threads to finish
        if self.transcribe_thread.is_alive():
            self.transcribe_thread.join(timeout=2)
        
        self.executor.shutdown(wait=True)
        
        # Cleanup GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    def stop(self):
        """Stop recording and return accumulated text"""
        print("Stopping recording...")
        self._cleanup()
        
        # Chờ một chút để xử lý các audio còn lại
        time.sleep(1.0)
        
        # Thu thập các kết quả còn lại
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                if result and result.strip():
                    cleaned_result = result.rstrip('.') + " "
                    self.text += cleaned_result
            except queue.Empty:
                break
        
        print("Cleanup completed.")
        return self.text.strip()
    
    def reset_recording(self):
        """Reset recording state without destroying the model"""
        print("Resetting recording state...")
        
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
        if self.executor._shutdown:
            print("Recreating ThreadPoolExecutor...")
            self.executor = ThreadPoolExecutor(max_workers=self.num_workers)
        
        print("Recording state reset completed.")
    
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

# Ví dụ sử dụng
if __name__ == "__main__":
    try:
        # Khởi tạo với optimal settings
        recognizer = SpeechRecognizer(
            batch_size=16,
            num_workers=2
        )
        
        print(recognizer.get_performance_stats())
        
        #  Sử dụng start_recording và nhận text khi dừng
        transcribed_text = recognizer.start_recording(return_text=True)
        print(f"\nText đã ghi được: {transcribed_text}")
        
        if transcribed_text:
            #  Lưu vào file
            with open("transcription.txt", "w", encoding="utf-8") as f:
                f.write(transcribed_text)
            
            # Ví dụ: Xử lý text thêm
            word_count = len(transcribed_text.split())
            print(f"Số từ đã ghi: {word_count}")
        
        
    except Exception as e:
        print(f"Initialization error: {e}", file=sys.stderr)
        sys.exit(1)