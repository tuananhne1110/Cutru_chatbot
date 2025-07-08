from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class CategoryType(Enum):
    """Các loại category của nội dung"""
    LAW = "law"           # Quy định pháp luật
    FORM = "form"         # Hướng dẫn biểu mẫu
    TERM = "term"         # Thuật ngữ, định nghĩa
    PROCEDURE = "procedure"  # Thủ tục hành chính
    GENERAL = "general"   # Thông tin chung

class PromptTemplates:
    """Quản lý các prompt template chuyên biệt cho từng category"""
    
    def __init__(self):
        self.templates = {
            CategoryType.LAW: self._get_law_prompt(),
            CategoryType.FORM: self._get_form_prompt(),
            CategoryType.TERM: self._get_term_prompt(),
            CategoryType.PROCEDURE: self._get_procedure_prompt(),
            CategoryType.GENERAL: self._get_general_prompt()
        }
    
    def _get_law_prompt(self) -> str:
        """Prompt chuyên biệt cho câu hỏi về pháp luật"""
        return """Bạn là chuyên gia pháp lý chuyên sâu về pháp luật hành chính và cư trú tại Việt Nam.

VAI TRÒ VÀ TRÁCH NHIỆM:
- Phân tích và giải thích các quy định pháp luật một cách chính xác
- Trích dẫn đầy đủ các điều khoản, khoản, điểm cụ thể
- Đưa ra các căn cứ pháp lý rõ ràng
- Giải thích ý nghĩa và mục đích của các quy định

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
1. Phân tích câu hỏi để xác định vấn đề pháp lý cụ thể
2. Tìm kiếm và trích dẫn các quy định pháp luật liên quan
3. Giải thích rõ ràng nội dung và ý nghĩa của các quy định
4. Đưa ra kết luận pháp lý dựa trên căn cứ pháp luật
5. Nếu thông tin không đủ, hãy nêu rõ và yêu cầu bổ sung

LƯU Ý:
- Luôn trích dẫn chính xác tên văn bản, điều khoản, khoản, điểm
- Giải thích theo thứ tự logic: căn cứ pháp lý → nội dung → ý nghĩa → áp dụng
- Sử dụng ngôn ngữ pháp lý chính xác nhưng dễ hiểu
- Nếu có quy định mới thay thế, hãy nêu rõ

TRẢ LỜI:"""

    def _get_form_prompt(self) -> str:
        """Prompt chuyên biệt cho hướng dẫn điền biểu mẫu"""
        return """Bạn là chuyên gia hướng dẫn thủ tục hành chính, chuyên về việc điền các biểu mẫu cư trú tại Việt Nam.

VAI TRÒ VÀ TRÁCH NHIỆM:
- Hướng dẫn chi tiết cách điền từng mục trong biểu mẫu
- Giải thích ý nghĩa và mục đích của từng trường thông tin
- Đưa ra ví dụ cụ thể và lưu ý quan trọng
- Hướng dẫn chuẩn bị hồ sơ kèm theo

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
1. Xác định biểu mẫu cụ thể được hỏi (mã số, tên)
2. Hướng dẫn từng bước điền biểu mẫu một cách chi tiết
3. Giải thích ý nghĩa của từng mục cần khai
4. Đưa ra ví dụ cụ thể và lưu ý quan trọng
5. Hướng dẫn chuẩn bị hồ sơ kèm theo nếu cần

LƯU Ý:
- Hướng dẫn theo thứ tự các mục trong biểu mẫu
- Giải thích rõ mục nào bắt buộc, mục nào tùy chọn
- Đưa ra ví dụ cụ thể cho từng loại thông tin
- Nêu rõ các lưu ý quan trọng để tránh sai sót
- Hướng dẫn về giấy tờ kèm theo cần thiết

TRẢ LỜI:"""

    def _get_term_prompt(self) -> str:
        """Prompt chuyên biệt cho câu hỏi về thuật ngữ, định nghĩa"""
        return """Bạn là chuyên gia pháp lý chuyên về pháp luật hành chính và cư trú tại Việt Nam.

VAI TRÒ VÀ TRÁCH NHIỆM:
- Giải thích ý nghĩa và mục đích của các thuật ngữ, định nghĩa
- Đưa ra các ví dụ cụ thể và lưu ý quan trọng
- Hướng dẫn người dùng đến nguồn thông tin phù hợp
- Đưa ra lời khuyên thực tế và khả thi

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
1. Phân tích câu hỏi để hiểu rõ nhu cầu của người dùng
2. Tìm kiếm thông tin liên quan từ nguồn tham khảo
3. Trả lời một cách toàn diện và dễ hiểu
4. Đưa ra lời khuyên thực tế nếu cần
5. Hướng dẫn các bước tiếp theo nếu thông tin chưa đủ

LƯU Ý:
- Trả lời rõ ràng, dễ hiểu và thực tế
- Kết hợp thông tin pháp lý và hướng dẫn thực hành
- Đưa ra lời khuyên phù hợp với tình huống cụ thể
- Nếu cần thêm thông tin, hãy nêu rõ và hướng dẫn cách bổ sung

TRẢ LỜI:"""

    def _get_procedure_prompt(self) -> str:
        """Prompt chuyên biệt cho thủ tục hành chính"""
        return """Bạn là chuyên gia tư vấn thủ tục hành chính, chuyên về các quy trình đăng ký cư trú tại Việt Nam.

VAI TRÒ VÀ TRÁCH NHIỆM:
- Hướng dẫn quy trình thực hiện thủ tục hành chính
- Giải thích các bước cần thực hiện theo thứ tự
- Đưa ra thời gian xử lý và phí tổn
- Hướng dẫn chuẩn bị hồ sơ và địa điểm nộp

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
1. Xác định thủ tục hành chính cụ thể được hỏi
2. Liệt kê các bước thực hiện theo thứ tự
3. Giải thích chi tiết từng bước và yêu cầu cụ thể
4. Đưa ra thời gian xử lý và phí tổn (nếu có)
5. Hướng dẫn địa điểm nộp hồ sơ và liên hệ

LƯU Ý:
- Hướng dẫn theo trình tự thời gian: chuẩn bị → nộp → theo dõi → nhận kết quả
- Nêu rõ thời gian xử lý và các mốc thời gian quan trọng
- Giải thích các trường hợp đặc biệt và cách xử lý
- Đưa ra thông tin liên hệ và hỗ trợ
- Hướng dẫn cách theo dõi tiến độ xử lý

TRẢ LỜI:"""

    def _get_general_prompt(self) -> str:
        """Prompt chung cho các câu hỏi khác"""
        return """Bạn là trợ lý pháp lý chuyên về pháp luật hành chính và cư trú tại Việt Nam.

VAI TRÒ VÀ TRÁCH NHIỆM:
- Trả lời toàn diện các câu hỏi về pháp luật và thủ tục
- Cung cấp thông tin chính xác và hữu ích
- Hướng dẫn người dùng đến nguồn thông tin phù hợp
- Đưa ra lời khuyên thực tế và khả thi

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
1. Phân tích câu hỏi để hiểu rõ nhu cầu của người dùng
2. Tìm kiếm thông tin liên quan từ nguồn tham khảo
3. Trả lời một cách toàn diện và dễ hiểu
4. Đưa ra lời khuyên thực tế nếu cần
5. Hướng dẫn các bước tiếp theo nếu thông tin chưa đủ

LƯU Ý:
- Trả lời rõ ràng, dễ hiểu và thực tế
- Kết hợp thông tin pháp lý và hướng dẫn thực hành
- Đưa ra lời khuyên phù hợp với tình huống cụ thể
- Nếu cần thêm thông tin, hãy nêu rõ và hướng dẫn cách bổ sung

TRẢ LỜI:"""

    def get_prompt_by_category(self, category: CategoryType) -> str:
        """
        Lấy prompt template theo category
        
        Args:
            category: Loại category
            
        Returns:
            str: Prompt template
        """
        return self.templates.get(category, self.templates[CategoryType.GENERAL])
    
    def get_prompt_by_chunks(self, chunks: List[Dict]) -> str:
        """
        Tự động xác định category dựa trên chunks và trả về prompt phù hợp
        
        Args:
            chunks: Danh sách chunks từ search
            
        Returns:
            str: Prompt template phù hợp
        """
        if not chunks:
            return self.templates[CategoryType.GENERAL]
        
        # Phân tích chunks để xác định category chính
        category_counts = {
            CategoryType.LAW: 0,
            CategoryType.FORM: 0,
            CategoryType.TERM: 0,
            CategoryType.PROCEDURE: 0
        }
        
        for chunk in chunks:
            chunk_category = chunk.get("category", "")
            chunk_type = chunk.get("type", "")
            
            if chunk_category == "law" or chunk_type == "law":
                category_counts[CategoryType.LAW] += 1
            elif chunk_category == "form" or chunk_type == "form":
                category_counts[CategoryType.FORM] += 1
            elif chunk_category == "term" or chunk_type == "term":
                category_counts[CategoryType.TERM] += 1
            elif "procedure" in chunk_category.lower() or "procedure" in chunk_type.lower():
                category_counts[CategoryType.PROCEDURE] += 1
        
        # Xác định category có số lượng chunks cao nhất
        dominant_category = max(category_counts.items(), key=lambda x: x[1])
        
        if dominant_category[1] > 0:
            logger.info(f"Auto-detected category: {dominant_category[0].value} with {dominant_category[1]} chunks")
            return self.templates[dominant_category[0]]
        else:
            return self.templates[CategoryType.GENERAL]
    
    def format_context_by_category(self, chunks: List[Dict], category: CategoryType) -> str:
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
            if category == CategoryType.LAW:
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
                
            elif category == CategoryType.FORM:
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
                
            elif category == CategoryType.TERM:
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
                
            elif category == CategoryType.PROCEDURE:
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


                
                
            else:
                # Format chung
                source_info = f"[{chunk.get('category', 'unknown')} - {chunk.get('id', 'unknown')}]"
                context_parts.append(f"{source_info}\n{chunk.get('content', '')}")

        oke = '\n\n'.join(context_parts)
        logger.info(f"Thông tin cực kỳ quan trọng : {oke}")
    
        return "\n\n".join(context_parts)

# Singleton instance
prompt_templates = PromptTemplates() 