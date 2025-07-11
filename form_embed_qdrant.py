import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
import os
import pickle
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app_config import embedding_model

# 1. Load data from both JSON files
json_files = [
    'chunking/output_json/form_chunks.json',
    'chunking/output_json/all_laws.json',
    'chunking/output_json/term_chunks.json',
    'chunking/output_json/procedure_chunks.json',
    'chunking/output_json/template_chunks.json'  # Thêm file template
]

form_chunks = []
law_chunks = []
term_chunks = []
procedure_chunks = []
template_chunks = []  # Thêm biến này

for json_file in json_files:
    try:
        with open(json_file, encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks from {json_file}")
        
        # Separate chunks by category
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
# 2. Sử dụng model embedding từ app_config
model = embedding_model

# 3. Helper function để tạo collection với payload schema
def create_collection_with_schema(client, collection_name, vector_size, schema_type="form"):
    """Tạo collection với payload schema tương ứng"""
    try:
        client.get_collection(collection_name)
        print(f"Using existing collection: {collection_name}")
        return
    except:
        pass
    
    # Define payload schema based on type
    if schema_type == "form":
        payload_schema = {
            "text": PayloadSchemaType.TEXT,
            "form_code": PayloadSchemaType.KEYWORD,
            "form_name": PayloadSchemaType.TEXT,
            "field_no": PayloadSchemaType.KEYWORD,
            "field_name": PayloadSchemaType.TEXT,
            "chunk_type": PayloadSchemaType.KEYWORD,
            "content": PayloadSchemaType.TEXT,
            "note": PayloadSchemaType.TEXT
        }
    elif schema_type == "law":
        payload_schema = {
            "text": PayloadSchemaType.TEXT,
            "law_code": PayloadSchemaType.KEYWORD,
            "law_name": PayloadSchemaType.TEXT,
            "promulgator": PayloadSchemaType.KEYWORD,
            "promulgation_date": PayloadSchemaType.DATETIME,
            "effective_date": PayloadSchemaType.DATETIME,
            "law_type": PayloadSchemaType.KEYWORD,
            "article": PayloadSchemaType.KEYWORD,
            "chapter": PayloadSchemaType.KEYWORD,
            "clause": PayloadSchemaType.KEYWORD,
            "point": PayloadSchemaType.KEYWORD,
            "content": PayloadSchemaType.TEXT
        }
    elif schema_type == "term":
        payload_schema = {
            "text": PayloadSchemaType.TEXT,
            "term": PayloadSchemaType.KEYWORD,
            "definition": PayloadSchemaType.TEXT,
            "content": PayloadSchemaType.TEXT,
            "category": PayloadSchemaType.KEYWORD,
            "source": PayloadSchemaType.KEYWORD,
            "article": PayloadSchemaType.KEYWORD,
            "synonyms": PayloadSchemaType.TEXT,
            "related_terms": PayloadSchemaType.TEXT,
            "examples": PayloadSchemaType.TEXT
        }
    elif schema_type == "procedure":
        payload_schema = {
            "text": PayloadSchemaType.TEXT,
            "procedure_code": PayloadSchemaType.KEYWORD,
            "decision_number": PayloadSchemaType.KEYWORD,
            "procedure_name": PayloadSchemaType.TEXT,
            "implementation_level": PayloadSchemaType.KEYWORD,
            "procedure_type": PayloadSchemaType.KEYWORD,
            "field": PayloadSchemaType.KEYWORD,
            "implementation_subject": PayloadSchemaType.TEXT,
            "implementing_agency": PayloadSchemaType.KEYWORD,
            "competent_authority": PayloadSchemaType.KEYWORD,
            "application_receiving_address": PayloadSchemaType.TEXT,
            "authorized_agency": PayloadSchemaType.KEYWORD,
            "coordinating_agency": PayloadSchemaType.KEYWORD,
            "implementation_result": PayloadSchemaType.TEXT,
            "requirements": PayloadSchemaType.TEXT,
            "keywords": PayloadSchemaType.TEXT,
            "content_type": PayloadSchemaType.KEYWORD,
            "source_section": PayloadSchemaType.KEYWORD,
            "table_title": PayloadSchemaType.TEXT,
            "table_index": PayloadSchemaType.KEYWORD,
            "row_index": PayloadSchemaType.KEYWORD,
            "column_name": PayloadSchemaType.KEYWORD,
            "chunk_index": PayloadSchemaType.INTEGER,
            "total_chunks": PayloadSchemaType.INTEGER,
            "content": PayloadSchemaType.TEXT
        }
    elif schema_type == "template":
        payload_schema = {
            "code": PayloadSchemaType.KEYWORD,
            "name": PayloadSchemaType.TEXT,
            "description": PayloadSchemaType.TEXT,
            "file_url": PayloadSchemaType.TEXT,
            "procedures": PayloadSchemaType.TEXT,
            "category": PayloadSchemaType.KEYWORD
        }
    else:
        payload_schema = {}
    
    # Create collection first
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE
        )
    )
    print(f"Created new collection: {collection_name}")
    
    # Create payload indexes for better search performance
    try:
        for field_name, field_type in payload_schema.items():
            if field_type in [PayloadSchemaType.KEYWORD, PayloadSchemaType.INTEGER, PayloadSchemaType.DATETIME]:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
        print(f"Created payload indexes for {collection_name}")
    except Exception as e:
        print(f"Warning: Could not create all payload indexes for {collection_name}: {e}")

