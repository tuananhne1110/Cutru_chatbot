-- Script tạo bảng cho Supabase Database
-- Chạy script này trong Supabase SQL Editor

-- 1. Tạo bảng laws (cho all_laws.json)
CREATE TABLE IF NOT EXISTS laws (
    id SERIAL PRIMARY KEY,
    law_code VARCHAR(50),
    law_name TEXT,
    promulgator VARCHAR(200),
    promulgation_date DATE,
    effective_date DATE,
    law_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'đang hiệu lực',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    category VARCHAR(20) DEFAULT 'law'
);

-- 2. Tạo bảng form_guidance (cho form_chunks.json)
CREATE TABLE IF NOT EXISTS form_guidance (
    id SERIAL PRIMARY KEY,
    form_code VARCHAR(20),
    form_name TEXT,
    field_no VARCHAR(10),
    field_name TEXT,
    chunk_type VARCHAR(50),
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    category VARCHAR(20) DEFAULT 'form'
);

-- 3. Tạo bảng terms (cho term_chunks.json)
CREATE TABLE IF NOT EXISTS terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL,
    definition TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    category VARCHAR(20) DEFAULT 'term'
);

-- 4. Tạo bảng procedures (cho procedure_chunks.json)
CREATE TABLE IF NOT EXISTS procedures (
    id SERIAL PRIMARY KEY,
    procedure_code VARCHAR(50),
    decision_number VARCHAR(50),
    procedure_name VARCHAR(200) NOT NULL,
    implementation_level VARCHAR(100),
    procedure_type VARCHAR(200),
    field VARCHAR(200),
    implementation_subject TEXT,
    implementing_agency VARCHAR(200),
    competent_authority VARCHAR(200),
    application_receiving_address TEXT,
    authorized_agency VARCHAR(200),
    coordinating_agency VARCHAR(200),
    implementation_result TEXT,
    requirements TEXT,
    keywords TEXT,
    content_type VARCHAR(50),
    source_section VARCHAR(100),
    table_title TEXT,
    table_index INTEGER,
    row_index INTEGER,
    column_name VARCHAR(100),
    chunk_index INTEGER,
    total_chunks INTEGER,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    category VARCHAR(20) DEFAULT 'procedure'
);

-- 5. Tạo indexes để tối ưu performance
CREATE INDEX IF NOT EXISTS idx_laws_law_code ON laws(law_code);
CREATE INDEX IF NOT EXISTS idx_laws_law_type ON laws(law_type);
CREATE INDEX IF NOT EXISTS idx_laws_status ON laws(status);
CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category);

CREATE INDEX IF NOT EXISTS idx_form_guidance_form_code ON form_guidance(form_code);
CREATE INDEX IF NOT EXISTS idx_form_guidance_field_no ON form_guidance(field_no);
CREATE INDEX IF NOT EXISTS idx_form_guidance_chunk_type ON form_guidance(chunk_type);
CREATE INDEX IF NOT EXISTS idx_form_guidance_category ON form_guidance(category);

CREATE INDEX IF NOT EXISTS idx_terms_term ON terms(term);
CREATE INDEX IF NOT EXISTS idx_terms_category ON terms(category);
CREATE INDEX IF NOT EXISTS idx_terms_source ON terms(source);
CREATE INDEX IF NOT EXISTS idx_terms_language ON terms(language);
CREATE INDEX IF NOT EXISTS idx_terms_category_type ON terms(category_type);

CREATE INDEX IF NOT EXISTS idx_procedures_procedure_code ON procedures(procedure_code);
CREATE INDEX IF NOT EXISTS idx_procedures_procedure_name ON procedures(procedure_name);
CREATE INDEX IF NOT EXISTS idx_procedures_implementation_level ON procedures(implementation_level);
CREATE INDEX IF NOT EXISTS idx_procedures_field ON procedures(field);
CREATE INDEX IF NOT EXISTS idx_procedures_category ON procedures(category);
CREATE INDEX IF NOT EXISTS idx_procedures_chunk_index ON procedures(chunk_index);

