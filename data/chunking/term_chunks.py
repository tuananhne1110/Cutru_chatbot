from docx import Document
import re
import json

def chunk_terms(file_path):
    doc = Document(file_path)
    results = []
    for para in doc.paragraphs:
        line = para.text.strip()
        if not line:
            continue
        if ':' in line:
            term_raw, definition = line.split(':', 1)
            term = term_raw.strip()
            definition = definition.strip().strip('"')
            # Optionally: extract law_ref if needed
            law_ref = None
            m = re.search(r'(Điều\s+\d+[^;,.]*)', definition)
            entry = {
                "term": term,
                "definition": definition,
                "category": "term"
            }
            if m:
                entry["law_ref"] = m.group(1)
            results.append(entry)
    return results

# Đường dẫn tới file
file_path = "data/Thuật ngữ.docx"
chunks = chunk_terms(file_path)

# Xuất ra file JSON
with open("chunking/output_json/term_chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Đã xuất {len(chunks)} thuật ngữ chuẩn hóa.")
