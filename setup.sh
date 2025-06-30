#!/bin/bash

echo "🚀 Bắt đầu setup Trợ Lý Pháp Luật..."

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 không được tìm thấy. Vui lòng cài đặt Python 3.10+"
    exit 1
fi

# Kiểm tra Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js không được tìm thấy. Vui lòng cài đặt Node.js 18+"
    exit 1
fi

# Kiểm tra Docker
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker không được tìm thấy. Docker deployment sẽ không khả dụng."
fi

echo "✅ Kiểm tra dependencies hoàn tất"

# Tạo thư mục cần thiết
mkdir -p laws output_json frontend/src

# Cài đặt Python dependencies
echo "📦 Cài đặt Python dependencies..."
pip install -r requirements.txt

# Setup frontend
echo "📦 Cài đặt Node.js dependencies..."
cd frontend
npm install
cd ..

# Tạo .env file nếu chưa có
if [ ! -f .env ]; then
    echo "🔧 Tạo file .env..."
    cat > .env << EOF
# Chutes.ai API Key
CHUTES_API_KEY=your-chutes-api-key-here

# Supabase Configuration
SUPABASE_URL=https://rjrqtogyzmgyqvryxfyk.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqcnF0b2d5em1neXF2cnl4ZnlrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA5MDcyNTcsImV4cCI6MjA2NjQ4MzI1N30.QjnPfVS7NbMTqe4z80X6q2MVA0z3iM3xsLzB71uEDNQ

# QDrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
EOF
    echo "⚠️ Vui lòng cập nhật CHUTES_API_KEY trong file .env"
fi

# Setup Supabase tables
echo "🗄️ Setup Supabase tables..."
if [ -f setup_supabase.py ]; then
    python3 setup_supabase.py
else
    echo "⚠️ setup_supabase.py không tìm thấy. Vui lòng tạo bảng thủ công trong Supabase."
fi

# Tạo nginx config cho frontend
if [ ! -f frontend/nginx.conf ]; then
    echo "🔧 Tạo nginx config..."
    cat > frontend/nginx.conf << EOF
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
fi

echo "✅ Setup hoàn tất!"
echo ""
echo "📋 Bước tiếp theo:"
echo "1. Đặt file .docx vào thư mục laws/"
echo "2. Cập nhật CHUTES_API_KEY trong file .env"
echo "3. Chạy: python chunking.py"
echo "4. Chạy: python embed_qdrant.py"
echo "5. Chạy backend: python api.py"
echo "6. Chạy frontend: cd frontend && npm start"
echo ""
echo "🐳 Hoặc deploy với Docker:"
echo "docker-compose up -d" 