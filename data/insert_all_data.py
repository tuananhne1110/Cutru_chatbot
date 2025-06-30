from supabase import create_client, Client
import json
import re
from datetime import datetime

url = "https://rjrqtogyzmgyqvryxfyk.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqcnF0b2d5em1neXF2cnl4ZnlrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA5MDcyNTcsImV4cCI6MjA2NjQ4MzI1N30.QjnPfVS7NbMTqe4z80X6q2MVA0z3iM3xsLzB71uEDNQ"

supabase: Client = create_client(url, key)

def convert_vietnamese_date(date_str):
    """Chuyển đổi ngày tháng từ tiếng Việt sang định dạng PostgreSQL"""
    if not date_str or date_str == "":
        return None
    
    # Pattern: "15 tháng 5 năm 2021"
    pattern = r"(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})"
    match = re.search(pattern, date_str)
    
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        
        try:
            date_obj = datetime(year, month, day)
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            print(f"⚠️ Ngày không hợp lệ: {date_str}")
            return None
    
    print(f"⚠️ Không thể parse ngày: {date_str}")
    return None

def clean_field_no(field_no):
    """Làm sạch field_no, chuyển null thành None"""
    if field_no is None or field_no == "" or field_no == "null":
        return None
    return str(field_no)

def clean_text(text):
    """Làm sạch text, loại bỏ ký tự đặc biệt"""
    if not text:
        return None
    # Loại bỏ ký tự đặc biệt và normalize
    cleaned = re.sub(r'[^\w\s\.,;:!?()\-/]', '', text)
    return cleaned.strip()

def insert_laws_data():
    """Insert dữ liệu laws từ all_laws.json"""
    print("📜 Bắt đầu import dữ liệu laws...")
    
    try:
        with open("chunking/output_json/all_laws.json", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"📊 Đang import {len(data)} law records vào Supabase...")
        
        for i, chunk in enumerate(data):
            try:
                # Chuyển đổi ngày tháng
                prom_date = convert_vietnamese_date(chunk.get("promulgation_date"))
                eff_date = convert_vietnamese_date(chunk.get("effective_date"))
                
                law_data = {
                    "law_code": chunk.get("law_code"),
                    "law_name": chunk.get("law_name"),
                    "promulgator": chunk.get("promulgator"),
                    "promulgation_date": prom_date,
                    "effective_date": eff_date,
                    "law_type": chunk.get("law_type"),
                    "status": "đang hiệu lực",
                    "category": "law"
                }
                
                supabase.table("laws").insert(law_data).execute()
                
                if (i + 1) % 10 == 0:
                    print(f"✅ Đã import {i + 1}/{len(data)} law records")
                    
            except Exception as e:
                print(f"❌ Lỗi khi import law record {i}: {e}")
        
        print("✅ Hoàn thành import dữ liệu laws!")
        return len(data)
        
    except FileNotFoundError:
        print("⚠️ File all_laws.json không tồn tại, bỏ qua import laws")
        return 0
    except Exception as e:
        print(f"❌ Lỗi khi import laws: {e}")
        return 0

def insert_form_guidance_data():
    """Insert dữ liệu form guidance từ form_chunks.json"""
    print("📋 Bắt đầu import dữ liệu form guidance...")
    
    try:
        with open("chunking/output_json/form_chunks.json", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"📊 Đang import {len(data)} form chunks vào Supabase...")
        
        for i, chunk in enumerate(data):
            try:
                form_data = {
                    "form_code": chunk.get("form_code"),
                    "form_name": clean_text(chunk.get("form_name")),
                    "field_no": clean_field_no(chunk.get("field_no")),
                    "field_name": clean_text(chunk.get("field_name")),
                    "chunk_type": chunk.get("chunk_type"),
                    "content": clean_text(chunk.get("content")),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "category": "form"
                }
                
                supabase.table("form_guidance").insert(form_data).execute()
                
                if (i + 1) % 10 == 0:
                    print(f"✅ Đã import {i + 1}/{len(data)} form chunks")
                    
            except Exception as e:
                print(f"❌ Lỗi khi import form chunk {i}: {e}")
        
        print("✅ Hoàn thành import dữ liệu form guidance!")
        return len(data)
        
    except FileNotFoundError:
        print("⚠️ File form_chunks.json không tồn tại, bỏ qua import form guidance")
        return 0
    except Exception as e:
        print(f"❌ Lỗi khi import form guidance: {e}")
        return 0

