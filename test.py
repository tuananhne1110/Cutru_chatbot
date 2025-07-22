from qdrant_client import QdrantClient

# Kết nối tới Qdrant
qdrant_client = QdrantClient(host="localhost", port=6333)

# ID của Điều 23 (bạn cần xác định đúng id này)
dieu_23_id = "68/2020/qh14_chương_iv_d23"

# Lấy tất cả chunk có id = dieu_23_id (điều) hoặc parent_id = dieu_23_id (khoản, điểm, ...)
filter_all = {
    "should": [
        {"key": "id", "match": {"value": dieu_23_id}},
        {"key": "parent_id", "match": {"value": dieu_23_id}}
    ]
}

results, _ = qdrant_client.scroll(
    collection_name="legal_chunks",
    scroll_filter=filter_all,
    limit=50,
    with_payload=True,
    with_vectors=False
)

for point in results:
    print("==== CHUNK ====")
    for k, v in point.payload.items():
        print(f"{k}: {v}")
    print()