import redis
import hashlib
import json
import numpy as np

r = redis.Redis(host='localhost', port=6379, db=0)
CACHE_KEY = "semantic_prompt_cache"
CACHE_LIMIT = 1000  # Giới hạn số lượng cache
PARAPHRASE_CACHE_PREFIX = "paraphrase_cache:"

CACHE_KEY = "semantic_prompt_cache"
CACHE_LIMIT = 1000  # Giới hạn số lượng cache
PARAPHRASE_CACHE_PREFIX = "paraphrase_cache:"

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def get_cache_key(prompt):
    return "prompt_cache:" + hashlib.sha256(prompt.encode()).hexdigest()

def get_cached_result(prompt):
    key = get_cache_key(prompt)
    result = r.get(key)
    if result is None:
        return None
    if isinstance(result, bytes):
        result = result.decode('utf-8')
    if not isinstance(result, str):
        return None
    return json.loads(result)

def set_cached_result(prompt, answer, sources):
    key = get_cache_key(prompt)
    value = json.dumps({'answer': answer, 'sources': sources})
    r.set(key, value, ex=3600)  # Cache 1h 

def get_semantic_cached_result(query_embedding, threshold=0.85):
    cache = r.get(CACHE_KEY)
    if cache is None:
        return None
    if isinstance(cache, bytes):
        cache = cache.decode('utf-8')
    if not isinstance(cache, str):
        return None
    cache_list = json.loads(cache)
    for item in cache_list:
        sim = cosine_similarity(query_embedding, item['embedding'])
        print(f"[Semantic Cache] Similarity: {sim:.4f}")

        if sim >= threshold:
            return item  # Trả về answer, sources, prompt đã cache
    return None

def set_semantic_cached_result(query_embedding, prompt, answer, sources):
    cache = r.get(CACHE_KEY)
    if cache is not None and isinstance(cache, bytes):
        cache = cache.decode('utf-8')
    if cache is not None and not isinstance(cache, str):
        cache = None
    cache_list = json.loads(cache) if cache else []
    # Thêm mới vào đầu, xóa bớt nếu quá giới hạn
    cache_list.insert(0, {
        'embedding': query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding,
        'prompt': prompt,
        'answer': answer,
        'sources': sources
    })
    if len(cache_list) > CACHE_LIMIT:
        cache_list = cache_list[:CACHE_LIMIT]
    r.set(CACHE_KEY, json.dumps(cache_list), ex=3600) 

def get_paraphrase_cache_key(question):
    return PARAPHRASE_CACHE_PREFIX + hashlib.sha256(question.strip().lower().encode()).hexdigest()

def get_cached_paraphrase(question):
    key = get_paraphrase_cache_key(question)
    result = r.get(key)
    if result and isinstance(result, bytes):
        return result.decode('utf-8')
    return None

def set_cached_paraphrase(question, paraphrase):
    key = get_paraphrase_cache_key(question)
    r.set(key, paraphrase, ex=86400)  # Cache 1 ngày 