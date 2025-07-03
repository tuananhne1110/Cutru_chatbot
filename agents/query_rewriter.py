import re
from typing import Tuple, Optional, List, Dict
import time
import logging
from transformers.pipelines import pipeline

# Nếu muốn dùng pyvi/vspell thì import ở đây (giả sử chưa cài)
# from pyvi import ViTokenizer, ViUtils
# import vspell

from services.llm_service import call_llm_full

logger = logging.getLogger(__name__)

# Các cụm từ mở đầu/ngữ cảnh không cần thiết
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

# Stopwords tiếng Việt phổ biến (có thể mở rộng)
STOPWORDS = set([
    "là", "và", "của", "cho", "với", "có", "không", "như", "được", "trong", "khi", "đã", "này", "đó", "thì", "lại", "nên", "rồi", "nữa", "vẫn", "đang"
])

# Regex emoji, html, ký tự lạ
EMOJI_PATTERN = re.compile("[\U00010000-\U0010ffff]+", flags=re.UNICODE)
HTML_TAG_PATTERN = re.compile(r'<.*?>')
STRANGE_CHAR_PATTERN = re.compile(r'[^\w\s.,:;!?()\-–—/\[\]{}@#%&*+=<>\u00C0-\u1EF9]')
MULTI_SPACE_PATTERN = re.compile(r'\s+')

# Ngưỡng để trigger paraphrase/LLM
MAX_LEN = 1000  # ký tự
MAX_STOPWORD = 10

