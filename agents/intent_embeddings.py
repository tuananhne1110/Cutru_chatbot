from services.embedding import get_embedding
import threading

# Định nghĩa mô tả cho từng intent
INTENT_DEFINITIONS = {
    "law": {"desc": "Tra cứu luật pháp, quy định, điều khoản, chế tài, quyền và nghĩa vụ."},
    "form": {"desc": "Hướng dẫn điền biểu mẫu, giấy tờ, tờ khai, phiếu, đơn từ."},
    "term": {"desc": "Tra cứu thuật ngữ, định nghĩa, khái niệm, ý nghĩa."},
    "procedure": {"desc": "Thủ tục hành chính, quy trình, hồ sơ, các bước thực hiện."},
    "template": {"desc": "Tìm kiếm, tải về biểu mẫu gốc, file mẫu, template chuẩn."},
    "ambiguous": {"desc": "Câu hỏi không rõ ràng, có thể thuộc nhiều loại intent."},
    "unknown": {"desc": "Không xác định được ý định người dùng."},
}

# Cache embedding intent (thread-safe)
_intent_emb_cache = None
_intent_emb_lock = threading.Lock()

def get_intent_embeddings():
    global _intent_emb_cache
    if _intent_emb_cache is not None:
        return _intent_emb_cache
    with _intent_emb_lock:
        if _intent_emb_cache is not None:
            return _intent_emb_cache
        _intent_emb_cache = {}
        for k, v in INTENT_DEFINITIONS.items():
            _intent_emb_cache[k] = get_embedding(v["desc"])
        return _intent_emb_cache 