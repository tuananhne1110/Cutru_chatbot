# Voice-to-Text Integration

## Tổng quan

Tính năng voice-to-text đã được tích hợp vào chatbot với hai phương pháp:

1. **Browser Web Speech API** (Ưu tiên): Sử dụng API của trình duyệt
2. **Server-side Speech Recognition** (Fallback): Sử dụng PhoWhisper model

## Cách sử dụng

### 1. Trong giao diện chatbot

- Nhấn vào icon microphone 🎤 bên cạnh ô nhập text
- Bắt đầu nói - text sẽ xuất hiện real-time
- Nhấn "Dừng" hoặc icon microphone lần nữa để kết thúc
- Text sẽ được tự động điền vào ô input

### 2. Trạng thái recording

- **Đang ghi âm**: Hiển thị animation đỏ với icon microphone
- **Text real-time**: Hiển thị text đang được transcribe
- **Lỗi**: Hiển thị thông báo lỗi màu vàng

## Cài đặt

### Dependencies

```bash
# System dependencies (Ubuntu/Debian)
sudo apt-get install portaudio19-dev python3-pyaudio libasound2-dev

# Python dependencies
pip install sounddevice==0.4.6
pip install webrtcvad==2.0.10
pip install transformers==4.53.1
```

### Hoặc sử dụng script

```bash
chmod +x install_voice_deps.sh
./install_voice_deps.sh
```

## API Endpoints

### POST /voice/start-recording
Bắt đầu recording voice-to-text

### POST /voice/stop-recording
Dừng recording và trả về text đã transcribe

### GET /voice/status
Kiểm tra trạng thái recording

### POST /voice/get-current-text
Lấy text hiện tại đang được transcribe

## Cấu trúc code

### Backend
- `routers/voice_to_text.py`: API endpoints
- `stream_speech.py`: Speech recognition engine

### Frontend
- `services/voiceToTextService.js`: Server-side voice service
- `services/browserVoiceService.js`: Browser voice service
- `hooks/useVoiceToText.js`: Voice-to-text hook
- `components/VoiceRecorder.js`: UI component
- `components/VoiceSupportInfo.js`: Support info

## Troubleshooting

### Lỗi audio device
```
Error querying device -1
```
**Giải pháp**: 
- Kiểm tra microphone permissions
- Cài đặt audio drivers
- Trong WSL: Có thể cần cấu hình audio forwarding

### Browser không hỗ trợ
**Giải pháp**: 
- Sử dụng Chrome/Edge (hỗ trợ tốt nhất)
- Kiểm tra HTTPS (required cho microphone access)

### Model loading chậm
**Giải pháp**:
- Giảm batch_size trong SpeechRecognizer
- Sử dụng GPU nếu có
- Cache model để tái sử dụng

## Performance Tips

1. **Browser API**: Nhanh nhất, không cần server
2. **Server API**: Chính xác hơn, hỗ trợ tiếng Việt tốt
3. **Batch size**: Giảm để giảm latency
4. **Workers**: Tăng để tăng throughput

## Browser Support

- ✅ Chrome/Chromium
- ✅ Edge
- ✅ Safari (limited)
- ❌ Firefox (no Web Speech API)

## Model Information

- **PhoWhisper-medium**: Optimized cho tiếng Việt
- **WebRTC VAD**: Voice Activity Detection
- **Real-time processing**: Streaming audio input