-- 6. Tạo RLS (Row Level Security) policies (tùy chọn)
-- Bật RLS cho bảng laws
ALTER TABLE laws ENABLE ROW LEVEL SECURITY;

-- Bật RLS cho bảng form_guidance
ALTER TABLE form_guidance ENABLE ROW LEVEL SECURITY;

-- Bật RLS cho bảng terms
ALTER TABLE terms ENABLE ROW LEVEL SECURITY;

-- Bật RLS cho bảng procedures
ALTER TABLE procedures ENABLE ROW LEVEL SECURITY;

-- Tạo policy cho phép đọc tất cả records (public read)
CREATE POLICY "Allow public read access to laws" ON laws
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access to form_guidance" ON form_guidance
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access to terms" ON terms
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access to procedures" ON procedures
    FOR SELECT USING (true);

-- Tạo policy cho phép insert (chỉ cho authenticated users hoặc service role)
CREATE POLICY "Allow insert to laws" ON laws
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert to form_guidance" ON form_guidance
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert to terms" ON terms
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert to procedures" ON procedures
    FOR INSERT WITH CHECK (true);

-- 7. Tạo function để tự động update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 8. Tạo triggers để tự động update updated_at
CREATE TRIGGER update_laws_updated_at 
    BEFORE UPDATE ON laws 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_form_guidance_updated_at 
    BEFORE UPDATE ON form_guidance 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_terms_updated_at 
    BEFORE UPDATE ON terms 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_procedures_updated_at 
    BEFORE UPDATE ON procedures 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 9. Thêm comments cho bảng và cột
COMMENT ON TABLE laws IS 'Bảng lưu trữ thông tin các văn bản luật pháp';
COMMENT ON COLUMN laws.law_code IS 'Mã văn bản luật';
COMMENT ON COLUMN laws.law_name IS 'Tên văn bản luật';
COMMENT ON COLUMN laws.promulgator IS 'Cơ quan ban hành';
COMMENT ON COLUMN laws.promulgation_date IS 'Ngày ban hành';
COMMENT ON COLUMN laws.effective_date IS 'Ngày có hiệu lực';
COMMENT ON COLUMN laws.law_type IS 'Loại văn bản (Nghị định, Thông tư, ...)';
COMMENT ON COLUMN laws.status IS 'Trạng thái hiệu lực';
COMMENT ON COLUMN laws.category IS 'Phân loại chunk (luôn là law)';

COMMENT ON TABLE form_guidance IS 'Bảng lưu trữ hướng dẫn điền form';
COMMENT ON COLUMN form_guidance.form_code IS 'Mã mẫu tờ khai (VD: CT01, CT02)';
COMMENT ON COLUMN form_guidance.form_name IS 'Tên đầy đủ tờ khai';
COMMENT ON COLUMN form_guidance.field_no IS 'Số thứ tự trường/mục';
COMMENT ON COLUMN form_guidance.field_name IS 'Tên trường theo hướng dẫn';
COMMENT ON COLUMN form_guidance.chunk_type IS 'Loại chunk (hướng_dẫn_điền, ví_dụ, lưu_ý)';
COMMENT ON COLUMN form_guidance.content IS 'Nội dung hướng dẫn chi tiết';
COMMENT ON COLUMN form_guidance.note IS 'Lưu ý/ví dụ bổ sung';
COMMENT ON COLUMN form_guidance.category IS 'Phân loại chunk (luôn là form)';

