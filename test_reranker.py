#!/usr/bin/env python3
"""
Test script cho BGE Reranker
Kiểm tra hiệu quả của reranking với dữ liệu mẫu
"""

import time
import json
from services.reranker_service import BGEReranker

def test_reranker():
    """Test BGE reranker với dữ liệu mẫu"""
    
    # Dữ liệu test mẫu
    test_query = "Thủ tục đăng ký thường trú cần những gì?"
    
    test_documents = [
        {
            "content": "Đăng ký thường trú là thủ tục hành chính quan trọng. Cần chuẩn bị các giấy tờ: CMND/CCCD, sổ hộ khẩu, giấy tờ chứng minh nơi ở hợp pháp.",
            "law_name": "Luật Cư trú",
            "article": "Điều 20",
            "type": "law"
        },
        {
            "content": "Thủ tục đăng ký thường trú được quy định tại Luật Cư trú số 81/2006/QH11. Công dân có quyền đăng ký thường trú tại nơi ở hợp pháp.",
            "law_name": "Luật Cư trú",
            "article": "Điều 19",
            "type": "law"
        },
        {
            "content": "Biểu mẫu đăng ký thường trú số 01/CT. Cần điền đầy đủ thông tin cá nhân, địa chỉ thường trú, lý do đăng ký.",
            "form_name": "Mẫu đăng ký thường trú",
            "form_code": "01/CT",
            "type": "form"
        },
        {
            "content": "Thường trú là nơi công dân sinh sống thường xuyên, ổn định, không có thời hạn tại một chỗ ở nhất định và đã được đăng ký thường trú.",
            "term": "Thường trú",
            "definition": "Nơi sinh sống ổn định",
            "type": "term"
        },
        {
            "content": "Quy trình đăng ký thường trú: 1) Chuẩn bị hồ sơ, 2) Nộp tại UBND cấp xã, 3) Kiểm tra và xử lý, 4) Cấp sổ hộ khẩu.",
            "procedure_name": "Đăng ký thường trú",
            "procedure_code": "TT001",
            "type": "procedure"
        },
        {
            "content": "Điều kiện đăng ký thường trú: có nơi ở hợp pháp, có đủ giấy tờ theo quy định, không vi phạm pháp luật về cư trú.",
            "law_name": "Luật Cư trú",
            "article": "Điều 21",
            "type": "law"
        },
        {
            "content": "Thời gian xử lý đăng ký thường trú: 15 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ.",
            "procedure_name": "Thời gian xử lý",
            "procedure_code": "TT002",
            "type": "procedure"
        },
        {
            "content": "Lệ phí đăng ký thường trú: 50.000 đồng/lần đăng ký theo quy định hiện hành.",
            "procedure_name": "Lệ phí",
            "procedure_code": "TT003",
            "type": "procedure"
        }
    ]
    
    print("🧪 Testing BGE Reranker...")
    print(f"Query: {test_query}")
    print(f"Number of documents: {len(test_documents)}")
    print("-" * 50)
    
    # Khởi tạo reranker
    try:
        reranker = BGEReranker()
        print("✅ BGE Reranker initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize BGE Reranker: {e}")
        return
    
    # Test reranking
    try:
        start_time = time.time()
        
        reranked_docs = reranker.rerank(
            query=test_query,
            documents=test_documents,
            top_k=5,
            batch_size=4
        )
        
        rerank_time = time.time() - start_time
        
        print(f"\n⏱️ Reranking completed in {rerank_time:.3f}s")
        print(f"📊 Results (top 5):")
        print("-" * 50)
        
        for i, doc in enumerate(reranked_docs):
            print(f"\n{i+1}. Score: {doc.get('rerank_score', 0):.4f}")
            print(f"   Type: {doc.get('type', 'unknown')}")
            print(f"   Content: {doc.get('content', '')[:100]}...")
            
            # Hiển thị metadata
            if doc.get('law_name'):
                print(f"   Law: {doc['law_name']} - {doc.get('article', '')}")
            elif doc.get('form_name'):
                print(f"   Form: {doc['form_name']} ({doc.get('form_code', '')})")
            elif doc.get('term'):
                print(f"   Term: {doc['term']}")
            elif doc.get('procedure_name'):
                print(f"   Procedure: {doc['procedure_name']} ({doc.get('procedure_code', '')})")
        
        # Thống kê reranking
        stats = reranker.get_rerank_stats(reranked_docs)
        print(f"\n📈 Reranking Statistics:")
        print(f"   Total documents: {stats.get('total_documents', 0)}")
        print(f"   Improved documents: {stats.get('improved_documents', 0)}")
        print(f"   Improvement rate: {stats.get('improvement_rate', 0):.2%}")
        print(f"   Average improvement: {stats.get('average_improvement', 0):.2f} positions")
        print(f"   Score range: {stats.get('min_score', 0):.4f} - {stats.get('max_score', 0):.4f}")
        
    except Exception as e:
        print(f"❌ Error during reranking: {e}")

def test_reranker_performance():
    """Test performance của reranker với nhiều documents"""
    
    # Tạo dữ liệu test lớn hơn
    test_query = "Quy định về đăng ký tạm trú"
    
    # Tạo documents mẫu
    test_documents = []
    for i in range(50):
        doc = {
            "content": f"Document {i+1}: Thông tin về đăng ký tạm trú và các quy định liên quan. Đây là nội dung mẫu để test reranking performance.",
            "type": "law" if i % 3 == 0 else "procedure" if i % 3 == 1 else "form",
            "id": i
        }
        test_documents.append(doc)
    
    print(f"\n🚀 Performance Test with {len(test_documents)} documents...")
    
    try:
        reranker = BGEReranker()
        
        # Test với batch sizes khác nhau
        batch_sizes = [8, 16, 32]
        
        for batch_size in batch_sizes:
            start_time = time.time()
            
            reranked_docs = reranker.rerank(
                query=test_query,
                documents=test_documents,
                top_k=10,
                batch_size=batch_size
            )
            
            total_time = time.time() - start_time
            
            print(f"   Batch size {batch_size}: {total_time:.3f}s")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")

if __name__ == "__main__":
    print("🎯 BGE Reranker Test Suite")
    print("=" * 50)
    
    # Test cơ bản
    test_reranker()
    
    # Test performance
    test_reranker_performance()
    
    print("\n✅ Test completed!") 