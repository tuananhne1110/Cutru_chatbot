from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType
import pickle
import os

# Load QDrant client
client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "qdrant"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)
def create_indexes_for_collection(collection_name, fields_to_index):
    """Tạo payload indexes cho một collection"""
    print(f"\n🔧 Creating indexes for collection: {collection_name}")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for field, schema_type in fields_to_index.items():
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=schema_type,
                wait=True
            )
            print(f"✅ Created index for field: {field}")
            success_count += 1
        except Exception as e:
            print(f"⚠️ Failed to create index for field {field}: {e}")
            error_count += 1
    
    print(f"\n📊 Summary for {collection_name}:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    return success_count, error_count

def main():
    print("🚀 Starting Payload Index Creation for All Collections")
    print("=" * 80)
    
    # 1. Form Chunks Collection
    form_fields = {
        "form_code": PayloadSchemaType.KEYWORD,
        "form_name": PayloadSchemaType.TEXT,
        "field_no": PayloadSchemaType.KEYWORD,
        "field_name": PayloadSchemaType.TEXT,
        "chunk_type": PayloadSchemaType.KEYWORD,
        "content": PayloadSchemaType.TEXT,
        "note": PayloadSchemaType.TEXT,
        "category": PayloadSchemaType.KEYWORD
    }
    
    # 2. Law Chunks Collection
    law_fields = {
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
        "content": PayloadSchemaType.TEXT,
        "category": PayloadSchemaType.KEYWORD
    }
    
    # 3. Term Chunks Collection
    term_fields = {
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
    
    # 4. Procedure Chunks Collection
    procedure_fields = {
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
        "content": PayloadSchemaType.TEXT,
        "category": PayloadSchemaType.KEYWORD
    }
    
    # 5. Template Chunks Collection
    template_fields = {
        "code": PayloadSchemaType.KEYWORD,
        "name": PayloadSchemaType.TEXT,
        "description": PayloadSchemaType.TEXT,
        "file_url": PayloadSchemaType.TEXT,
        "procedures": PayloadSchemaType.TEXT,
        "category": PayloadSchemaType.KEYWORD,
        "content": PayloadSchemaType.TEXT
    }
    
    # Collections configuration
    collections_config = {
        "form_chunks": form_fields,
        "legal_chunks": law_fields,
        "term_chunks": term_fields,
        "procedure_chunks": procedure_fields,
        "template_chunks": template_fields
    }
    
    total_success = 0
    total_errors = 0
    
    # Create indexes for each collection
    for collection_name, fields in collections_config.items():
        try:
            # Check if collection exists
            collection_info = client.get_collection(collection_name)
            print(f"\n📋 Collection '{collection_name}' exists with {collection_info.points_count} points")
            
            success, errors = create_indexes_for_collection(collection_name, fields)
            total_success += success
            total_errors += errors
            
        except Exception as e:
            print(f"❌ Collection '{collection_name}' not found or error: {e}")
            total_errors += 1
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎯 FINAL SUMMARY")
    print("=" * 80)
    print(f"✅ Total successful indexes created: {total_success}")
    print(f"❌ Total errors: {total_errors}")
    
    if total_errors == 0:
        print("🎉 All indexes created successfully!")
    else:
        print("⚠️ Some indexes failed to create. Check the errors above.")
    
    print("\n💡 Benefits of payload indexes:")
    print("   • Faster filtering by metadata fields")
    print("   • Better performance for exact match queries")
    print("   • Optimized range queries for dates and numbers")
    print("   • Improved search capabilities")

if __name__ == "__main__":
    main() 