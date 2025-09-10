# Voice Module

Voice module cung cấp các chức năng voice-to-text, text-to-speech và voice chatbot cho backend.

## Cấu trúc

```
backend/src/voice/
├── __init__.py          # Package exports
├── speech_recognizer.py # Speech-to-text với Whisper
├── tts_engine.py        # Text-to-speech với pyttsx3
├── voice_service.py     # Service quản lý voice operations
├── voice_chatbot.py     # Voice chatbot với LangGraph RAG
└── README.md           # Tài liệu này
```

## Tính năng

### 1. Speech Recognition (ASR)
- Sử dụng Whisper model (vinai/PhoWhisper-medium)
- Hỗ trợ real-time transcription
- Voice Activity Detection (VAD)
- Async processing với callback system
- GPU/CPU auto-detection

### 2. Text-to-Speech (TTS)
- Sử dụng pyttsx3 với SAPI
- Hỗ trợ giọng tiếng Việt (MSTTS - An)
- Async speaking với callback
- Anti-echo khi TTS đang phát

### 3. Voice Chatbot
- Tích hợp với LangGraph RAG workflow
- Voice-to-voice conversation
- Conversation history management
- Real-time response generation

## Cấu hình

Thêm cấu hình voice vào `configs.yaml`:

```yaml
services:
  voice:
    enabled: true
    model_name: "vinai/PhoWhisper-medium"
    device: null  # Auto-detect GPU/CPU
    batch_size: 16
    num_workers: 2
    language: "vi"
    tts_rate: 180
    tts_volume: 1.0
    vad_aggressiveness: 2
    frame_duration: 30
    sample_rate: 16000
    min_segment_sec: 2.0
    max_segment_sec: 3.0
    overlap_sec: 0.8
```

## API Endpoints

### REST API

#### Khởi tạo Voice Service
```http
POST /voice/initialize
Content-Type: application/json

{
  "model_name": "vinai/PhoWhisper-medium",
  "device": null,
  "batch_size": 16,
  "num_workers": 2,
  "tts_rate": 180,
  "tts_volume": 1.0
}
```

#### Voice Recording
```http
POST /voice/start-recording
# Bắt đầu recording và trả về text đã transcribe
```

```http
POST /voice/stop-recording
# Dừng recording và trả về text cuối cùng
```

```http
GET /voice/current-text
# Lấy text hiện tại mà không dừng recording
```

#### Text-to-Speech
```http
POST /voice/speak
Content-Type: application/json

"text=Chào bạn, tôi có thể giúp gì?"
```

#### Voice Chat
```http
POST /voice/chat
# Xử lý voice input và trả về voice response
```

#### Status & Control
```http
GET /voice/status
# Lấy trạng thái voice service

POST /voice/clear-text
# Xóa text hiện tại
```

### WebSocket API

#### Real-time Voice Chat
```javascript
const ws = new WebSocket('ws://localhost:8000/voice/ws/chat');

// Listen for messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'transcription':
      console.log('Transcription:', data.data.text);
      break;
    case 'status':
      console.log('Status:', data.data.status);
      break;
    case 'response':
      console.log('Response:', data.data.text);
      break;
  }
};

// Start chat
ws.send(JSON.stringify({ action: 'start_chat' }));

// Stop
ws.send(JSON.stringify({ action: 'stop' }));
```

## Sử dụng trong Code

### Basic Usage

```python
from backend.src.voice.voice_service import VoiceService
from backend.src.voice.voice_chatbot import VoiceChatbot

# Initialize voice service
voice_service = VoiceService()
await voice_service.initialize()

# Use speech recognition
transcribed_text = await voice_service.start_recording_async()

# Use TTS
await voice_service.speak_async("Chào bạn!")

# Use voice chatbot
chatbot = VoiceChatbot(voice_service=voice_service)
await chatbot.initialize()

response = await chatbot.process_voice_input()
```

### Advanced Usage với Callbacks

```python
def on_text_callback(text: str):
    print(f"Real-time transcription: {text}")

def on_status_callback(status: str):
    print(f"Status: {status}")

voice_service.set_callbacks(
    on_text=on_text_callback,
    on_status=on_status_callback
)
```

## Dependencies

```bash
pip install torch transformers sounddevice numpy webrtcvad scipy
pip install pyttsx3  # For Windows TTS
```

## Troubleshooting

### Audio Device Issues
- Đảm bảo microphone được phép truy cập
- Kiểm tra device index với `python -c "import sounddevice as sd; print(sd.query_devices())"`
- Thử chạy với device=None để dùng default device

### GPU Issues
- Đảm bảo CUDA được cài đặt đúng
- Kiểm tra `torch.cuda.is_available()`
- Thử chạy với device=-1 (CPU only)

### TTS Issues (Windows)
- Cài đặt Speech SDK
- Kiểm tra giọng tiếng Việt có sẵn
- Thử chạy với TTS khác nếu cần

## Performance Tuning

### ASR Performance
- `batch_size`: Tăng để xử lý nhiều audio chunks cùng lúc (16-32)
- `num_workers`: Tăng để parallel processing (2-4)
- `frame_duration`: Giảm để real-time hơn (20-30ms)

### Memory Usage
- Giảm `batch_size` nếu gặp OOM
- Sử dụng CPU nếu GPU memory không đủ
- Clear cache thường xuyên với `torch.cuda.empty_cache()`

## Migration từ Voice Cũ

Nếu đang dùng voice module cũ:

1. Cập nhật import paths:
   ```python
   # Old
   from src.call_chatbot.stream_speech import SpeechRecognizer

   # New
   from src.voice.speech_recognizer import SpeechRecognizer
   ```

2. Cập nhật router trong main.py:
   ```python
   # Old
   from src.routers.voice_to_text import router as voice_to_text_router

   # New
   from src.routers.voice_router import router as voice_router
   ```

3. Cập nhật cấu hình trong YAML theo format mới

## Contributing

- Thêm test cases cho các components
- Optimize performance với async/await
- Thêm support cho các TTS engines khác
- Implement voice activity detection nâng cao
