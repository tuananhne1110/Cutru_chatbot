from enum import Enum
from typing import Dict, List
import logging
import os
import yaml



logger = logging.getLogger(__name__)



from typing import Any, Dict


class DocumentProcessor:
    """Xử lý và định dạng tài liệu được truy xuất"""
    
    @staticmethod
    def format_document_content(payload: Dict[str, Any], doc_id: int) -> str:
        """Format nội dung một tài liệu thành chuỗi có cấu trúc"""
        content = f"<document id=\"{doc_id}\">\n"
        
        
        field_mappings = {
            # Luật pháp
            "law_name": "Tên luật",
            "law_code": "Luật số", 
            "promulgation_date": "Ngày ban hành",
            "chapter": "Chương",
   
            # Thủ tục hành chính
            "procedure_code": "Mã thủ tục",
            "decision_number": "Số quyết định",
            "procedure_name": "Tên thủ tục",
            "implementation_level": "Cấp thực hiện",
            "procedure_type": "Loại thủ tục",
            "field": "Lĩnh vực",
            "source_section": "Mục nguồn",
            
            # Thuật ngữ
            "term": "Thuật ngữ",
            
            # Giấy tờ/Biểu mẫu
            "form_code": "Mã giấy tờ",
            "form_name": "Tên giấy tờ",
            "field_no": "Trường số",
            "field_name": "Tên trường",
            
            # Nội dung chung
            "content": "Nội dung"
        }
        
        for key, value in payload.items():
            if key in field_mappings:
                display_name = field_mappings[key]
                content += f"- {display_name}: {value}\n"
        
        content += "</document>\n\n"
        return content

document_processor = DocumentProcessor()


class CategoryType(Enum):
    """Các loại category của nội dung"""
    LAW = "law"           # Quy định pháp luật
    FORM = "form"         # Hướng dẫn biểu mẫu
    TERM = "term"         # Thuật ngữ, định nghĩa
    PROCEDURE = "procedure"  # Thủ tục hành chính
    TEMPLATE = "template"     # Biểu mẫu gốc (template)
    GENERAL = "general"   # Thông tin chung

class PromptTemplates:
    """Quản lý các prompt template chuyên biệt cho từng category"""
    def __init__(self, config_path: str = "config/config.yaml"):
        self.base_template = self._load_base_template(config_path)

    def _load_base_template(self, config_path: str) -> str:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                pt = config.get("prompt_templates", {})
                if pt and pt.get("base_template"):
                    return pt["base_template"]
        # fallback nếu không có file hoặc key
        return """
        Bạn là chuyên gia pháp lý về pháp luật hành chính và cư trú tại Việt Nam.
        VAI TRÒ VÀ TRÁCH NHIỆM:
        - Trả lời chính xác, chi tiết và đầy đủ theo câu hỏi bên dưới
        - Chỉ dùng thông tin từ phần THÔNG TIN THAM KHẢO để trả lời. Không suy đoán ngoài phạm vi
        - Khi trả lời về thủ tục, giấy tờ, hồ sơ: liệt kê đầy đủ từng loại giấy tờ, số lượng, yêu cầu cụ thể
        - Khi trả lời về luật pháp: TRÍCH DẪN ĐẦY ĐỦ nội dung các điều, khoản, điểm liên quan (không chỉ nhắc tên điều luật)
        - Sắp xếp thông tin theo thứ tự logic và dễ hiểu

        THÔNG TIN THAM KHẢO:
        {context}

        CÂU HỎI: {question}

        TRẢ LỜI:"""

   
    def get_prompt_by_category(self) -> str:
        """
        Lấy prompt template theo category
        
        Args:
            category: Loại category
            
        Returns:
            str: Prompt template
        """
      
        return self.base_template.format(
            context="{context}",
            question="{question}",
        )

    def format_context_by_category(self, chunks: List[Dict]) -> str:
        """
        Format context theo category để tối ưu prompt
        
        Args:
            chunks: Danh sách chunks từ search
            category: Category type
            
        Returns:
            str: Context được format
        """
        if not chunks:
            return ""
        
        # context_parts = []
        filtered_content = ""
        
        for idx, chunk in enumerate(chunks):
            formatted_doc = document_processor.format_document_content(
                payload=chunk, 
                doc_id=idx+1,
            )
            filtered_content += formatted_doc
        return filtered_content

# Singleton instance
prompt_templates = PromptTemplates() 

