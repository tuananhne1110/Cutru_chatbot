import redis
import hashlib
import json
import numpy as np
import os
import yaml

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=redis_host, port=redis_port, db=0)

def load_cache_config(yaml_path="config/config.yaml"):
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get("cache", {})
    except Exception:
        return {}

cache_cfg = load_cache_config()
CACHE_LIMIT = cache_cfg.get("cache_limit", 1000)
CHUNK_SIZE = cache_cfg.get("chunk_size", 100)
THRESHOLD = cache_cfg.get("threshold", 0.85)
PARAPHRASE_CACHE_PREFIX = cache_cfg.get("paraphrase_cache_prefix", "paraphrase_cache:")
CACHE_KEY = cache_cfg.get("cache_key", "semantic_prompt_cache")

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