COMMENT ON TABLE terms IS 'Bảng lưu trữ thuật ngữ và định nghĩa pháp lý';
COMMENT ON COLUMN terms.term IS 'Thuật ngữ chính';
COMMENT ON COLUMN terms.definition IS 'Định nghĩa ngắn gọn của thuật ngữ';
COMMENT ON COLUMN terms.content IS 'Nội dung chi tiết giải thích thuật ngữ';
COMMENT ON COLUMN terms.category IS 'Phân loại thuật ngữ (cư_trú, hộ_gia_đình, giấy_tờ, ...)';
COMMENT ON COLUMN terms.source IS 'Nguồn trích dẫn (tên văn bản luật)';
COMMENT ON COLUMN terms.article IS 'Điều khoản trong văn bản';
COMMENT ON COLUMN terms.chapter IS 'Chương trong văn bản';
COMMENT ON COLUMN terms.section IS 'Mục trong văn bản';
COMMENT ON COLUMN terms.language IS 'Ngôn ngữ (vi, en)';
COMMENT ON COLUMN terms.synonyms IS 'Mảng các từ đồng nghĩa';
COMMENT ON COLUMN terms.related_terms IS 'Mảng các thuật ngữ liên quan';
COMMENT ON COLUMN terms.examples IS 'Mảng các ví dụ sử dụng';
COMMENT ON COLUMN terms.notes IS 'Ghi chú bổ sung';
COMMENT ON COLUMN terms.category_type IS 'Phân loại chunk (luôn là term)';

COMMENT ON TABLE procedures IS 'Bảng lưu trữ thông tin thủ tục hành chính';
COMMENT ON COLUMN procedures.procedure_code IS 'Mã thủ tục hành chính';
COMMENT ON COLUMN procedures.decision_number IS 'Số quyết định';
COMMENT ON COLUMN procedures.procedure_name IS 'Tên thủ tục hành chính';
COMMENT ON COLUMN procedures.implementation_level IS 'Cấp thực hiện (Cấp Xã, Cấp Huyện, ...)';
COMMENT ON COLUMN procedures.procedure_type IS 'Loại thủ tục hành chính';
COMMENT ON COLUMN procedures.field IS 'Lĩnh vực thủ tục';
COMMENT ON COLUMN procedures.implementation_subject IS 'Đối tượng thực hiện';
COMMENT ON COLUMN procedures.implementing_agency IS 'Cơ quan thực hiện';
COMMENT ON COLUMN procedures.competent_authority IS 'Cơ quan có thẩm quyền';
COMMENT ON COLUMN procedures.application_receiving_address IS 'Địa chỉ tiếp nhận hồ sơ';
COMMENT ON COLUMN procedures.authorized_agency IS 'Cơ quan được ủy quyền';
COMMENT ON COLUMN procedures.coordinating_agency IS 'Cơ quan phối hợp';
COMMENT ON COLUMN procedures.implementation_result IS 'Kết quả thực hiện';
COMMENT ON COLUMN procedures.requirements IS 'Yêu cầu, điều kiện';
COMMENT ON COLUMN procedures.keywords IS 'Từ khóa tìm kiếm';
COMMENT ON COLUMN procedures.content_type IS 'Loại nội dung (text, table_row, ...)';
COMMENT ON COLUMN procedures.source_section IS 'Phần nguồn (implementation_procedure, legal_basis, ...)';
COMMENT ON COLUMN procedures.table_title IS 'Tiêu đề bảng (nếu có)';
COMMENT ON COLUMN procedures.table_index IS 'Chỉ số bảng';
COMMENT ON COLUMN procedures.row_index IS 'Chỉ số hàng';
COMMENT ON COLUMN procedures.column_name IS 'Tên cột';
COMMENT ON COLUMN procedures.chunk_index IS 'Chỉ số chunk trong tổng số chunks';
COMMENT ON COLUMN procedures.total_chunks IS 'Tổng số chunks của thủ tục';
COMMENT ON COLUMN procedures.content IS 'Nội dung chi tiết thủ tục';
COMMENT ON COLUMN procedures.category IS 'Phân loại chunk (luôn là procedure)';

-- 10. Kiểm tra bảng đã được tạo
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('laws', 'form_guidance', 'terms', 'procedures')
ORDER BY table_name, ordinal_position; 