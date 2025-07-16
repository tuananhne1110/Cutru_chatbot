#!/bin/bash
set -e

# if [ ! -f "/app/.embedded" ]; then
#   echo "🔥 Bắt đầu nhúng embedding vào Qdrant..."
#   python embed_to_qdrant_local.py
#   touch /app/.embedded
# else
#   echo "✅ Đã nhúng embedding trước đó, bỏ qua bước này."
# fi

echo "🚀 Khởi động ứng dụng chính..."
python main.py