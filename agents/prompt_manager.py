from typing import Dict, List, Optional, Tuple
import logging
from .prompt_templates import prompt_templates, CategoryType
from .intent_detector import IntentType, intent_detector

logger = logging.getLogger(__name__)

class PromptManager:
    """Quản lý việc tạo prompt động dựa trên category và context"""
    
    def __init__(self):
        self.prompt_templates = prompt_templates
        self.intent_detector = intent_detector
    
    def create_dynamic_prompt(self, 
                            question: str, 
                            chunks: List[Dict], 
                            intent: Optional[IntentType] = None,
                            category: Optional[CategoryType] = None) -> str:
        """
        Tạo prompt động dựa trên câu hỏi, chunks và intent/category
        
        Args:
            question: Câu hỏi của người dùng
            chunks: Danh sách chunks từ search
            intent: Intent đã detect (optional)
            category: Category cụ thể (optional)
            
        Returns:
            str: Prompt hoàn chỉnh
        """
        # Xác định category
        if category is None:
            if intent is None:
                # Detect intent từ câu hỏi
                intent, metadata = self.intent_detector.detect_intent(question)
                logger.info(f"Auto-detected intent: {intent.value}")
            
            # Map intent to category
            intent_to_category = {
                IntentType.LAW: CategoryType.LAW,
                IntentType.FORM: CategoryType.FORM,
                IntentType.AMBIGUOUS: CategoryType.GENERAL,
                IntentType.UNKNOWN: CategoryType.GENERAL,
                IntentType.PROCEDURE: CategoryType.PROCEDURE,
                IntentType.TERM: CategoryType.TERM,
            }
            category = intent_to_category.get(intent, CategoryType.GENERAL)
        
        # Lấy prompt template theo category
        prompt_template = self.prompt_templates.get_prompt_by_category(category)
        
        # Format context theo category
        formatted_context = self.prompt_templates.format_context_by_category(chunks, category)
        
        # Tạo prompt hoàn chỉnh
        final_prompt = prompt_template.format(
            context=formatted_context,
            question=question
        )
        
        logger.info(f"Created dynamic prompt for category: {category.value}")
        return final_prompt
    
    def create_multi_category_prompt(self, 
                                   question: str, 
                                   chunks: List[Dict]) -> str:
        """
        Tạo prompt cho trường hợp có nhiều category trong chunks
        
        Args:
            question: Câu hỏi của người dùng
            chunks: Danh sách chunks từ search
            
        Returns:
            str: Prompt hoàn chỉnh
        """
        # Phân tích chunks để xác định categories
        category_chunks = self._categorize_chunks(chunks)
        
        if len(category_chunks) == 1:
            # Chỉ có một category, sử dụng prompt đơn giản
            category = list(category_chunks.keys())[0]
            return self.create_dynamic_prompt(question, chunks, category=category)
        
        # Có nhiều categories, tạo prompt tổng hợp
        return self._create_combined_prompt(question, category_chunks)
    
    def _categorize_chunks(self, chunks: List[Dict]) -> Dict[CategoryType, List[Dict]]:
        """
        Phân loại chunks theo category
        
        Args:
            chunks: Danh sách chunks
            
        Returns:
            Dict[CategoryType, List[Dict]]: Chunks được phân loại
        """
        categorized = {
            CategoryType.LAW: [],
            CategoryType.FORM: [],
            CategoryType.PROCEDURE: [],
            CategoryType.GENERAL: []
        }
        
        for chunk in chunks:
            chunk_category = chunk.get("category", "")
            chunk_type = chunk.get("type", "")
            
            if chunk_category == "law" or chunk_type == "law":
                categorized[CategoryType.LAW].append(chunk)
            elif chunk_category == "form" or chunk_type == "form":
                categorized[CategoryType.FORM].append(chunk)
            elif "procedure" in chunk_category.lower() or "procedure" in chunk_type.lower():
                categorized[CategoryType.PROCEDURE].append(chunk)
            else:
                categorized[CategoryType.GENERAL].append(chunk)
        
        # Loại bỏ categories rỗng
        return {k: v for k, v in categorized.items() if v}
    
    def _create_combined_prompt(self, 
                              question: str, 
                              category_chunks: Dict[CategoryType, List[Dict]]) -> str:
        """
        Tạo prompt tổng hợp cho nhiều categories
        
        Args:
            question: Câu hỏi của người dùng
            category_chunks: Chunks được phân loại theo category
            
        Returns:
            str: Prompt tổng hợp
        """
        base_prompt = """Bạn là trợ lý pháp lý chuyên về pháp luật hành chính và cư trú tại Việt Nam.

VAI TRÒ VÀ TRÁCH NHIỆM:
- Phân tích câu hỏi và trả lời toàn diện dựa trên thông tin được cung cấp
- Kết hợp thông tin từ các nguồn khác nhau một cách logic
- Đưa ra hướng dẫn thực tế và khả thi
- Trích dẫn nguồn thông tin khi cần thiết

CÂU HỎI: {question}

THÔNG TIN THAM KHẢO:"""

        # Thêm thông tin từ từng category
        context_parts = []
        
        for category, chunks in category_chunks.items():
            if category == CategoryType.LAW:
                context_parts.append("\n--- QUY ĐỊNH PHÁP LUẬT ---")
                context_parts.append(self.prompt_templates.format_context_by_category(chunks, category))
            elif category == CategoryType.FORM:
                context_parts.append("\n--- HƯỚNG DẪN BIỂU MẪU ---")
                context_parts.append(self.prompt_templates.format_context_by_category(chunks, category))
            elif category == CategoryType.PROCEDURE:
                context_parts.append("\n--- THỦ TỤC HÀNH CHÍNH ---")
                context_parts.append(self.prompt_templates.format_context_by_category(chunks, category))
            else:
                context_parts.append("\n--- THÔNG TIN KHÁC ---")
                context_parts.append(self.prompt_templates.format_context_by_category(chunks, category))
        
        context = "".join(context_parts)
        
        # Thêm hướng dẫn trả lời
        response_guide = """

HƯỚNG DẪN TRẢ LỜI:
1. Phân tích câu hỏi để xác định các khía cạnh cần trả lời
2. Kết hợp thông tin từ các nguồn khác nhau một cách logic
3. Trả lời theo thứ tự ưu tiên: quy định pháp luật → thủ tục → hướng dẫn thực hành
4. Đưa ra lời khuyên thực tế và khả thi
5. Nếu cần thêm thông tin, hãy nêu rõ và hướng dẫn cách bổ sung

LƯU Ý:
- Trả lời toàn diện, bao gồm cả lý thuyết và thực hành
- Kết hợp thông tin từ các nguồn một cách mạch lạc
- Đưa ra hướng dẫn cụ thể và thực tế
- Trích dẫn nguồn thông tin khi cần thiết

TRẢ LỜI:"""

        return base_prompt.format(question=question) + context + response_guide
    
    def create_specialized_prompt(self, 
                                question: str, 
                                chunks: List[Dict], 
                                specialization: str) -> str:
        """
        Tạo prompt chuyên biệt cho các trường hợp đặc biệt
        
        Args:
            question: Câu hỏi của người dùng
            chunks: Danh sách chunks từ search
            specialization: Loại chuyên biệt (e.g., "emergency", "detailed", "simple")
            
        Returns:
            str: Prompt chuyên biệt
        """
        if specialization == "emergency":
            return self._create_emergency_prompt(question, chunks)
        elif specialization == "detailed":
            return self._create_detailed_prompt(question, chunks)
        elif specialization == "simple":
            return self._create_simple_prompt(question, chunks)
        else:
            return self.create_dynamic_prompt(question, chunks)
    
    def _create_emergency_prompt(self, question: str, chunks: List[Dict]) -> str:
        """Prompt cho trường hợp khẩn cấp - trả lời ngắn gọn, trực tiếp"""
        return f"""Bạn là chuyên gia tư vấn khẩn cấp về pháp luật cư trú.

CÂU HỎI: {question}

THÔNG TIN THAM KHẢO:
{self.prompt_templates.format_context_by_category(chunks, CategoryType.GENERAL)}

HƯỚNG DẪN: Trả lời ngắn gọn, trực tiếp, tập trung vào thông tin quan trọng nhất. Đưa ra hướng dẫn cụ thể và khả thi ngay lập tức.

TRẢ LỜI:"""
    
    def _create_detailed_prompt(self, question: str, chunks: List[Dict]) -> str:
        """Prompt cho trường hợp cần trả lời chi tiết"""
        return f"""Bạn là chuyên gia pháp lý cao cấp, chuyên sâu về pháp luật hành chính và cư trú.

CÂU HỎI: {question}

THÔNG TIN THAM KHẢO:
{self.prompt_templates.format_context_by_category(chunks, CategoryType.GENERAL)}

HƯỚNG DẪN: 
1. Phân tích chi tiết vấn đề từ góc độ pháp lý
2. Trích dẫn đầy đủ các quy định liên quan
3. Giải thích ý nghĩa và mục đích của từng quy định
4. Đưa ra các trường hợp áp dụng cụ thể
5. Phân tích các rủi ro và lưu ý quan trọng
6. Đưa ra khuyến nghị chi tiết và toàn diện

TRẢ LỜI:"""
    
    def _create_simple_prompt(self, question: str, chunks: List[Dict]) -> str:
        """Prompt cho trường hợp cần trả lời đơn giản, dễ hiểu"""
        return f"""Bạn là trợ lý thân thiện, chuyên giải thích pháp luật một cách đơn giản, dễ hiểu.

CÂU HỎI: {question}

THÔNG TIN THAM KHẢO:
{self.prompt_templates.format_context_by_category(chunks, CategoryType.GENERAL)}

HƯỚNG DẪN: 
- Sử dụng ngôn ngữ đơn giản, dễ hiểu
- Tránh thuật ngữ pháp lý phức tạp
- Đưa ra ví dụ cụ thể, thực tế
- Tập trung vào những gì người dùng cần làm
- Đưa ra lời khuyên thực tế và khả thi

TRẢ LỜI:"""

# Singleton instance
prompt_manager = PromptManager() 