# 4. Chuẩn bị text cho embedding
def prepare_text_for_embedding(chunk):
    """
    Prepare text for embedding by combining relevant fields
    """
    parts = []
    
    # Add form information if exists
    if 'form_name' in chunk:
        parts.append(f"Form: {chunk.get('form_name', '')}")
    
    # Add procedure information if exists
    if 'procedure_name' in chunk:
        parts.append(f"Procedure: {chunk.get('procedure_name', '')}")
        if chunk.get('procedure_code'):
            parts.append(f"Code: {chunk.get('procedure_code')}")
        if chunk.get('implementation_level'):
            parts.append(f"Level: {chunk.get('implementation_level')}")
        if chunk.get('field'):
            parts.append(f"Field: {chunk.get('field')}")
    
    # Add term information if exists
    if 'term' in chunk:
        parts.append(f"Term: {chunk.get('term', '')}")
        if chunk.get('definition'):
            parts.append(f"Definition: {chunk.get('definition')}")
    
    # Add field information for forms
    if chunk.get("field_no"):
        parts.append(f"Field {chunk.get('field_no')}: {chunk.get('field_name', '')}")
    elif chunk.get("field_name"):
        parts.append(f"Field: {chunk.get('field_name', '')}")
    
    # Add content
    if chunk.get("content"):
        parts.append(f"Content: {chunk.get('content')}")
    
    # Add note if exists
    if chunk.get("note"):
        parts.append(f"Note: {chunk.get('note')}")
    
    # Add requirements for procedures
    if chunk.get("requirements"):
        parts.append(f"Requirements: {chunk.get('requirements')}")
    
    # Add implementation result for procedures
    if chunk.get("implementation_result"):
        parts.append(f"Result: {chunk.get('implementation_result')}")
    
    # Add template information if exists
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
    
    return " | ".join(parts)

# 4. Kết nối QDrant
# Thử load client từ file cũ trước
client = None
try:
    with open("qdrant_client.pkl", "rb") as f:
        client = pickle.load(f)
    print("Loaded existing Qdrant client")
except FileNotFoundError:
    print("No existing Qdrant client found, creating new one")
    client = QdrantClient(":memory:")  # In-memory cho demo
    # Hoặc lưu vào file: client = QdrantClient(path="./qdrant_db")

