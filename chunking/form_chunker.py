import json
import re
from pathlib import Path
from docx import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FormChunker:
    def __init__(self):
        self.chunks = []
        self.current_form_code = None
        self.current_form_name = None

    def extract_form_info(self, heading_line):
        heading_line = heading_line.replace('–', '-').replace('—', '-')
        if '-' in heading_line:
            name_part, code_part = heading_line.split('-', 1)
            form_name = name_part.strip()
            m = re.search(r'Mẫu\s*([A-Z0-9]+)', code_part, re.IGNORECASE)
            if m:
                form_code = m.group(1).strip().upper()
            else:
                form_code = code_part.strip().upper()
            return form_code, form_name
        return "UNKNOWN", heading_line.strip()

    def parse_docx_content(self, docx_path):
        try:
            doc = Document(docx_path)
            return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        except Exception as e:
            logger.error(f"Error reading {docx_path}: {e}")
            return []

    def extract_field_info(self, text):
        m = re.match(r'^Mục\s*\((\d+)\)\s*([^\:]+)', text)
        if m:
            field_no = None
            field_name = m.group(2).strip()
            return field_no, field_name
        
        m = re.match(r'^Mục\s*(\d+)\.?\s*([^\:]+)(?:\:)?', text)
        if m:
            return m.group(1), m.group(2).strip()
        
        m = re.match(r'^(\d+)\.?\s*([^\:]+)(?:\:)?', text)
        if m:
            return m.group(1), m.group(2).strip()
        
        m = re.match(r'^Mục\s+([^\:]+):\s*(.*)', text)
        if m:
            return None, m.group(1).strip()
        
        m = re.match(r'^([A-Za-zÀ-ỹ ,/()\-]+):\s*(.*)', text)
        if m:
            return None, m.group(1).strip()
        
        return None, None

    def normalize_field_name(self, field_name):
        if not field_name:
            return field_name
        name = field_name.lower().strip('“”"\'')
        # Chuẩn hóa label cho các mục đặc biệt
        if 'quan hệ với người có thay đổi' in name:
            return "Quan hệ với người có thay đổi"
        if 'quan hệ với chủ hộ' in name:
            return "Quan hệ với chủ hộ"
        if 'ý kiến của chủ hộ' in name:
            return "Ý kiến của chủ hộ"
        if 'ý kiến của cha' in name or 'giám hộ' in name:
            return "Ý kiến của cha, mẹ hoặc người giám hộ"
        if 'người kê khai' in name:
            return "Người kê khai"
        if 'những thành viên trong hộ gia đình cùng thay đổi' in name:
            return "Những thành viên trong hộ gia đình cùng thay đổi"
        return field_name.strip('“”"\' ')

    def clean_content(self, text, field_name=None):
        if field_name:
            fn = field_name.strip('“”"\' ')
            # Loại bỏ 'Mục ...', hoặc 'field_name:' ở đầu content
            text = re.sub(r'^Mục\s*[\d\(\)]*\.?\s*', '', text, flags=re.IGNORECASE)
            text = text.strip()
            # Remove field_name (với hoặc không dấu ngoặc kép, hai chấm) ở đầu
            pattern = rf'^(“?{re.escape(fn)}”?|{re.escape(fn)}):?\s*'
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        text = re.sub(r'^:+\s*', '', text)
        return text.strip()

    def chunk_cases(self, line, field_no, field_name, form_code, form_name):
        cases = re.split(r'([a-c]\))', line)
        cur_case = None
        case_text = ""
        for part in cases:
            if re.match(r'[a-c]\)', part):
                if cur_case and case_text:
                    self._chunk_fields_in_case(case_text, cur_case, form_code, form_name)
                cur_case = part
                case_text = ""
            else:
                case_text += part
        if cur_case and case_text:
            self._chunk_fields_in_case(case_text, cur_case, form_code, form_name)

    def _chunk_fields_in_case(self, case_text, cur_case, form_code, form_name):
        for m in re.finditer(r'\+\s*Mục[" ]*(\d+)\.?\s*([^\""]+)[""]*\:\s*([^\+]+)', case_text):
            num, name, content = m.groups()
            norm_name = self.normalize_field_name(name.strip())
            clean_cont = self.clean_content(content.strip(), norm_name)
            self.chunks.append({
                "form_code": form_code,
                "form_name": form_name,
                "field_no": num,
                "field_name": norm_name,
                "chunk_type": "hướng_dẫn_điền",
                "case_label": f"Trường hợp {cur_case}",
                "content": clean_cont,
                "category": "form"
            })

    def chunk_content(self, content, form_code, form_name):
        current_chunk = None
        for idx, line in enumerate(content):
            line = line.strip()
            if not line:
                continue

            if 'Mẫu' in line and ('-' in line or '–' in line) and idx < 3:
                code, name = self.extract_form_info(line)
                self.current_form_code = code
                self.current_form_name = name
                continue

            # Lưu ý / Ví dụ
            if line.lower().startswith("lưu ý"):
                self.chunks.append({
                    "form_code": form_code,
                    "form_name": form_name,
                    "field_no": None,
                    "field_name": "Lưu ý",
                    "chunk_type": "lưu_ý",
                    "content": line,
                    "category": "form"
                })
                continue
            if line.lower().startswith("ví dụ") or line.lower().startswith("vd:"):
                self.chunks.append({
                    "form_code": form_code,
                    "form_name": form_name,
                    "field_no": None,
                    "field_name": "Ví dụ",
                    "chunk_type": "ví_dụ",
                    "content": line,
                    "category": "form"
                })
                continue

            if re.search(r'\sa\)', line) and re.search(r'\+\s*Mục', line):
                self.chunk_cases(line, None, None, form_code, form_name)
                continue

            field_no, field_name = self.extract_field_info(line)
            norm_field_name = self.normalize_field_name(field_name)

            if field_no is not None or norm_field_name is not None:
                if current_chunk:
                    self.chunks.append(current_chunk)
                current_chunk = {
                    "form_code": form_code,
                    "form_name": form_name,
                    "field_no": field_no,
                    "field_name": norm_field_name,
                    "chunk_type": "hướng_dẫn_điền",
                    "content": self.clean_content(line, norm_field_name),
                    "category": "form"
                }
            else:
                if re.search(r'Mục\s+\d+\.', line) or re.search(r'^\d+\.', line):
                    if current_chunk:
                        self.chunks.append(current_chunk)
                    field_no, field_name = self.extract_field_info(line)
                    norm_field_name = self.normalize_field_name(field_name)
                    if field_no is None and norm_field_name is None:
                        if ":" in line:
                            field_name = line.split(":")[0].strip()
                            norm_field_name = self.normalize_field_name(field_name)
                            content_part = line.split(":", 1)[1].strip()
                        else:
                            norm_field_name = "Mục không xác định"
                            content_part = line
                        current_chunk = {
                            "form_code": form_code,
                            "form_name": form_name,
                            "field_no": None,
                            "field_name": norm_field_name,
                            "chunk_type": "hướng_dẫn_điền",
                            "content": content_part,
                            "category": "form"
                        }
                    else:
                        current_chunk = {
                            "form_code": form_code,
                            "form_name": form_name,
                            "field_no": field_no,
                            "field_name": norm_field_name,
                            "chunk_type": "hướng_dẫn_điền",
                            "content": self.clean_content(line, norm_field_name),
                            "category": "form"
                        }
                else:
                    if ":" in line and ("Mục" in line or re.match(r'^[A-Za-zÀ-ỹ ,/()\-]+:', line)):
                        if current_chunk:
                            self.chunks.append(current_chunk)
                        if ":" in line:
                            field_name = line.split(":")[0].strip()
                            norm_field_name = self.normalize_field_name(field_name)
                            content_part = line.split(":", 1)[1].strip()
                        else:
                            norm_field_name = self.normalize_field_name(line.strip())
                            content_part = ""
                        current_chunk = {
                            "form_code": form_code,
                            "form_name": form_name,
                            "field_no": None,
                            "field_name": norm_field_name,
                            "chunk_type": "hướng_dẫn_điền",
                            "content": content_part,
                            "category": "form"
                        }
                    elif '"' in line and "Mục" in line and "cần ghi" in line:
                        if current_chunk:
                            self.chunks.append(current_chunk)
                        match = re.search(r'Mục\s*"([^"]+)"', line)
                        if match:
                            norm_field_name = self.normalize_field_name(match.group(1))
                            content_start = line.find('"', line.find('"') + 1) + 1
                            content_part = line[content_start:].strip()
                        else:
                            norm_field_name = "Mục không xác định"
                            content_part = line
                        current_chunk = {
                            "form_code": form_code,
                            "form_name": form_name,
                            "field_no": None,
                            "field_name": norm_field_name,
                            "chunk_type": "hướng_dẫn_điền",
                            "content": content_part,
                            "category": "form"
                        }
                    else:
                        if current_chunk:
                            current_chunk["content"] += " " + line

        if current_chunk:
            self.chunks.append(current_chunk)

    def process_folder(self, folder_path):
        folder = Path(folder_path)
        for docx_file in folder.glob("*.docx"):
            logger.info(f"Processing: {docx_file.name}")
            content = self.parse_docx_content(docx_file)
            code, name = self.extract_form_info(content[0]) if content else ("UNKNOWN", docx_file.stem)
            self.chunk_content(content, code, name)

    def save_to_json(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self.chunks)} chunks to {output_path}")

def main():
    chunker = FormChunker()
    folder_path = "filling_guide"
    chunker.process_folder(folder_path)
    output_path = "chunking/output_json/form_chunks.json"
    chunker.save_to_json(output_path)
    print(f"Processing complete! Generated {len(chunker.chunks)} chunks.")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    main()
