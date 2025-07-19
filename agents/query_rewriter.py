import re
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Các cụm từ mở đầu không giá trị
UNNECESSARY_PHRASES = [
    r"mình muốn hỏi",
    r"tư vấn giúp",
    r"cho mình hỏi",
    r"xin hỏi",
    r"bạn ơi",
    r"ad ơi",
    r"có ai biết",
    r"ai biết cho hỏi",
    r"mọi người cho hỏi",
    r"em muốn hỏi",
    r"tôi muốn hỏi",
    r"làm ơn cho hỏi",
    r"cần tư vấn",
    r"giúp em với",
    r"giúp mình với",
    r"giúp với",
]

STOPWORDS = set([
    "là", "và", "của", "cho", "với", "có", "không", "như", "được", "trong", "khi", "đã", "này", "đó", "thì", "lại", "nên", "rồi", "nữa", "vẫn", "đang"
])

EMOJI_PATTERN = re.compile("[\U00010000-\U0010ffff]+", flags=re.UNICODE)
HTML_TAG_PATTERN = re.compile(r'<.*?>')
STRANGE_CHAR_PATTERN = re.compile(r'[^\w\s.,:;!?()\-–—/\[\]{}@#%&*+=<>\u00C0-\u1EF9]')
MULTI_SPACE_PATTERN = re.compile(r'\s+')

class QueryRewriter:
    def __init__(self):
        pass

    # --- Tầng 1: Làm sạch truy vấn ---
    def rule_based_clean(self, text: str) -> str:
        # 1. Bỏ emoji
        text = EMOJI_PATTERN.sub('', text)
        # 2. Bỏ html tag
        text = HTML_TAG_PATTERN.sub('', text)
        # 3. Bỏ ký tự lạ
        text = STRANGE_CHAR_PATTERN.sub(' ', text)
        # 4. Bỏ xuống dòng
        text = text.replace('\n', ' ').replace('\r', ' ')
        # 5. Loại cụm từ mở đầu
        for phrase in UNNECESSARY_PHRASES:
            if re.search(phrase, text, re.IGNORECASE):
                text = re.sub(phrase, '', text, flags=re.IGNORECASE)
        # 6. Chuẩn hóa khoảng trắng
        text = MULTI_SPACE_PATTERN.sub(' ', text).strip()
        return text

    # --- Tầng 2: Phân tích thông minh ---
    def detect_intent(self, text: str) -> str:
        """
        Phát hiện intent dựa trên rule đơn giản (có thể thay bằng model)
        """
        text_lower = text.lower()
        if any(x in text_lower for x in ["lệ phí", "phí", "mức phí", "bao nhiêu tiền", "giá"]):
            return "fee"
        if any(x in text_lower for x in ["giấy tờ", "hồ sơ", "cần những gì", "cần giấy gì", "thủ tục"]):
            return "document"
        if any(x in text_lower for x in ["bao lâu", "thời gian", "mất bao lâu", "trong bao lâu"]):
            return "time"
        if any(x in text_lower for x in ["đối tượng", "ai", "dành cho ai"]):
            return "subject"
        if any(x in text_lower for x in ["biểu mẫu", "mẫu", "form", "ct01", "ct02"]):
            return "form"
        return "general"

    def extract_meta(self, text: str) -> Dict[str, str]:
        """
        Trích xuất procedure, subject, form từ câu hỏi (rule-based, có thể thay bằng NER/model)
        """
        meta = {}
        # Procedure: tìm các cụm từ như "đăng ký tạm trú", "cấp lại thẻ", ...
        m = re.search(r'(đăng ký [\w ]+|cấp lại [\w ]+|gia hạn [\w ]+|xin [\w ]+|thủ tục [\w ]+)', text.lower())
        if m:
            meta['procedure'] = m.group(0)
        # Subject: người nước ngoài, công dân, trẻ em, ...
        m = re.search(r'(người nước ngoài|công dân|trẻ em|học sinh|sinh viên|người cao tuổi)', text.lower())
        if m:
            meta['subject'] = m.group(0)
        # Form: CT01, CT02, ...
        m = re.search(r'(ct0\d+|ct\d+|mẫu [a-z0-9]+)', text.lower())
        if m:
            meta['form'] = m.group(0)
        return meta

    # --- Tầng 3: Tái tạo câu hỏi ---
    def rewrite_with_template(self, intent: str, meta: Dict[str, str]) -> str:
        """
        Sinh câu hỏi mới từ intent + meta (template động)
        """
        procedure = meta.get('procedure', '')
        subject = meta.get('subject', '')
        form = meta.get('form', '')
        if intent == "fee" and procedure:
            if subject:
                return f"{subject.capitalize()} cần nộp lệ phí bao nhiêu khi thực hiện thủ tục {procedure}?"
            return f"Lệ phí thực hiện thủ tục {procedure} là bao nhiêu?"
        if intent == "document" and procedure:
            if subject:
                return f"{subject.capitalize()} cần chuẩn bị những giấy tờ gì để làm thủ tục {procedure}?"
            return f"Cần chuẩn bị những giấy tờ gì để làm thủ tục {procedure}?"
        if intent == "time" and procedure:
            return f"Thời gian hoàn thành thủ tục {procedure} là bao lâu?"
        if intent == "form" and form:
            return f"Biểu mẫu {form.upper()} dùng trong thủ tục nào và điền như thế nào?"
        # fallback
        return ""

    def rewrite_with_llm(self, original: str, context: Optional[str], intent: str, meta: Dict[str, str]) -> str:
        """
        Dùng LLM để rewrite, giữ ý định gốc, bổ sung context nếu có
        """
        # Tạm thời trả về câu hỏi gốc đã clean thay vì prompt
        return original

    def rewrite(self, text: str, context: Optional[str] = None) -> str:
        """
        Pipeline 3 tầng: clean -> intent/meta -> rewrite
        """
        clean = self.rule_based_clean(text)
        intent = self.detect_intent(clean)
        meta = self.extract_meta(clean)
        logger.info(f"[QueryRewriter] Clean: {clean}")
        logger.info(f"[QueryRewriter] Intent: {intent}")
        logger.info(f"[QueryRewriter] Meta: {meta}")
        rewritten = self.rewrite_with_template(intent, meta)
        if rewritten:
            logger.info(f"[QueryRewriter] Rewrite by template: {rewritten}")
            return rewritten
        # fallback dùng LLM
        rewritten = self.rewrite_with_llm(clean, context, intent, meta)
        logger.info(f"[QueryRewriter] Rewrite by LLM fallback: {rewritten}")
        return rewritten

    # Backward compatibility
    def rewrite_with_context(self, text: str, conversation_context: Optional[str] = None) -> str:
        return self.rewrite(text, conversation_context) 