# 5. Process form chunks
if form_chunks:
    print("\n" + "="*50)
    print("PROCESSING FORM CHUNKS")
    print("="*50)
    
    form_texts = [prepare_text_for_embedding(chunk) for chunk in form_chunks]
    form_embeddings = model.encode(form_texts, show_progress_bar=True, batch_size=32)
    
    # Clean metadata for form chunks
    form_metadatas = []
    for chunk in form_chunks:
        cleaned = {}
        for k, v in chunk.items():
            if k != 'content':
                if v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
        form_metadatas.append(cleaned)
    
    # Create form_chunks collection with payload schema
    collection_name = "form_chunks"
    vector_size = len(form_embeddings[0])
    create_collection_with_schema(client, collection_name, vector_size, "form")
    
    # Add form data to QDrant
    print(f"Adding {len(form_chunks)} form documents to QDrant...")
    
    try:
        current_count = client.count(collection_name=collection_name).count
        start_id = current_count
        print(f"Starting from ID: {start_id}")
    except:
        start_id = 0
        print("Starting from ID: 0")
    
    form_points = []
    for i, (text, embedding, metadata) in enumerate(zip(form_texts, form_embeddings, form_metadatas)):
        point = PointStruct(
            id=start_id + i,
            vector=embedding.tolist(),
            payload={
                "text": text,
                **metadata
            }
        )
        form_points.append(point)
    
    # Add form points in batches
    batch_size = 100
    for i in range(0, len(form_points), batch_size):
        batch = form_points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"Added form batch {i//batch_size + 1}/{(len(form_points) + batch_size - 1)//batch_size}")
    
    print(f"Form collection total points: {client.count(collection_name=collection_name).count}")

# 6. Process law chunks
if law_chunks:
    print("\n" + "="*50)
    print("PROCESSING LAW CHUNKS")
    print("="*50)
    
    law_texts = [prepare_text_for_embedding(chunk) for chunk in law_chunks]
    law_embeddings = model.encode(law_texts, show_progress_bar=True, batch_size=32)
    
    # Clean metadata for law chunks
    law_metadatas = []
    for chunk in law_chunks:
        cleaned = {}
        for k, v in chunk.items():
            if k != 'content':
                if v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
        law_metadatas.append(cleaned)
    
    # Create legal_chunks collection with payload schema
    collection_name = "legal_chunks"
    vector_size = len(law_embeddings[0])
    create_collection_with_schema(client, collection_name, vector_size, "law")
    
    # Add law data to QDrant
    print(f"Adding {len(law_chunks)} law documents to QDrant...")
    
    try:
        current_count = client.count(collection_name=collection_name).count
        start_id = current_count
        print(f"Starting from ID: {start_id}")
    except:
        start_id = 0
        print("Starting from ID: 0")
    
    law_points = []
    for i, (text, embedding, metadata) in enumerate(zip(law_texts, law_embeddings, law_metadatas)):
        point = PointStruct(
            id=start_id + i,
            vector=embedding.tolist(),
            payload={
                "text": text,
                **metadata
            }
        )
        law_points.append(point)
    
    # Add law points in batches
    batch_size = 100
    for i in range(0, len(law_points), batch_size):
        batch = law_points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"Added law batch {i//batch_size + 1}/{(len(law_points) + batch_size - 1)//batch_size}")
    
    print(f"Law collection total points: {client.count(collection_name=collection_name).count}")

