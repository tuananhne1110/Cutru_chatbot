#!/bin/bash

# Script để cài đặt các dependencies cần thiết cho việc tạo file DOCX/PDF

echo "🚀 Cài đặt dependencies cho việc tạo file DOCX/PDF..."

# Cài đặt Python packages
echo "📦 Cài đặt Python packages..."
pip install weasyprint==63.1
pip install html2docx==2.1.3
pip install docxtpl==0.18.0

# Cài đặt system dependencies cho weasyprint (Ubuntu/Debian)
echo "🔧 Cài đặt system dependencies..."
if command -v apt-get &> /dev/null; then
    echo "Phát hiện Ubuntu/Debian system"
    sudo apt-get update
    sudo apt-get install -y \
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
        libfontconfig1 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info
elif command -v yum &> /dev/null; then
    echo "Phát hiện CentOS/RHEL system"
    sudo yum install -y \
        pango \
        harfbuzz \
        fontconfig \
        cairo \
        gdk-pixbuf2 \
        libffi-devel
elif command -v brew &> /dev/null; then
    echo "Phát hiện macOS system"
    brew install pango cairo gdk-pixbuf libffi
else
    echo "⚠️ Không thể tự động cài đặt system dependencies. Vui lòng cài đặt thủ công:"
    echo "- pango"
    echo "- cairo" 
    echo "- gdk-pixbuf"
    echo "- libffi"
    echo "- fontconfig"
fi

echo "✅ Hoàn thành cài đặt dependencies!"
echo ""
echo "🧪 Test việc import các thư viện..."

python3 -c "
try:
    import weasyprint
    print('✅ weasyprint: OK')
except ImportError as e:
    print('❌ weasyprint:', e)

try:
    import html2docx
    print('✅ html2docx: OK')
except ImportError as e:
    print('❌ html2docx:', e)

try:
    from docx import Document
    print('✅ python-docx: OK')
except ImportError as e:
    print('❌ python-docx:', e)
"

echo ""
echo "🎉 Setup hoàn tất! Bạn có thể chạy server và test việc tạo file DOCX/PDF."