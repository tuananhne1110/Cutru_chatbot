
from string import Template
from typing import Any, Dict, Union
from typing_extensions import TypedDict

class TextChatMessage(TypedDict):
    """Representation of a single text-based chat message in the chat history."""
    role: str  # Either "system", "user", or "assistant"
    content: Union[str, Template]  # The text content of the message (could also be a string.Template instance)

class DocumentProcessor:
    """Xử lý và định dạng tài liệu được truy xuất"""
    
    @staticmethod
    def format_document_content(payload: Dict[str, Any], doc_id: int) -> str:
        """Format nội dung một tài liệu thành chuỗi có cấu trúc"""
        content = f"<document id=\"{doc_id}\">\n"
        
        
        # Mapping cho các loại tài liệu khác nhau
        field_mappings = {
            # Luật pháp
            "law_name": "Tên luật",
            "law_code": "Luật số", 
            "promulgation_date": "Ngày ban hành",
            "chapter": "Chương",
            # "article": "Điều",
            # "clause": "Khoản",
            # "point": "Điểm",
            
            # Thủ tục hành chính
            "procedure_code": "Mã thủ tục",
            "decision_number": "Số quyết định",
            "procedure_name": "Tên thủ tục",
            "implementation_level": "Cấp thực hiện",
            "procedure_type": "Loại thủ tục",
            "field": "Lĩnh vực",
            "source_section": "Mục nguồn",
            "source": "nguồn",
            "templates": "Giấy tờ",
            
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
                if key == "templates":
                    display_name = field_mappings[key]
                    content += f"- {display_name}:\n"
                    for v in value:
                        content +=f"    {v}\n"
                else :
                    display_name = field_mappings[key]
                    content += f"- {display_name}: {value}\n"
        
        content += "</document>\n\n"
        return content