# 7. Process term chunks
if term_chunks:
    print("\n" + "="*50)
    print("PROCESSING TERM CHUNKS")
    print("="*50)
    
    term_texts = [prepare_text_for_embedding(chunk) for chunk in term_chunks]
    term_embeddings = model.encode(term_texts, show_progress_bar=True, batch_size=32)
    
    # Clean metadata for term chunks
    term_metadatas = []
    for chunk in term_chunks:
        cleaned = {}
        for k, v in chunk.items():
            if k != 'content':
                if v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
        term_metadatas.append(cleaned)
    
    # Create term_chunks collection with payload schema
    collection_name = "term_chunks"
    vector_size = len(term_embeddings[0])
    create_collection_with_schema(client, collection_name, vector_size, "term")
    
    # Add term data to QDrant
    print(f"Adding {len(term_chunks)} term documents to QDrant...")
    
    try:
        current_count = client.count(collection_name=collection_name).count
        start_id = current_count
        print(f"Starting from ID: {start_id}")
    except:
        start_id = 0
        print("Starting from ID: 0")
    
    term_points = []
    for i, (text, embedding, metadata) in enumerate(zip(term_texts, term_embeddings, term_metadatas)):
        point = PointStruct(
            id=start_id + i,
            vector=embedding.tolist(),
            payload={
                "text": text,
                **metadata
            }
        )
        term_points.append(point)
    
    # Add term points in batches
    batch_size = 100
    for i in range(0, len(term_points), batch_size):
        batch = term_points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"Added term batch {i//batch_size + 1}/{(len(term_points) + batch_size - 1)//batch_size}")
    
    print(f"Term collection total points: {client.count(collection_name=collection_name).count}")

# 8. Process procedure chunks
if procedure_chunks:
    print("\n" + "="*50)
    print("PROCESSING PROCEDURE CHUNKS")
    print("="*50)
    
    procedure_texts = [prepare_text_for_embedding(chunk) for chunk in procedure_chunks]
    procedure_embeddings = model.encode(procedure_texts, show_progress_bar=True, batch_size=32)
    
    # Clean metadata for procedure chunks
    procedure_metadatas = []
    for chunk in procedure_chunks:
        cleaned = {}
        for k, v in chunk.items():
            if k != 'content':
                if v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
        procedure_metadatas.append(cleaned)
    
    # Create procedure_chunks collection with payload schema
    collection_name = "procedure_chunks"
    vector_size = len(procedure_embeddings[0])
    create_collection_with_schema(client, collection_name, vector_size, "procedure")
    
    # Add procedure data to QDrant
    print(f"Adding {len(procedure_chunks)} procedure documents to QDrant...")
    
    try:
        current_count = client.count(collection_name=collection_name).count
        start_id = current_count
        print(f"Starting from ID: {start_id}")
    except:
        start_id = 0
        print("Starting from ID: 0")
    
    procedure_points = []
    for i, (text, embedding, metadata) in enumerate(zip(procedure_texts, procedure_embeddings, procedure_metadatas)):
        point = PointStruct(
            id=start_id + i,
            vector=embedding.tolist(),
            payload={
                "text": text,
                **metadata
            }
        )
        procedure_points.append(point)
    
    # Add procedure points in batches
    batch_size = 100
    for i in range(0, len(procedure_points), batch_size):
        batch = procedure_points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"Added procedure batch {i//batch_size + 1}/{(len(procedure_points) + batch_size - 1)//batch_size}")
    
    print(f"Procedure collection total points: {client.count(collection_name=collection_name).count}")

# 8.5. Process template chunks
if template_chunks:
    print("\n" + "="*50)
    print("PROCESSING TEMPLATE CHUNKS")
    print("="*50)
    
    template_texts = [prepare_text_for_embedding(chunk) for chunk in template_chunks]
    template_embeddings = model.encode(template_texts, show_progress_bar=True, batch_size=32)
    
    # Clean metadata for template chunks
    template_metadatas = []
    for chunk in template_chunks:
        cleaned = {}
        for k, v in chunk.items():
            if k != 'content':
                if v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
        template_metadatas.append(cleaned)
    
    # Create template_chunks collection with payload schema
    collection_name = "template_chunks"
    vector_size = len(template_embeddings[0])
    create_collection_with_schema(client, collection_name, vector_size, "template")
    
    # Add template data to QDrant
    print(f"Adding {len(template_chunks)} template documents to QDrant...")
    
    try:
        current_count = client.count(collection_name=collection_name).count
        start_id = current_count
        print(f"Starting from ID: {start_id}")
    except:
        start_id = 0
        print("Starting from ID: 0")
    
    template_points = []
    for i, (text, embedding, metadata) in enumerate(zip(template_texts, template_embeddings, template_metadatas)):
        point = PointStruct(
            id=start_id + i,
            vector=embedding.tolist(),
            payload={
                "text": text,
                **metadata
            }
        )
        template_points.append(point)
    
    # Add template points in batches
    batch_size = 100
    for i in range(0, len(template_points), batch_size):
        batch = template_points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"Added template batch {i//batch_size + 1}/{(len(template_points) + batch_size - 1)//batch_size}")
    
    print(f"Template collection total points: {client.count(collection_name=collection_name).count}")

