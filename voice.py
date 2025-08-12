import torch
import sounddevice as sd
import numpy as np
import io
import wave
import threading
import time
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
import queue

class SpeechToTextModule:
    def __init__(self,model_name = "vinai/PhoWhisper-medium",sample_rate = 16000, channels = 1, dtype = np.float32):
        # Khởi tạo model PhoWhisper
        self.model_name = model_name
        self.processor = None
        self.model = None
        
        # Audio settings
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        
        # Recording state
        self.is_recording = False
        self.audio_data = []
        self.audio_queue = queue.Queue()
        
        print("Đang tải model...")
        self.load_model()
        print("Tải thành công!")
        
    def load_model(self):
        """Tải model và processor"""
        try:
            self.processor = WhisperProcessor.from_pretrained(self.model_name)
            self.model = WhisperForConditionalGeneration.from_pretrained(self.model_name)
            
            # Chuyển model sang GPU nếu có
            if torch.cuda.is_available():
                self.model = self.model.cuda()
                print("Đang sử dụng GPU")
            else:
                print("Đang sử dụng CPU")
                
        except Exception as e:
            print(f"Lỗi khi tải model: {e}")
            raise
    
    def audio_callback(self, indata, frames, time, status):
        """Callback function để ghi âm"""
        if status:
            print(f"Audio callback error: {status}")
        
        if self.is_recording:
            # Chuyển đổi từ stereo sang mono nếu cần
            if indata.shape[1] > 1:
                audio_mono = np.mean(indata, axis=1)
            else:
                audio_mono = indata[:, 0]
            
            self.audio_queue.put(audio_mono.copy())
    
    def start_recording(self):
        """Bắt đầu ghi âm"""
        if self.is_recording:
            return
        
        print("Bắt đầu ghi...")
        self.is_recording = True
        self.audio_data = []
        
        # Bắt đầu stream audio
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self.audio_callback
        )
        self.stream.start()
        
        # Thread để thu thập dữ liệu audio
        self.recording_thread = threading.Thread(target=self._collect_audio)
        self.recording_thread.start()
    
    def _collect_audio(self):
        """Thu thập dữ liệu audio từ queue"""
        while self.is_recording:
            try:
                audio_chunk = self.audio_queue.get(timeout=0.1)
                self.audio_data.extend(audio_chunk)
            except queue.Empty:
                continue
    
    def stop_recording(self):
        """Dừng ghi âm và trả về audio data"""
        if not self.is_recording:
            return None
        
        print("Dừng ghi...")
        self.is_recording = False
        
        # Dừng stream
        self.stream.stop()
        self.stream.close()
        
        # Đợi thread ghi âm kết thúc
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()
        
        # Thu thập dữ liệu còn lại trong queue
        while not self.audio_queue.empty():
            try:
                audio_chunk = self.audio_queue.get_nowait()
                self.audio_data.extend(audio_chunk)
            except queue.Empty:
                break
        
        if len(self.audio_data) > 0:
            return np.array(self.audio_data, dtype=np.float32)
        return None
    
    def transcribe_audio(self, audio_data):
        """Chuyển đổi audio thành text"""
        if audio_data is None or len(audio_data) == 0:
            return ""
        
        try:
            print("Đang chuyển đổi giọng nói thành văn bản...")
            
            # Chuẩn hóa audio về đúng sample rate
            if len(audio_data) < self.sample_rate * 0.1:  # Quá ngắn (< 0.1 giây)
                return ""
            
            # Tiền xử lý audio
            input_features = self.processor(
                audio_data, 
                sampling_rate=self.sample_rate, 
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
            
            print(f"Kết quả: {transcription}")
            return transcription.strip()
            
        except Exception as e:
            print(f"Lỗi khi chuyển đổi: {e}")
            return f"Lỗi: {str(e)}"
    
    def record_and_transcribe(self):
        """Ghi âm và chuyển đổi trong một lần gọi"""
        self.start_recording()
        input("Nhấn Enter để dừng ghi âm...")
        audio_data = self.stop_recording()
        return self.transcribe_audio(audio_data)



import tkinter as tk
from tkinter import ttk, scrolledtext

class SpeechToTextGUI:
    def __init__(self):
        self.stt_module = SpeechToTextModule()
        self.setup_gui()
        
    def setup_gui(self):
        """Thiết lập giao diện người dùng"""
        self.root = tk.Tk()
        self.root.title("Speech to Text - PhoWhisper")
        self.root.geometry("500x400")
        
        # Frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Nút ghi âm
        self.record_button = ttk.Button(
            main_frame, 
            text="Nhấn giữ để ghi âm",
            style="Record.TButton"
        )
        self.record_button.grid(row=0, column=0, pady=10, sticky=(tk.W, tk.E))
        
        # Bind events cho nút
        self.record_button.bind('<Button-1>', self.start_recording)
        self.record_button.bind('<ButtonRelease-1>', self.stop_recording)
        
        # Label trạng thái
        self.status_label = ttk.Label(main_frame, text="Sẵn sàng ghi âm")
        self.status_label.grid(row=1, column=0, pady=5)
        
        # Text area để hiển thị kết quả
        ttk.Label(main_frame, text="Kết quả:").grid(row=2, column=0, sticky=tk.W, pady=(10,5))
        
        self.result_text = scrolledtext.ScrolledText(
            main_frame, 
            height=15, 
            width=50,
            wrap=tk.WORD
        )
        self.result_text.grid(row=3, column=0, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Nút xóa
        clear_button = ttk.Button(main_frame, text="Xóa", command=self.clear_text)
        clear_button.grid(row=4, column=0, pady=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Style cho nút ghi âm
        style = ttk.Style()
        style.configure("Record.TButton", font=("Arial", 12, "bold"))
    
    def start_recording(self, event):
        """Bắt đầu ghi âm khi nhấn nút"""
        self.record_button.config(text="Đang ghi âm... (Thả để dừng)", state="active")
        self.status_label.config(text="🔴 Đang ghi âm...")
        self.root.update()
        
        self.stt_module.start_recording()
    
    def stop_recording(self, event):
        """Dừng ghi âm khi thả nút"""
        self.record_button.config(text="Đang xử lý...", state="disabled")
        self.status_label.config(text="⏳ Đang chuyển đổi...")
        self.root.update()
        
        # Dừng ghi âm và lấy dữ liệu
        audio_data = self.stt_module.stop_recording()
        
        # Chuyển đổi thành text
        if audio_data is not None:
            transcription = self.stt_module.transcribe_audio(audio_data)
            if transcription:
                # Thêm kết quả vào text area
                self.result_text.insert(tk.END, transcription + "\n\n")
                self.result_text.see(tk.END)
        
        # Reset nút và trạng thái
        self.record_button.config(text="Nhấn giữ để ghi âm", state="normal")
        self.status_label.config(text="Sẵn sàng ghi âm")
    
    def clear_text(self):
        """Xóa nội dung text area"""
        self.result_text.delete(1.0, tk.END)
    
    def run(self):
        """Chạy ứng dụng"""
        print("Ứng dụng Speech to Text đã sẵn sàng!")
        self.root.mainloop()


# Sử dụng module
if __name__ == "__main__":

    # Chạy với giao diện GUI
    app = SpeechToTextGUI()
    app.run()
    