import hashlib
import json
import os
import numpy as np
import redis

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)


CACHE_LIMIT =  1000
CHUNK_SIZE = 100
THRESHOLD = 0.85
PARAPHRASE_CACHE_PREFIX = "paraphrase_cache:"
CACHE_KEY = "semantic_prompt_cache"


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def get_cache_key(prompt):
    return "prompt_cache:" + hashlib.sha256(prompt.encode()).hexdigest()

def get_cached_result(prompt):
    key = get_cache_key(prompt)
    result = redis_client.get(key)
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
    redis_client.set(key, value, ex=3600)

def get_semantic_cached_result(query_embedding, threshold=0.85):
    cache = redis_client.get(CACHE_KEY)
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
            return item
    return None

def set_semantic_cached_result(query_embedding, prompt, answer, sources):
    cache = redis_client.get(CACHE_KEY)
    if cache is not None and isinstance(cache, bytes):
        cache = cache.decode('utf-8')
    if cache is not None and not isinstance(cache, str):
        cache = None
    cache_list = json.loads(cache) if cache else []
    cache_list.insert(0, {
        'embedding': query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding,
        'prompt': prompt,
        'answer': answer,
        'sources': sources
    })
    if len(cache_list) > CACHE_LIMIT:
        cache_list = cache_list[:CACHE_LIMIT]
    redis_client.set(CACHE_KEY, json.dumps(cache_list), ex=3600)

def get_paraphrase_cache_key(question):
    return PARAPHRASE_CACHE_PREFIX + hashlib.sha256(question.strip().lower().encode()).hexdigest()

def get_cached_paraphrase(question):
    key = get_paraphrase_cache_key(question)
    result = redis_client.get(key)
    if result and isinstance(result, bytes):
        return result.decode('utf-8')
    return None

def set_cached_paraphrase(question, paraphrase):
    key = get_paraphrase_cache_key(question)
    redis_client.set(key, paraphrase, ex=86400)