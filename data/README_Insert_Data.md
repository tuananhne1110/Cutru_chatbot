# Hướng dẫn Insert Data vào Supabase

## Tổng quan
Các script này giúp bạn import dữ liệu từ JSON files vào Supabase database.

## Cấu trúc Files
```
data/
├── insert_data.py           # Script gốc - chỉ import all_laws.json
├── insert_form_data.py      # Script mới - chỉ import form_chunks.json  
├── insert_all_data.py       # Script tổng hợp - import cả 2 files
└── README_Insert_Data.md    # File hướng dẫn này
```

## Các Script có sẵn

### 1. `insert_data.py` (Script gốc)
- **Mục đích**: Import dữ liệu từ `all_laws.json` vào bảng `laws`
- **Sử dụng**: Khi chỉ cần import laws data
- **Chạy**: `python data/insert_data.py`

### 2. `insert_form_data.py` (Script mới)
- **Mục đích**: Import dữ liệu từ `form_chunks.json` vào bảng `form_guidance`
- **Sử dụng**: Khi chỉ cần import form guidance data
- **Chạy**: `python data/insert_form_data.py`

### 3. `insert_all_data.py` (Script tổng hợp - Khuyến nghị)
- **Mục đích**: Import cả 2 loại dữ liệu vào database
- **Sử dụng**: Khi cần import tất cả dữ liệu
- **Chạy**: `python data/insert_all_data.py`

## Cấu trúc Database

### Bảng `laws`
```sql
CREATE TABLE laws (
    id SERIAL PRIMARY KEY,
    law_code VARCHAR(50),
    law_name TEXT,
    promulgator VARCHAR(200),
    promulgation_date DATE,
    effective_date DATE,
    law_type VARCHAR(100),
    status VARCHAR(50),
    file_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Bảng `form_guidance`
```sql
CREATE TABLE form_guidance (
    id SERIAL PRIMARY KEY,
    form_code VARCHAR(20),
    form_name TEXT,
    field_no VARCHAR(10),
    field_name TEXT,
    chunk_type VARCHAR(50),
    content TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Cách sử dụng

### Bước 1: Chuẩn bị dữ liệu
Đảm bảo các file JSON đã được tạo:
```bash
# Tạo form chunks
python chunking/form_chunker.py

# Tạo all_laws.json (nếu chưa có)
# File này cần được tạo từ quá trình chunking laws
```

### Bước 2: Chạy script import
```bash
# Import tất cả dữ liệu (Khuyến nghị)
python data/insert_all_data.py
```

## Tính năng của Scripts

### Data Cleaning
- **Date conversion**: Chuyển đổi ngày tháng từ tiếng Việt sang PostgreSQL format
- **Text cleaning**: Loại bỏ ký tự đặc biệt và normalize text
- **Null handling**: Xử lý đúng các giá trị null/empty

### Error Handling
- **File not found**: Thông báo rõ ràng nếu file JSON không tồn tại
- **Database errors**: Log chi tiết lỗi khi insert
- **Progress tracking**: Hiển thị tiến độ import

### Statistics
- **Import count**: Đếm số records đã import thành công
- **Database stats**: Thống kê tổng số records trong database
- **Form analysis**: Phân tích số lượng form và chunk types

## Output Example

```
🚀 BẮT ĐẦU IMPORT DỮ LIỆU VÀO SUPABASE
============================================================
📜 Bắt đầu import dữ liệu laws...
📊 Đang import 150 law records vào Supabase...
✅ Đã import 10/150 law records
✅ Đã import 20/150 law records
...
✅ Hoàn thành import dữ liệu laws!

------------------------------------------------------------
📋 Bắt đầu import dữ liệu form guidance...
📊 Đang import 89 form chunks vào Supabase...
✅ Đã import 10/89 form chunks
...
✅ Hoàn thành import dữ liệu form guidance!

============================================================
✅ HOÀN THÀNH IMPORT TẤT CẢ DỮ LIỆU!
📊 Tổng kết:
   - Laws imported: 150
   - Form chunks imported: 89
   - Total records: 239

📊 THỐNG KÊ DATABASE
==================================================
📜 Tổng số laws records: 150
📋 Tổng số form guidance records: 89
📋 Số lượng form khác nhau: 2
📋 Các form codes: CT01, CT02
🏷️ Các loại chunk: hướng_dẫn_điền, ký_xác_nhận, lưu_ý, ví_dụ
```

## Troubleshooting

### Lỗi "File not found"
```bash
# Kiểm tra file tồn tại
ls -la chunking/output_json/
```

### Lỗi "Table does not exist"
- Tạo bảng trong Supabase trước khi chạy script
- Kiểm tra tên bảng và cấu trúc

### Lỗi "Connection failed"
- Kiểm tra URL và API key trong script
- Đảm bảo kết nối internet

### Lỗi "Duplicate key"
- Script sẽ báo lỗi nếu có duplicate
- Có thể cần xóa dữ liệu cũ trước khi import lại

## Lưu ý quan trọng

1. **Backup**: Luôn backup database trước khi import dữ liệu lớn
2. **Test**: Test với dữ liệu nhỏ trước khi import toàn bộ
3. **Monitoring**: Theo dõi logs để phát hiện lỗi sớm
4. **Validation**: Kiểm tra dữ liệu sau khi import để đảm bảo tính toàn vẹn 