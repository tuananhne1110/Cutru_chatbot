# Floating Chatbot Frontend

Frontend cho chatbot trợ lý ảo Chính phủ điện tử với giao diện floating ở góc màn hình.

## Tính năng

- **Floating Chatbot**: Chatbot nổi ở góc phải dưới màn hình
- **Thu gọn/Mở rộng**: Có thể thu gọn thành nút tròn hoặc mở rộng thành cửa sổ chat đầy đủ
- **Responsive**: Tương thích với các thiết bị khác nhau
- **Giao diện đẹp**: Sử dụng Tailwind CSS với animations mượt mà

## Cách sử dụng

### Trạng thái thu gọn
- Hiển thị dưới dạng nút tròn màu xanh với icon 🤖
- Click để mở chatbot

### Trạng thái bình thường
- Cửa sổ chat nhỏ (320px x 500px)
- Có thể mở rộng hoặc đóng
- Hiển thị tin nhắn và input để chat

### Trạng thái mở rộng
- Cửa sổ chat lớn (384px x 600px)
- Hiển thị đầy đủ các controls (refresh, clear, new chat)
- Hiển thị session ID

## Cấu trúc Components

- `FloatingChatbot.js`: Component chính của chatbot
- `Message.js`: Component hiển thị tin nhắn
- `MessageInput.js`: Component input để nhập tin nhắn
- `App.js`: Component chính của ứng dụng

## Chạy ứng dụng

```bash
cd frontend
npm install
npm start
```

Ứng dụng sẽ chạy tại `http://localhost:3000`

## API Endpoints

- `POST /chat/session`: Tạo session mới
- `POST /chat/stream`: Gửi tin nhắn và nhận phản hồi
- `GET /chat/history/{session_id}`: Lấy lịch sử chat
- `DELETE /chat/history/{session_id}`: Xóa lịch sử chat

## Styling

Sử dụng Tailwind CSS với các custom styles trong `index.css`:
- Animations cho floating button
- Custom scrollbar cho chat messages
- Smooth transitions
- Hover effects 