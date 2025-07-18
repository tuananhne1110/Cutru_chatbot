from enum import Enum
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

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
    
    def __init__(self):
        # Template base chung cho tất cả categories
        self.base_template = """
        Bạn là chuyên gia pháp lý về pháp luật hành chính và cư trú tại Việt Nam.
        VAI TRÒ VÀ TRÁCH NHIỆM:
        - Trả lời chính xác, ngắn gọn, đúng trọng tâm theo câu hỏi bên dưới
        - Chỉ dùng thông tin từ phần THÔNG TIN THAM KHẢO để trả lời. Không suy đoán ngoài phạm vi

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
        
        context_parts = []
        
        for chunk in chunks:
            if chunk['category'] == "law":
                logger.info(f"check cateogty ======== : {CategoryType.LAW}")

                # Format cho law chunks
                law_name = chunk.get("law_name", "Luật")
                article = chunk.get("article", "")
                chapter = chunk.get("chapter", "")
                clause = chunk.get("clause", "")
                point = chunk.get("point", "")
                
                source_info = f"[{law_name}"
                if article:
                    source_info += f" - {article}"
                if chapter:
                    source_info += f" - {chapter}"
                if clause:
                    source_info += f" - Khoản {clause}"
                if point:
                    source_info += f" - Điểm {point}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{chunk.get('content', '')}")
                
            elif chunk['category'] == "form":
                logger.info(f"check cateogty ======== : {CategoryType.FORM}")

                # Format cho form chunks
                form_code = chunk.get("form_code", "Form")
                field_no = chunk.get("field_no", "")
                field_name = chunk.get("field_name", "")
                chunk_type_detail = chunk.get("chunk_type", "")
                
                source_info = f"[{form_code}"
                if field_no:
                    source_info += f" - Mục {field_no}"
                if field_name:
                    source_info += f" - {field_name}"
                if chunk_type_detail:
                    source_info += f" - {chunk_type_detail}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{chunk.get('content', '')}")
                
            elif chunk['category'] == "term":
                logger.info(f"check cateogty ======== : {CategoryType.TERM}")

                # Format cho term chunks
                term = chunk.get("term", "Thuật ngữ")
                definition = chunk.get("definition", "")
                category_detail = chunk.get("category", "")
                
                source_info = f"[{term}"
                if definition:
                    source_info += f" - Định nghĩa"
                if category_detail:
                    source_info += f" - {category_detail}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{chunk.get('content', '')}")
                
            elif chunk['category'] == "procedure":
                logger.info(f"check cateogty ======== : {CategoryType.PROCEDURE}")

                # Format cho procedure chunks
                procedure_name = chunk.get("procedure_name", "Thủ tục")
                procedure_code = chunk.get("procedure_code", "")
                implementation_level = chunk.get("implementation_level", "")
                chunk_index = chunk.get("chunk_index", "")
                total_chunks = chunk.get("total_chunks", "")

                source_info = f"[{procedure_name}"
                if procedure_code:
                    source_info += f" - {procedure_code}"
                if implementation_level:
                    source_info += f" - {implementation_level}"
                if chunk_index and total_chunks:
                    source_info += f" - Phần {chunk_index}/{total_chunks}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{chunk.get('text', '')}")
                for k , value in chunk.items():
                    logger.info(f"key : {k} \nValue : {value}")

            elif chunk['category'] == "templates":
                code = chunk.get("code", "")
                name = chunk.get("name", "")
                description = chunk.get("description", "")
                file_url = chunk.get("file_url", "")
                procedures = chunk.get("procedures", "")
                context_parts.append(
                    f"[{code}] {name}\nMô tả: {description}\nThủ tục liên quan: {procedures}\nFile: {file_url}"
                )
                
            else:
                context_parts.append("================ Không cần tham khảo ở dòng này ================")
        return "\n\n".join(context_parts)

# Singleton instance
prompt_templates = PromptTemplates() 