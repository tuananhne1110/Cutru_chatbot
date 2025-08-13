# Cập nhật test_graph_rag.py để test đầy đủ hơn
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_knowledge_graph_only():
    """Test chỉ Knowledge Graph không cần workflow"""
    print("Testing Knowledge Graph Creation")
    print("=" * 50)
    
    try:
        from services.graph_rag_service import LegalKnowledgeGraph
        
        # Initialize knowledge graph
        kg = LegalKnowledgeGraph()
        
        # Test với một sample data nhỏ
        sample_law = {
            "id": "test_001",
            "law_name": "Luật Cư trú 2020",
            "law_code": "47/2020/QH14",
            "promulgation_date": "13 tháng 11 năm 2020",
            "promulgator": "Quốc hội",
            "law_type": "Luật",
            "chapter": "Chương I",
            "chapter_content": "NHỮNG QUY ĐỊNH CHUNG",
            "content": "Điều 1. Phạm vi điều chỉnh. Luật này quy định về đăng ký cư trú, quản lý cư trú và trách nhiệm của cơ quan, tổ chức, cá nhân trong việc thực hiện các quy định về cư trú.",
            "category": "law"
        }
        
        # Extract entities
        entities = kg.extract_legal_entities(sample_law)
        print(f"Extracted {len(entities)} entities:")
        for entity in entities:
            print(f"  - {entity.type}: {entity.name}")
        
        # Extract relationships
        relationships = kg.extract_relationships(entities, sample_law)
        print(f"\nExtracted {len(relationships)} relationships:")
        for rel in relationships:
            print(f"  - {rel.source} --{rel.relation_type}--> {rel.target}")
        
        # Test semantic search
        test_query = "đăng ký cư trú"
        print(f"\nTesting semantic search for: '{test_query}'")
        
        # Mock some entity embeddings for test
        kg.entity_embeddings = {
            entity.id: kg.embedding_model.encode(f"{entity.name} {entity.properties.get('content', '')}")
            for entity in entities
        }
        
        similar_entities = kg.semantic_search_entities(test_query, top_k=3)
        print(f"Found {len(similar_entities)} similar entities:")
        for entity_id, score in similar_entities:
            entity = next((e for e in entities if e.id == entity_id), None)
            if entity:
                print(f"  - {entity.name} (score: {score:.3f})")
        
        print("\n✅ Knowledge Graph test completed successfully!")
        
    except Exception as e:
        print(f"❌ Knowledge Graph test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_full_workflow():
    """Test full Graph RAG workflow"""
    print("\nTesting Full Graph RAG Workflow")
    print("=" * 50)
    
    try:
        # Check if all components are available
        from services.graph_rag_init import get_graph_rag_service
        
        service = get_graph_rag_service()
        if not service:
            print("❌ Graph RAG service not initialized")
            return
        
        # Test queries
        test_queries = [
            "Thủ tục đăng ký cư trú",
            "Luật cư trú quy định gì?",
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nTest {i}: {query}")
            print("-" * 40)
            
            try:
                # Test graph context extraction
                graph_context = service.get_graph_context(query)
                print(f"Graph context: {graph_context[:200] if graph_context else 'None'}...")
                
            except Exception as e:
                print(f"Error in query {i}: {e}")
        
        print("\n✅ Full workflow test completed!")
        
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("Graph RAG System Testing")
    print("=" * 60)
    
    # Test 1: Knowledge Graph only
    await test_knowledge_graph_only()
    
    # Test 2: Full workflow (if available)
    await test_full_workflow()

if __name__ == "__main__":
    asyncio.run(main())