import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

COLLECTION = "legal_chunks"
PARENT_ID = "68/2020/qh14_chương_iv_d23"

client = QdrantClient(host="localhost", port=6333)

# 1. Tìm chunk điều 23
hits = client.scroll(
    collection_name=COLLECTION,
    scroll_filter={
        "must": [
            {"key": "id", "match": {"value": PARENT_ID}}
        ]
    },
    with_payload=True,
    with_vectors=False,
    limit=10
)[0]
print("=== Chunk ĐIỀU 23 ===")
for h in hits:
    payload = h.payload if hasattr(h, "payload") else h
    print(f"id: {payload.get('id')}, type: {payload.get('type')}, content: {payload.get('content', '')[:80]}")

# 2. Tìm các khoản/điểm con của điều 23
hits = client.scroll(
    collection_name=COLLECTION,
    scroll_filter={
        "must": [
            {"key": "parent_id", "match": {"value": PARENT_ID}}
        ]
    },
    with_payload=True,
    with_vectors=False,
    limit=100
)[0]
print("\n=== Các khoản/điểm con của ĐIỀU 23 ===")
for h in hits:
    payload = h.payload if hasattr(h, "payload") else h
    print(f"id: {payload.get('id')}, parent_id: {payload.get('parent_id')}, type: {payload.get('type')}, content: {payload.get('content', '')[:80]}")

# 3. Nếu không có kết quả, thử tìm các parent_id gần giống (d23, d 23, ...)
hits = client.scroll(
    collection_name=COLLECTION,
    scroll_filter={
        "must": [
            {"key": "parent_id", "match": {"value": "d23"}}
        ]
    },
    with_payload=True,
    with_vectors=False,
    limit=100
)[0]
if hits:
    print("\n=== Các chunk có parent_id chứa 'd23' (fuzzy) ===")
    for h in hits:
        payload = h.payload if hasattr(h, "payload") else h
        print(f"id: {payload.get('id')}, parent_id: {payload.get('parent_id')}, type: {payload.get('type')}, content: {payload.get('content', '')[:80]}")
else:
    print("\nKhông tìm thấy chunk nào có parent_id chứa 'd23' (fuzzy)") 