# 9. Kiểm tra kết quả
print("\n" + "="*50)
print("COLLECTION SUMMARY")
print("="*50)

collections = ["form_chunks", "legal_chunks", "term_chunks", "procedure_chunks", "template_chunks"]
for collection_name in collections:
    try:
        collection_info = client.get_collection(collection_name)
        count = client.count(collection_name=collection_name).count
        print(f"{collection_name}: {count} points")
    except Exception as e:
        print(f"{collection_name}: Not found - {e}")

print("✅ Đã import thành công vào QDrant!")

# 10. Lưu client để sử dụng sau
with open("qdrant_client.pkl", "wb") as f:
    pickle.dump(client, f)
print("Saved Qdrant client to qdrant_client.pkl")

# 11. Demo search
print("\n" + "="*50)
print("DEMO SEARCH")
print("="*50)

# Test search
test_queries = [
    ("hướng dẫn điền họ tên", "form_chunks"),
    ("số định danh cá nhân", "form_chunks"),
    ("đăng ký thường trú", "legal_chunks"),
    ("thường trú là gì", "term_chunks"),
    ("định nghĩa tạm trú", "term_chunks"),
    ("thủ tục đăng ký tạm trú", "procedure_chunks"),
    ("cách đăng ký tạm trú", "procedure_chunks")
]

for query, collection_name in test_queries:
    print(f"\nSearching for: '{query}' in {collection_name}")
    
    try:
        # Generate embedding for query
        query_embedding = model.encode([query])
        
        # Search
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_embedding[0].tolist(),
            limit=3
        )
        
        for i, result in enumerate(search_result, 1):
            print(f"\nResult {i}:")
            print(f"  Score: {result.score:.4f}")
            
            # Check if payload exists
            if result.payload is None:
                print("  Payload: None")
                continue
                
            if collection_name == "form_chunks":
                print(f"  Form Code: {result.payload.get('form_code', 'N/A')}")
                print(f"  Field Name: {result.payload.get('field_name', 'N/A')}")
            elif collection_name == "term_chunks":
                print(f"  Term: {result.payload.get('term', 'N/A')}")
                print(f"  Definition: {result.payload.get('definition', 'N/A')}")
            elif collection_name == "procedure_chunks":
                print(f"  Procedure: {result.payload.get('procedure_name', 'N/A')}")
                print(f"  Code: {result.payload.get('procedure_code', 'N/A')}")
                print(f"  Level: {result.payload.get('implementation_level', 'N/A')}")
                print(f"  Field: {result.payload.get('field', 'N/A')}")
            elif collection_name == "template_chunks":
                print(f"  Code: {result.payload.get('code', 'N/A')}")
                print(f"  Name: {result.payload.get('name', 'N/A')}")
                print(f"  Description: {result.payload.get('description', 'N/A')}")
                print(f"  Procedures: {result.payload.get('procedures', 'N/A')}")
            else:
                print(f"  Law Name: {result.payload.get('law_name', 'N/A')}")
                print(f"  Article: {result.payload.get('article', 'N/A')}")
            print(f"  Content: {result.payload.get('content', 'N/A')[:100]}...")
    except Exception as e:
        print(f"Error searching {collection_name}: {e}") 