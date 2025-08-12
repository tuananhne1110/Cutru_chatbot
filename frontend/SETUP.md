# Setup CT01 Integration

## Environment Variables

Tạo file `.env` trong thư mục `frontend` với các biến sau:

```env
# API Configuration
REACT_APP_API_URL=http://localhost:8000

# Supabase Configuration
REACT_APP_SUPABASE_URL=your_supabase_url_here
REACT_APP_SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Optional: Development settings
REACT_APP_DEBUG=true
```

## Supabase Database Setup

### 1. Tạo bảng `forms`
```sql
CREATE TABLE forms (
  id SERIAL PRIMARY KEY,
  code VARCHAR(10) UNIQUE NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  template_url VARCHAR(500),
  fields JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert CT01 template
INSERT INTO forms (code, title, description, fields) VALUES (
  'CT01',
  'Tờ khai thuế thu nhập cá nhân',
  'Áp dụng đối với cá nhân có thu nhập từ tiền lương, tiền công',
  '{
    "fields": [
      {"name": "ho_ten", "label": "Họ và tên", "type": "text", "required": true},
      {"name": "so_cccd", "label": "Số căn cước công dân", "type": "text", "required": true},
      {"name": "ngay_sinh", "label": "Ngày sinh", "type": "date", "required": true},
      {"name": "gioi_tinh", "label": "Giới tính", "type": "select", "options": ["Nam", "Nữ"], "required": true},
      {"name": "dia_chi", "label": "Địa chỉ thường trú", "type": "textarea", "required": true},
      {"name": "so_dien_thoai", "label": "Số điện thoại", "type": "tel", "required": true},
      {"name": "email", "label": "Email", "type": "email", "required": true},
      {"name": "nghe_nghiep", "label": "Nghề nghiệp", "type": "text"},
      {"name": "thu_nhap", "label": "Thu nhập chịu thuế (VNĐ)", "type": "number", "required": true},
      {"name": "thue_da_khau_tru", "label": "Thuế đã khấu trừ (VNĐ)", "type": "number"},
      {"name": "so_nguoi_phu_thuoc", "label": "Số người phụ thuộc", "type": "number", "default": 0},
      {"name": "ghi_chu", "label": "Ghi chú", "type": "textarea"}
    ]
  }'
);
```

### 2. Tạo bảng `cccd_data`
```sql
CREATE TABLE cccd_data (
  id SERIAL PRIMARY KEY,
  so_cccd VARCHAR(12) UNIQUE NOT NULL,
  ho_ten VARCHAR(255) NOT NULL,
  ngay_sinh DATE NOT NULL,
  gioi_tinh VARCHAR(10) NOT NULL,
  quoc_tich VARCHAR(50) DEFAULT 'Việt Nam',
  dia_chi TEXT NOT NULL,
  noi_sinh VARCHAR(255),
  ngay_cap DATE,
  noi_cap VARCHAR(255),
  ngay_het_han DATE,
  dac_diem_nhan_dang TEXT,
  anh_chan_dung TEXT,
  van_tay TEXT,
  iris TEXT,
  chip_data TEXT,
  signature TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. Tạo bảng `ct01_forms`
```sql
CREATE TABLE ct01_forms (
  id SERIAL PRIMARY KEY,
  cccd_data_id INTEGER REFERENCES cccd_data(id),
  ho_ten VARCHAR(255) NOT NULL,
  so_cccd VARCHAR(12) NOT NULL,
  ngay_sinh DATE NOT NULL,
  gioi_tinh VARCHAR(10) NOT NULL,
  dia_chi TEXT NOT NULL,
  so_dien_thoai VARCHAR(20),
  email VARCHAR(255),
  nghe_nghiep VARCHAR(255),
  thu_nhap DECIMAL(15,2),
  thue_da_khau_tru DECIMAL(15,2) DEFAULT 0,
  so_nguoi_phu_thuoc INTEGER DEFAULT 0,
  ghi_chu TEXT,
  status VARCHAR(20) DEFAULT 'draft',
  reference_id VARCHAR(50) UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Tạo index cho performance
CREATE INDEX idx_ct01_forms_cccd_data_id ON ct01_forms(cccd_data_id);
CREATE INDEX idx_ct01_forms_status ON ct01_forms(status);
CREATE INDEX idx_ct01_forms_created_at ON ct01_forms(created_at);
```

## API Endpoints

### Backend cần implement các endpoints sau:

1. `POST /api/ct01/generate` - Tạo file CT01
2. `POST /api/ct01/submit` - Nộp form trực tuyến
3. `GET /api/ct01/history` - Lấy lịch sử form
4. `GET /api/ct01/template` - Lấy template form

## Usage

1. Cài đặt dependencies:
```bash
cd frontend
npm install
```

2. Cấu hình environment variables

3. Chạy ứng dụng:
```bash
npm start
```

4. Test CT01 flow:
   - Mở chatbot
   - Gõ "Điền biểu mẫu CT01"
   - Modal sẽ mở và hướng dẫn qua các bước

## Features

- ✅ Quét CCCD và trích xuất thông tin
- ✅ Tự động điền form từ dữ liệu CCCD
- ✅ Validation form
- ✅ Preview biểu mẫu
- ✅ Tải về PDF/Word
- ✅ Nộp trực tuyến
- ✅ Lưu trữ vào Supabase
- ✅ Chatbot integration 