class QueryRewriter:
    def __init__(self):
        self.correction_count = 0  # Đếm số lần sửa lỗi chính tả (nếu có)
        # Khởi tạo paraphrase pipeline với BARTpho
        self.paraphrase_pipe = pipeline("text2text-generation", model="vinai/bartpho-syllable")

    def rule_based_clean(self, text: str) -> Tuple[str, dict]:
        info = {"removed_phrases": [], "corrections": 0}
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
                info["removed_phrases"].append(phrase)
        # 6. Sửa lỗi chính tả (nếu tích hợp pyvi/vspell)
        # TODO: Tích hợp pyvi/vspell nếu cần
        # text, n_corrections = vspell.correct(text)
        # info["corrections"] = n_corrections
        # self.correction_count += n_corrections
        # 7. Chuẩn hóa khoảng trắng
        text = MULTI_SPACE_PATTERN.sub(' ', text).strip()
        return text, info

    def need_paraphrase(self, text: str, info: dict) -> bool:
        # Trigger paraphrase nếu quá dài, nhiều stopword, nhiều corrections, hoặc chứa nhiều rác
        if len(text) > MAX_LEN:
            return True
        stopword_count = sum(1 for w in text.split() if w.lower() in STOPWORDS)
        if stopword_count > MAX_STOPWORD:
            return True
        if info.get("corrections", 0) > 2:
            return True
        if len(info.get("removed_phrases", [])) > 0:
            return True
        return False

    def paraphrase_llm(self, text: str) -> str:
        # Sử dụng BARTpho với prefix 'paraphrase: '
        prompt = f"paraphrase: {text}"
        result = self.paraphrase_pipe(prompt, max_length=128, do_sample=False)
        if isinstance(result, list) and len(result) > 0 and 'generated_text' in result[0]:
            return str(result[0]['generated_text']).strip()
        return text

    def rewrite_with_context(self, text: str, conversation_context: Optional[str] = None) -> str:
        """
        Rewrite câu hỏi với context từ cuộc hội thoại
        
        Args:
            text: Câu hỏi gốc
            conversation_context: Context từ cuộc hội thoại (optional)
            
        Returns:
            str: Câu hỏi đã được rewrite
        """
        logger.info(f"[QueryRewriter] Câu hỏi gốc: {text}")
        if conversation_context:
            logger.info(f"[QueryRewriter] Có context: {len(conversation_context)} chars")
        
        t0 = time.time()
        
        # Nếu có context, tạo prompt kết hợp
        if conversation_context:
            combined_text = self._combine_with_context(text, conversation_context)
            logger.info(f"[QueryRewriter] Kết hợp với context: {combined_text}")
        else:
            combined_text = text
        
        # Rule-based cleaning
        cleaned, info = self.rule_based_clean(combined_text)
        t1 = time.time()
        logger.info(f"[QueryRewriter] Sau rule-based: {cleaned}")
        logger.info(f"[QueryRewriter] Cụm từ bị loại bỏ: {info.get('removed_phrases', [])}")
        logger.info(f"[QueryRewriter] Thời gian rule-based: {t1-t0:.4f}s")
        
        # Kiểm tra có cần paraphrase không
        if self.need_paraphrase(cleaned, info):
            logger.info(f"[QueryRewriter] Sử dụng LLM paraphrase!")
            t2 = time.time()
            try:
                rewritten = self.paraphrase_llm(cleaned)
                t3 = time.time()
                logger.info(f"[QueryRewriter] Sau paraphrase: {rewritten}")
                logger.info(f"[QueryRewriter] Thời gian paraphrase LLM: {t3-t2:.4f}s")
                
                # Log để debug
                self._log_rewrite_comparison(text, rewritten, conversation_context)
                
                return rewritten
            except Exception as e:
                logger.error(f"[QueryRewriter] LLM paraphrase failed: {e}")
                return cleaned
        
        logger.info(f"[QueryRewriter] Không cần paraphrase LLM.")
        
        # Log để debug
        self._log_rewrite_comparison(text, cleaned, conversation_context)
        
        return cleaned

    def _combine_with_context(self, question: str, context: str) -> str:
        """
        Kết hợp câu hỏi với context để tạo input cho rewriting
        """
        # Trích xuất các từ khóa quan trọng từ context
        context_keywords = self._extract_context_keywords(context)
        
        if context_keywords:
            # Thêm context keywords vào câu hỏi
            enhanced_question = f"{question} [Context: {', '.join(context_keywords)}]"
            return enhanced_question
        
        return question

    def _extract_context_keywords(self, context: str) -> List[str]:
        """
        Trích xuất keywords quan trọng từ context
        """
        # Tách context thành các phần
        lines = context.split('\n')
        keywords = []
        
        for line in lines:
            if ':' in line and not line.startswith('['):
                # Lấy phần nội dung sau dấu :
                content = line.split(':', 1)[1].strip()
                if content:
                    # Trích xuất keywords từ content
                    words = re.findall(r'\b\w+\b', content.lower())
                    # Lọc stopwords và từ ngắn
                    filtered_words = [w for w in words if len(w) > 3 and w not in STOPWORDS]
                    keywords.extend(filtered_words[:3])  # Lấy tối đa 3 từ mỗi dòng
        
        # Loại bỏ duplicates và trả về top keywords
        unique_keywords = list(set(keywords))
        return unique_keywords[:5]  # Trả về tối đa 5 keywords

    def _log_rewrite_comparison(self, original: str, rewritten: str, context: Optional[str] = None):
        """Log so sánh câu gốc và câu đã rewrite để debug"""
        logger.info("=== QUERY REWRITE COMPARISON ===")
        logger.info(f"Original: {original}")
        logger.info(f"Rewritten: {rewritten}")
        if context:
            logger.info(f"Context used: {len(context)} chars")
        
        # Tính độ lệch ý nghĩa đơn giản
        original_words = set(re.findall(r'\b\w+\b', original.lower()))
        rewritten_words = set(re.findall(r'\b\w+\b', rewritten.lower()))
        
        common_words = original_words.intersection(rewritten_words)
        total_words = original_words.union(rewritten_words)
        
        if total_words:
            similarity = len(common_words) / len(total_words)
            logger.info(f"Similarity: {similarity:.2f} ({len(common_words)}/{len(total_words)} words)")

    def rewrite(self, text: str) -> str:
        """
        Legacy method - giữ lại để tương thích
        """
        return self.rewrite_with_context(text) 