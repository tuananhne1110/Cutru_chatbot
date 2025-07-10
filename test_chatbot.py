#!/usr/bin/env python3
"""
Test script cho chatbot với AWS Bedrock
"""

import asyncio
import logging
from agents.langgraph_implementation import create_rag_workflow, create_initial_state
from langchain_core.runnables import RunnableConfig
from typing import cast

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_chatbot():
    """Test chatbot với AWS Bedrock"""
    
    # Tạo workflow
    rag_workflow = create_rag_workflow()
    
    # Test questions
    test_questions = [
        "Xin chào, bạn có thể giúp tôi tìm hiểu về thủ tục đăng ký tạm trú không?",
        "Thế nào là thường trú?",
        "Hướng dẫn điền mẫu CT01",
        "Điều 20 Luật Cư trú quy định gì?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {question}")
        print(f"{'='*60}")
        
        try:
            # Tạo initial state
            session_id = f"test_session_{i}"
            initial_state = create_initial_state(question, [], session_id)
            
            # Run workflow
            config = cast(RunnableConfig, {"configurable": {"thread_id": session_id}})
            result = await rag_workflow.ainvoke(initial_state, config=config)
            
            # Extract results
            answer = result.get("answer", "Không có câu trả lời")
            sources = result.get("sources", [])
            intent = result.get("intent", "unknown")
            processing_time = result.get("processing_time", {})
            
            print(f"Intent: {intent}")
            print(f"Answer: {answer}")
            print(f"Sources: {len(sources)} sources found")
            print(f"Processing time: {processing_time}")
            
            if sources:
                print("\nTop sources:")
                for j, source in enumerate(sources[:2], 1):
                    print(f"  {j}. {source.get('title', 'N/A')}")
                    print(f"     Content: {source.get('content', 'N/A')[:100]}...")
            
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Error in test {i}: {e}")

def test_llm_direct():
    """Test LLM service trực tiếp"""
    print("\n" + "="*60)
    print("TESTING LLM SERVICE DIRECTLY")
    print("="*60)
    
    try:
        from services.llm_service import call_llm_full
        
        test_prompt = "Xin chào, bạn có thể giúp tôi tìm hiểu về thủ tục đăng ký tạm trú không?"
        
        print(f"Testing prompt: {test_prompt}")
        result = call_llm_full(test_prompt, "llama")
        print(f"Response: {result}")
        
    except Exception as e:
        print(f"Error testing LLM: {e}")

if __name__ == "__main__":
    print("🚀 Testing Chatbot with AWS Bedrock")
    print("="*60)
    
    # Test LLM trực tiếp trước
    test_llm_direct()
    
    # Test chatbot workflow
    print("\n" + "="*60)
    print("TESTING CHATBOT WORKFLOW")
    print("="*60)
    
    asyncio.run(test_chatbot())
    
    print("\n✅ Testing completed!") 