def insert_terms_data():
    """Insert dữ liệu terms từ term_chunks.json"""
    print("📚 Bắt đầu import dữ liệu terms...")
    
    try:
        with open("chunking/output_json/term_chunks.json", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"📊 Đang import {len(data)} term records vào Supabase...")
        
        for i, chunk in enumerate(data):
            try:
                # Xử lý arrays
                synonyms = chunk.get("synonyms", [])
                if isinstance(synonyms, str):
                    synonyms = [synonyms] if synonyms else []
                
                related_terms = chunk.get("related_terms", [])
                if isinstance(related_terms, str):
                    related_terms = [related_terms] if related_terms else []
                
                examples = chunk.get("examples", [])
                if isinstance(examples, str):
                    examples = [examples] if examples else []
                
                term_data = {
                    "term": clean_text(chunk.get("term")),
                    "definition": clean_text(chunk.get("definition")),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "category": "term"
                }
                
                supabase.table("terms").insert(term_data).execute()
                
                if (i + 1) % 10 == 0:
                    print(f"✅ Đã import {i + 1}/{len(data)} term records")
                    
            except Exception as e:
                print(f"❌ Lỗi khi import term record {i}: {e}")
        
        print("✅ Hoàn thành import dữ liệu terms!")
        return len(data)
        
    except FileNotFoundError:
        print("⚠️ File term_chunks.json không tồn tại, bỏ qua import terms")
        return 0
    except Exception as e:
        print(f"❌ Lỗi khi import terms: {e}")
        return 0

def insert_procedures_data():
    """Insert dữ liệu procedures từ procedure_chunks.json"""
    print("📋 Bắt đầu import dữ liệu procedures...")
    
    try:
        with open("chunking/output_json/procedure_chunks.json", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"📊 Đang import {len(data)} procedure records vào Supabase...")
        
        for i, chunk in enumerate(data):
            try:
                procedure_data = {
                    "procedure_code": chunk.get("procedure_code"),
                    "decision_number": chunk.get("decision_number"),
                    "procedure_name": clean_text(chunk.get("procedure_name")),
                    "implementation_level": chunk.get("implementation_level"),
                    "procedure_type": chunk.get("procedure_type"),
                    "field": chunk.get("field"),
                    "implementation_subject": clean_text(chunk.get("implementation_subject")),
                    "implementing_agency": chunk.get("implementing_agency"),
                    "competent_authority": chunk.get("competent_authority"),
                    "application_receiving_address": clean_text(chunk.get("application_receiving_address")),
                    "authorized_agency": chunk.get("authorized_agency"),
                    "coordinating_agency": chunk.get("coordinating_agency"),
                    "implementation_result": clean_text(chunk.get("implementation_result")),
                    "requirements": clean_text(chunk.get("requirements")),
                    "keywords": clean_text(chunk.get("keywords")),
                    "content_type": chunk.get("content_type"),
                    "source_section": chunk.get("source_section"),
                    "table_title": clean_text(chunk.get("table_title")),
                    "table_index": chunk.get("table_index"),
                    "row_index": chunk.get("row_index"),
                    "column_name": chunk.get("column_name"),
                    "chunk_index": chunk.get("chunk_index"),
                    "total_chunks": chunk.get("total_chunks"),
                    "content": clean_text(chunk.get("content")),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "category": "procedure"
                }
                
                supabase.table("procedures").insert(procedure_data).execute()
                
                if (i + 1) % 10 == 0:
                    print(f"✅ Đã import {i + 1}/{len(data)} procedure records")
                    
            except Exception as e:
                print(f"❌ Lỗi khi import procedure record {i}: {e}")
        
        print("✅ Hoàn thành import dữ liệu procedures!")
        return len(data)
        
    except FileNotFoundError:
        print("⚠️ File procedure_chunks.json không tồn tại, bỏ qua import procedures")
        return 0
    except Exception as e:
        print(f"❌ Lỗi khi import procedures: {e}")
        return 0

