import json
import sys
import os

# Fix import path - Thêm thư mục gốc vào Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from qdrant_client.models import Distance, VectorParams, PointStruct
from config.app_config import embedding_model
from config.app_config import qdrant_client as client

# 1. Đường dẫn các file chunk (từ thư mục gốc)
json_files = [
    'data/chunking/output_json/form_chunks.json',
    'data/chunking/output_json/all_laws_updated.json',
    'data/chunking/output_json/term_chunks.json',
    'data/chunking/output_json/procedure_chunks.json',
    'data/chunking/output_json/template_chunks.json'
]

form_chunks = []
law_chunks = []
term_chunks = []
procedure_chunks = []
template_chunks = []

# Chuyển về thư mục gốc để đọc file
os.chdir(project_root)

for json_file in json_files:
    try:
        with open(json_file, encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks from {json_file}")
        for chunk in chunks:
            if 'form_code' in chunk or 'form_name' in chunk:
                form_chunks.append(chunk)
            elif 'term' in chunk or 'definition' in chunk or 'glossary' in chunk:
                term_chunks.append(chunk)
            elif 'procedure_code' in chunk or 'procedure_name' in chunk or chunk.get('category') == 'procedure':
                procedure_chunks.append(chunk)
            elif 'category' in chunk and chunk.get('category') == 'templates':
                template_chunks.append(chunk)
            else:
                law_chunks.append(chunk)
    except FileNotFoundError:
        print(f"File {json_file} not found, skipping...")
    except Exception as e:
        print(f"Error loading {json_file}: {e}")

print(f"Form chunks: {len(form_chunks)}")
print(f"Law chunks: {len(law_chunks)}")
print(f"Term chunks: {len(term_chunks)}")
print(f"Procedure chunks: {len(procedure_chunks)}")
print(f"Template chunks: {len(template_chunks)}")


# 3. Hàm chuẩn hóa text và metadata về lowercase
def prepare_text_for_embedding(chunk):
    parts = []
    
    # Thêm thông tin law_status và status_description vào embedding
    if chunk.get('law_status'):
        parts.append(f"Law Status: {chunk.get('law_status')}")
    if chunk.get('status_description'):
        parts.append(f"Status Description: {chunk.get('status_description')}")
    if 'form_name' in chunk:
        parts.append(f"Form: {chunk.get('form_name', '')}")
    if 'procedure_name' in chunk:
        parts.append(f"Procedure: {chunk.get('procedure_name', '')}")
        if chunk.get('procedure_code'):
            parts.append(f"Code: {chunk.get('procedure_code')}")
        if chunk.get('implementation_level'):
            parts.append(f"Level: {chunk.get('implementation_level')}")
        if chunk.get('field'):
            parts.append(f"Field: {chunk.get('field')}")
    if 'term' in chunk:
        parts.append(f"Term: {chunk.get('term', '')}")
        if chunk.get('definition'):
            parts.append(f"Definition: {chunk.get('definition')}")
    if chunk.get("field_no"):
        parts.append(f"Field {chunk.get('field_no')}: {chunk.get('field_name', '')}")
    elif chunk.get("field_name"):
        parts.append(f"Field: {chunk.get('field_name', '')}")
    if chunk.get("content"):
        parts.append(f"Content: {chunk.get('content')}")
    if chunk.get("note"):
        parts.append(f"Note: {chunk.get('note')}")
    if chunk.get("requirements"):
        parts.append(f"Requirements: {chunk.get('requirements')}")
    if chunk.get("implementation_result"):
        parts.append(f"Result: {chunk.get('implementation_result')}")
    if 'code' in chunk:
        parts.append(f"Template Code: {chunk.get('code', '')}")
    if 'name' in chunk:
        parts.append(f"Template Name: {chunk.get('name', '')}")
    if chunk.get('description'):
        parts.append(f"Description: {chunk.get('description')}")
    if chunk.get('procedures'):
        parts.append(f"Procedures: {chunk.get('procedures')}")
    if chunk.get('file_url'):
        parts.append(f"File URL: {chunk.get('file_url')}")
    return " | ".join(parts).lower()

def lower_metadata(chunk):
    cleaned = {}
    for k, v in chunk.items():
        if v is None:
            cleaned[k] = ""
        else:
            cleaned[k] = str(v).lower()
    return cleaned

# 4. Hàm tạo collection với schema
def create_collection(client, name, vector_size):
    try:
        client.get_collection(name)
        print(f"Using existing collection: {name}")
    except:
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        print(f"Created new collection: {name}")

# 5. Hàm insert lên Qdrant
def insert_chunks(client, collection_name, chunks, model):
    if not chunks:
        return
    texts = [prepare_text_for_embedding(chunk) for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    metadatas = [lower_metadata(chunk) for chunk in chunks]
    vector_size = len(embeddings[0])
    create_collection(client, collection_name, vector_size)
    print(f"Adding {len(chunks)} documents to {collection_name}...")
    try:
        current_count = client.count(collection_name=collection_name).count
        start_id = current_count
    except:
        start_id = 0
    points = []
    for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
        point = PointStruct(
            id=start_id + i,
            vector=embedding.tolist(),
            payload={
                "content": text,
                **metadata
            }
        )
        points.append(point)
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        print(f"Added batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}")
    print(f"Collection {collection_name} total points: {client.count(collection_name=collection_name).count}")

# 6. Insert từng loại chunk
insert_chunks(client, "form_chunks", form_chunks, embedding_model)
insert_chunks(client, "legal_chunks", law_chunks, embedding_model)
insert_chunks(client, "term_chunks", term_chunks, embedding_model)
insert_chunks(client, "procedure_chunks", procedure_chunks, embedding_model)
insert_chunks(client, "template_chunks", template_chunks, embedding_model)

print("✅ Hoàn thành embedding tất cả chunks!") 