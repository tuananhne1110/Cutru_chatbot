import re
from typing import Tuple
import time

# Nếu muốn dùng pyvi/vspell thì import ở đây (giả sử chưa cài)
# from pyvi import ViTokenizer, ViUtils
# import vspell

from services.llm_service import call_llm_full

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
        # Step-back prompt: yêu cầu LLM không chỉ viết lại mà còn xác định mục tiêu thực sự của truy vấn
        prompt = (
            """Bạn là chuyên gia pháp luật.
            Bước 1: Hãy tóm tắt mục đích và ý định nghiệp vụ chính của người hỏi trong câu sau.
            Bước 2: Viết lại câu hỏi thành truy vấn pháp lý ngắn gọn, rõ ràng, chỉ giữ lại phần nghiệp vụ chính, loại bỏ các từ thừa, cảm thán, câu chào hỏi.
            Chỉ in ra kết quả của Bước 2.\n"""
            f"Câu hỏi gốc: '{text}'"
        )
        rewritten = call_llm_full(prompt, model="deepseek-ai/DeepSeek-V3-0324", max_tokens=128, temperature=0.2)
        return rewritten.strip()

    def rewrite(self, text: str) -> str:
        print(f"[QueryRewriter] Câu hỏi gốc: {text}")
        t0 = time.time()
        cleaned, info = self.rule_based_clean(text)
        t1 = time.time()
        print(f"[QueryRewriter] Sau rule-based: {cleaned}")
        print(f"[QueryRewriter] Cụm từ bị loại bỏ: {info.get('removed_phrases', [])}")
        print(f"[QueryRewriter] Thời gian rule-based: {t1-t0:.4f}s")
        if self.need_paraphrase(cleaned, info):
            print(f"[QueryRewriter] Sử dụng LLM paraphrase!")
            t2 = time.time()
            try:
                rewritten = self.paraphrase_llm(cleaned)
                t3 = time.time()
                print(f"[QueryRewriter] Sau paraphrase: {rewritten}")
                print(f"[QueryRewriter] Thời gian paraphrase LLM: {t3-t2:.4f}s")
                return rewritten
            except Exception as e:
                print(f"[QueryRewriter] LLM paraphrase failed: {e}")
                return cleaned
        print(f"[QueryRewriter] Không cần paraphrase LLM.")
        return cleaned 