def get_database_stats():
    """Lấy thống kê từ database"""
    print("\n📊 THỐNG KÊ DATABASE")
    print("="*50)
    
    try:
        # Thống kê laws
        result = supabase.table("laws").select("id", count="exact").execute()
        laws_count = result.count if result.count is not None else 0
        print(f"📜 Tổng số laws records: {laws_count}")
        
        # Thống kê form_guidance
        result = supabase.table("form_guidance").select("id", count="exact").execute()
        forms_count = result.count if result.count is not None else 0
        print(f"📋 Tổng số form guidance records: {forms_count}")
        
        # Thống kê terms
        result = supabase.table("terms").select("id", count="exact").execute()
        terms_count = result.count if result.count is not None else 0
        print(f"📚 Tổng số terms records: {terms_count}")
        
        # Thống kê procedures
        result = supabase.table("procedures").select("id", count="exact").execute()
        procedures_count = result.count if result.count is not None else 0
        print(f"📋 Tổng số procedures records: {procedures_count}")
        
        # Thống kê theo category
        if laws_count > 0:
            result = supabase.table("laws").select("category").execute()
            categories = [row['category'] for row in result.data if row.get('category')]
            law_categories = categories.count('law')
            print(f"   - Law records: {law_categories}")
        
        if forms_count > 0:
            result = supabase.table("form_guidance").select("category").execute()
            categories = [row['category'] for row in result.data if row.get('category')]
            form_categories = categories.count('form')
            print(f"   - Form records: {form_categories}")
        
        if terms_count > 0:
            result = supabase.table("terms").select("category").execute()
            categories = [row['category'] for row in result.data if row.get('category')]
            term_categories = categories.count('term')
            print(f"   - Term records: {term_categories}")
        
        if procedures_count > 0:
            result = supabase.table("procedures").select("category").execute()
            categories = [row['category'] for row in result.data if row.get('category')]
            procedure_categories = categories.count('procedure')
            print(f"   - Procedure records: {procedure_categories}")
        
        # Thống kê form codes
        result = supabase.table("form_guidance").select("form_code").execute()
        form_codes = [row['form_code'] for row in result.data if row['form_code']]
        unique_forms = set(form_codes)
        print(f"📋 Số lượng form khác nhau: {len(unique_forms)}")
        if unique_forms:
            print(f"📋 Các form codes: {', '.join(unique_forms)}")
        
        # Thống kê chunk types
        result = supabase.table("form_guidance").select("chunk_type").execute()
        chunk_types = [row['chunk_type'] for row in result.data if row['chunk_type']]
        unique_types = set(chunk_types)
        print(f"🏷️ Các loại chunk: {', '.join(unique_types)}")
        
        # Thống kê terms categories
        if terms_count > 0:
            result = supabase.table("terms").select("category").execute()
            term_categories = [row['category'] for row in result.data if row['category']]
            unique_term_cats = set(term_categories)
            print(f"📚 Các loại terms: {', '.join(unique_term_cats)}")
            
            # Thống kê languages
            result = supabase.table("terms").select("language").execute()
            languages = [row['language'] for row in result.data if row['language']]
            unique_langs = set(languages)
            print(f"🌐 Ngôn ngữ terms: {', '.join(unique_langs)}")
            
            # Thống kê sources
            result = supabase.table("terms").select("source").execute()
            sources = [row['source'] for row in result.data if row['source']]
            unique_sources = set(sources)
            print(f"📖 Nguồn terms: {', '.join(unique_sources)}")
        
        # Thống kê procedures
        if procedures_count > 0:
            result = supabase.table("procedures").select("implementation_level").execute()
            levels = [row['implementation_level'] for row in result.data if row['implementation_level']]
            unique_levels = set(levels)
            print(f"📋 Cấp thực hiện procedures: {', '.join(unique_levels)}")
            
            result = supabase.table("procedures").select("field").execute()
            fields = [row['field'] for row in result.data if row['field']]
            unique_fields = set(fields)
            print(f"🏛️ Lĩnh vực procedures: {', '.join(unique_fields)}")
            
            result = supabase.table("procedures").select("procedure_type").execute()
            types = [row['procedure_type'] for row in result.data if row['procedure_type']]
            unique_types = set(types)
            print(f"📄 Loại procedures: {', '.join(unique_types)}")
            
            result = supabase.table("procedures").select("content_type").execute()
            content_types = [row['content_type'] for row in result.data if row['content_type']]
            unique_content_types = set(content_types)
            print(f"📝 Loại nội dung procedures: {', '.join(unique_content_types)}")
        
    except Exception as e:
        print(f"⚠️ Không thể lấy thống kê: {e}")

def main():
    """Main function"""
    print("🚀 BẮT ĐẦU IMPORT DỮ LIỆU VÀO SUPABASE")
    print("="*60)
    
    # Import laws data
    laws_count = insert_laws_data()
    
    print("\n" + "-"*60)
    
    # Import form guidance data
    forms_count = insert_form_guidance_data()
    
    print("\n" + "-"*60)
    
    # Import terms data
    terms_count = insert_terms_data()
    
    print("\n" + "-"*60)
    
    # Import procedures data
    procedures_count = insert_procedures_data()
    
    print("\n" + "="*60)
    print("✅ HOÀN THÀNH IMPORT TẤT CẢ DỮ LIỆU!")
    print(f"📊 Tổng kết:")
    print(f"   - Laws imported: {laws_count}")
    print(f"   - Form chunks imported: {forms_count}")
    print(f"   - Terms imported: {terms_count}")
    print(f"   - Procedures imported: {procedures_count}")
    print(f"   - Total records: {laws_count + forms_count + terms_count + procedures_count}")
    
    # Hiển thị thống kê
    get_database_stats()

if __name__ == "__main__":
    main() 