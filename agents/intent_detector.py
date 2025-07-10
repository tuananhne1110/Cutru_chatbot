import re
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from .prompt_templates import prompt_templates, CategoryType

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Các loại intent của câu hỏi"""
    LAW = "law"           # Tra cứu luật pháp
    FORM = "form"         # Hướng dẫn điền biểu mẫu
    TERM = "term"         # Tra cứu thuật ngữ, định nghĩa
    PROCEDURE = "procedure"  # Thủ tục hành chính
    TEMPLATE = "template"     # Biểu mẫu gốc (template)
    AMBIGUOUS = "ambiguous"  # Không rõ ràng, cần search cả hai
    UNKNOWN = "unknown"   # Không xác định được

class IntentDetector:
    """
    Intent Detection & Query Routing
    
    Phân loại câu hỏi thành:
    - LAW: Tra cứu luật pháp
    - FORM: Hướng dẫn điền biểu mẫu  
    - AMBIGUOUS: Không rõ ràng, search cả hai
    """
    
    def __init__(self):
        # Keywords cho intent LAW
        self.law_keywords = [
            r'\b(luật|lệnh|nghị quyết|pháp lệnh|nghị định|quyết định|thông tư|chỉ thị)\b',
            r'\b(điều|khoản|điểm|chương|mục|phần)\s+\d+',
            r'\b(quy định|quy chế|quy tắc|tiêu chuẩn|định mức)\b',
            r'\b(ban hành|có hiệu lực|thi hành|áp dụng)\b',
            r'\b(vi phạm|chế tài|xử phạt|hình phạt)\b',
            r'\b(thẩm quyền|trách nhiệm|nghĩa vụ|quyền lợi)\b',
            r'\b(căn cứ|theo quy định|theo luật|theo điều)\b',
            r'\b(quyền|nghĩa vụ|trách nhiệm|thẩm quyền)\b',
            r'\b(điều kiện|tiêu chuẩn|yêu cầu|điều kiện)\b',
            r'\b(quyết định|ban hành|công bố|thông báo)\b'
        ]
        
        # Keywords cho intent FORM
        self.form_keywords = [
            r'\b(biểu mẫu|tờ khai|đơn|phiếu|giấy)\b',
            r'\b(điền|khai|ghi|viết|kê khai)\b',
            r'\b(mục|trường|ô|cột|dòng)\s+\d+',
            r'\b(hướng dẫn|chỉ dẫn|giải thích)\b',
            r'\b(ký tên|chữ ký|ngày tháng)\b',
            r'\b(đính kèm|kèm theo|giấy tờ)\b',
            r'\b(điền đầy đủ|ghi rõ|viết rõ)\b',
            r'\b(điền theo|ghi theo|viết theo)\b',
            r'\b(lưu ý|chú ý|quan trọng)\b'
        ]
        
        # Keywords cho intent TERM
        self.term_keywords = [
            r'\b(thuật ngữ|định nghĩa|khái niệm|ý nghĩa)\b',
            r'\b(là gì|nghĩa là|có nghĩa|hiểu là)\b',
            r'\b(giải thích|giải nghĩa|định nghĩa)\b',
            r'\b(term|glossary|vocabulary|terminology)\b',
            r'\b(định nghĩa|khái niệm|ý nghĩa|nội hàm)\b',
            r'\b(phân biệt|so sánh|khác nhau|giống nhau)\b',
            r'\b(bao gồm|gồm có|bao hàm|chứa đựng)\b',
            r'\b(đặc điểm|tính chất|đặc trưng|bản chất)\b',
            r'\b(phạm vi|phạm trù|lĩnh vực|ngành)\b',
            r'\b(định nghĩa|giải thích|chú thích|ghi chú)\b'
        ]
        
        # Keywords cho intent PROCEDURE
        self.procedure_keywords = [
            r'\b(thủ tục|quy trình|hồ sơ|giấy tờ)\b',
            r'\b(đăng ký|khai báo|thông báo|nộp hồ sơ)\b',
            r'\b(cư trú|thường trú|tạm trú|đăng ký cư trú)\b',
            r'\b(giải quyết|xử lý|tiếp nhận|thẩm định)\b',
            r'\b(yêu cầu|điều kiện|tiêu chuẩn|hồ sơ)\b',
            r'\b(thời gian|thời hạn|hạn chót|thời gian xử lý)\b',
            r'\b(phí|lệ phí|tiền|chi phí|phí tổn)\b',
            r'\b(địa điểm|nơi|cơ quan|phòng ban)\b',
            r'\b(liên hệ|hỗ trợ|tư vấn|hướng dẫn)\b',
            r'\b(kiểm tra|xác minh|thẩm định|đánh giá)\b',
            r'\b(bước|bước thực hiện|các bước|quy trình)\b',
            r'\b(chuẩn bị|nộp|theo dõi|nhận kết quả)\b'
        ]
        
        # Keywords ambiguous (có thể thuộc cả hai)
        self.ambiguous_keywords = [
            r'\b(thủ tục|quy trình|hồ sơ|giấy tờ)\b',
            r'\b(đăng ký|khai báo|thông báo)\b',
            r'\b(cư trú|thường trú|tạm trú)\b',
            r'\b(giải quyết|xử lý|tiếp nhận)\b',
            r'\b(yêu cầu|điều kiện|tiêu chuẩn)\b',
            r'\b(thời gian|thời hạn|hạn chót)\b',
            r'\b(phí|lệ phí|tiền|chi phí)\b',
            r'\b(địa điểm|nơi|cơ quan)\b',
            r'\b(liên hệ|hỗ trợ|tư vấn)\b',
            r'\b(kiểm tra|xác minh|thẩm định)\b'
        ]
        
        # Keywords cho intent TEMPLATE
        self.template_keywords = [
            r'\b(biểu mẫu gốc|template|file mẫu|tải mẫu|download mẫu|file docx|file pdf|mẫu chuẩn|mẫu gốc)\b',
            r'\b(mẫu\s+(CT01|CT02|NA17|TK\d+))\b',
            r'\b(CT01|CT02|NA17|TK\d+)\b',
            r'\b(tải\s+mẫu|download\s+mẫu|file\s+mẫu)\b'
        ]
        
        # Compile patterns
        self.law_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.law_keywords]
        self.form_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.form_keywords]
        self.term_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.term_keywords]
        self.procedure_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.procedure_keywords]
        self.ambiguous_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.ambiguous_keywords]
        self.template_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.template_keywords]
    
    def detect_intent(self, query: str) -> Tuple[IntentType, Dict]:
        """
        Phát hiện intent của câu hỏi
        
        Args:
            query: Câu hỏi của người dùng
            
        Returns:
            Tuple[IntentType, Dict]: Intent type và metadata
        """
        query_lower = query.lower()
        
        # Đếm số lượng matches cho mỗi loại
        law_matches = sum(1 for pattern in self.law_patterns if pattern.search(query_lower))
        form_matches = sum(1 for pattern in self.form_patterns if pattern.search(query_lower))
        term_matches = sum(1 for pattern in self.term_patterns if pattern.search(query_lower))
        procedure_matches = sum(1 for pattern in self.procedure_patterns if pattern.search(query_lower))
        ambiguous_matches = sum(1 for pattern in self.ambiguous_patterns if pattern.search(query_lower))
        template_matches = sum(1 for pattern in self.template_patterns if pattern.search(query_lower))
        
        # Metadata để debug
        metadata = {
            "law_matches": law_matches,
            "form_matches": form_matches,
            "term_matches": term_matches,
            "procedure_matches": procedure_matches,
            "template_matches": template_matches,
            "ambiguous_matches": ambiguous_matches,
            "detected_keywords": self._extract_detected_keywords(query_lower)
        }
        
        # Logic phân loại - ưu tiên TEMPLATE khi có template keywords
        if template_matches > 0:
            # Ưu tiên TEMPLATE nếu có template keywords
            intent = IntentType.TEMPLATE
            confidence = "high" if template_matches >= 2 else "medium"
        elif law_matches > 0 and form_matches == 0 and term_matches == 0:
            intent = IntentType.LAW
            confidence = "high" if law_matches >= 2 else "medium"
        elif form_matches > 0 and law_matches == 0 and term_matches == 0:
            intent = IntentType.FORM
            confidence = "high" if form_matches >= 2 else "medium"
        elif law_matches > 0 and form_matches > 0 and term_matches == 0:
            # Có cả hai loại keywords
            if law_matches > form_matches:
                intent = IntentType.LAW
                confidence = "medium"
            elif form_matches > law_matches:
                intent = IntentType.FORM
                confidence = "medium"
            else:
                intent = IntentType.AMBIGUOUS
                confidence = "low"
        elif term_matches > 0 and law_matches == 0 and form_matches == 0:
            intent = IntentType.TERM
            confidence = "high" if term_matches >= 2 else "medium"
        elif procedure_matches > 0:
            intent = IntentType.PROCEDURE
            confidence = "high" if procedure_matches >= 2 else "medium"
        elif ambiguous_matches > 0:
            # Chỉ có ambiguous keywords
            intent = IntentType.AMBIGUOUS
            confidence = "low"
        else:
            # Không có keywords nào
            intent = IntentType.UNKNOWN
            confidence = "very_low"
        
        metadata["confidence"] = confidence
        metadata["intent"] = intent.value
        
        logger.info(f"Intent Detection: {intent.value} (confidence: {confidence}) - Law: {law_matches}, Form: {form_matches}, Term: {term_matches}, Procedure: {procedure_matches}, Template: {template_matches}, Ambiguous: {ambiguous_matches}")
        
        return intent, metadata
    
    def _extract_detected_keywords(self, query_lower: str) -> Dict[str, List[str]]:
        """Trích xuất các keywords được phát hiện"""
        detected = {
            "law": [],
            "form": [],
            "term": [],
            "procedure": [],
            "ambiguous": [],
            "template": []
        }
        
        for pattern in self.law_patterns:
            if pattern.search(query_lower):
                detected["law"].append(pattern.pattern.replace(r'\b', ''))
        
        for pattern in self.form_patterns:
            if pattern.search(query_lower):
                detected["form"].append(pattern.pattern.replace(r'\b', ''))
        
        for pattern in self.term_patterns:
            if pattern.search(query_lower):
                detected["term"].append(pattern.pattern.replace(r'\b', ''))
        
        for pattern in self.procedure_patterns:
            if pattern.search(query_lower):
                detected["procedure"].append(pattern.pattern.replace(r'\b', ''))
        
        for pattern in self.ambiguous_patterns:
            if pattern.search(query_lower):
                detected["ambiguous"].append(pattern.pattern.replace(r'\b', ''))
        
        for pattern in self.template_patterns:
            if pattern.search(query_lower):
                detected["template"].append(pattern.pattern.replace(r'\b', ''))
        
        return detected
    
    def get_search_collections(self, intent: IntentType, confidence: str) -> List[str]:
        """
        Xác định collections cần search dựa trên intent
        
        Args:
            intent: Intent type
            confidence: Độ tin cậy của detection
            
        Returns:
            List[str]: Danh sách collections cần search
        """
        if intent == IntentType.LAW:
            return ["legal_chunks"]
        elif intent == IntentType.FORM:
            return ["form_chunks"]
        elif intent == IntentType.TERM:
            return ["term_chunks"]
        elif intent == IntentType.PROCEDURE:
            return ["procedure_chunks"]
        elif intent == IntentType.TEMPLATE:
            return ["template_chunks"]
        elif intent == IntentType.AMBIGUOUS:
            # Search cả hai, ưu tiên theo confidence
            if confidence == "low":
                return ["legal_chunks", "form_chunks", "term_chunks", "procedure_chunks", "template_chunks"]  # Cả bốn với ưu tiên ngang nhau
            else:
                return ["legal_chunks", "form_chunks", "term_chunks", "procedure_chunks", "template_chunks"]  # Cả bốn
        else:  # UNKNOWN
            return ["legal_chunks", "form_chunks", "term_chunks", "procedure_chunks", "template_chunks"]  # Search tất cả
    
    def get_search_weights(self, intent: IntentType, confidence: str) -> Dict[str, float]:
        """
        Xác định trọng số cho từng collection khi search
        
        Args:
            intent: Intent type
            confidence: Độ tin cậy của detection
            
        Returns:
            Dict[str, float]: Trọng số cho từng collection
        """
        if intent == IntentType.LAW:
            return {"legal_chunks": 1.0, "form_chunks": 0.0, "term_chunks": 0.0, "procedure_chunks": 0.0, "template_chunks": 0.0}
        elif intent == IntentType.FORM:
            return {"legal_chunks": 0.0, "form_chunks": 1.0, "term_chunks": 0.0, "procedure_chunks": 0.0, "template_chunks": 0.0}
        elif intent == IntentType.TERM:
            return {"legal_chunks": 0.0, "form_chunks": 0.0, "term_chunks": 1.0, "procedure_chunks": 0.0, "template_chunks": 0.0}
        elif intent == IntentType.PROCEDURE:
            return {"legal_chunks": 0.0, "form_chunks": 0.0, "term_chunks": 0.0, "procedure_chunks": 1.0, "template_chunks": 0.0}
        elif intent == IntentType.TEMPLATE:
            return {"legal_chunks": 0.0, "form_chunks": 0.0, "term_chunks": 0.0, "procedure_chunks": 0.0, "template_chunks": 1.0}
        elif intent == IntentType.AMBIGUOUS:
            if confidence == "low":
                return {"legal_chunks": 0.2, "form_chunks": 0.2, "term_chunks": 0.2, "procedure_chunks": 0.2, "template_chunks": 0.2}  # Ngang nhau
            else:
                return {"legal_chunks": 0.2, "form_chunks": 0.2, "term_chunks": 0.2, "procedure_chunks": 0.2, "template_chunks": 0.2}  # Ưu tiên law
        else:  # UNKNOWN
            return {"legal_chunks": 0.2, "form_chunks": 0.2, "term_chunks": 0.2, "procedure_chunks": 0.2, "template_chunks": 0.2}  # Cân bằng
    
    def format_context_by_intent(self, chunks: List[Dict], intent: IntentType) -> str:
        """
        Format context theo intent để tối ưu prompt
        
        Args:
            chunks: Danh sách chunks từ search
            intent: Intent type
            
        Returns:
            str: Context được format
        """
        # Map intent to category
        intent_to_category = {
            IntentType.LAW: CategoryType.LAW,
            IntentType.FORM: CategoryType.FORM,
            IntentType.TERM: CategoryType.TERM,
            IntentType.PROCEDURE: CategoryType.PROCEDURE,
            IntentType.TEMPLATE: CategoryType.TEMPLATE,
            IntentType.AMBIGUOUS: CategoryType.GENERAL,
            IntentType.UNKNOWN: CategoryType.GENERAL
        }
        
        category = intent_to_category.get(intent, CategoryType.GENERAL)
        return prompt_templates.format_context_by_category(chunks, category)
    
    def get_prompt_by_intent(self, intent: IntentType) -> str:
        """
        Lấy prompt phù hợp theo intent
        
        Args:
            intent: Intent type
            
        Returns:
            str: Prompt template
        """
        # Map intent to category
        intent_to_category = {
            IntentType.LAW: CategoryType.LAW,
            IntentType.FORM: CategoryType.FORM,
            IntentType.TERM: CategoryType.TERM,
            IntentType.PROCEDURE: CategoryType.PROCEDURE,
            IntentType.TEMPLATE: CategoryType.TEMPLATE,
            IntentType.AMBIGUOUS: CategoryType.GENERAL,
            IntentType.UNKNOWN: CategoryType.GENERAL
        }
        
        category = intent_to_category.get(intent, CategoryType.GENERAL)
        return prompt_templates.get_prompt_by_category(category)

# Singleton instance
intent_detector = IntentDetector() 