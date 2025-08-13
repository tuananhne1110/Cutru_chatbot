#!/usr/bin/env python3
"""
Script để test LangSmith integration và tạo sample traces.
Chạy script này để kiểm tra xem LangSmith đã được cấu hình đúng chưa.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.app_config import langsmith_cfg, LANGCHAIN_API_KEY
from agents.workflow import rag_workflow
from agents.utils.message_conversion import create_initial_state
from langchain_core.runnables import RunnableConfig
from typing import cast

def check_langsmith_config():
    """Kiểm tra cấu hình LangSmith"""
    print("🔍 Checking LangSmith Configuration...")
    print(f"├── Tracing Enabled: {langsmith_cfg.get('tracing_enabled', False)}")
    print(f"├── Project Name: {langsmith_cfg.get('project_name', 'N/A')}")
    print(f"├── API URL: {langsmith_cfg.get('api_url', 'N/A')}")
    print(f"├── API Key Present: {'✅ Yes' if LANGCHAIN_API_KEY else '❌ No'}")
    print(f"├── Tags: {langsmith_cfg.get('tags', [])}")
    print(f"└── Metadata: {langsmith_cfg.get('metadata', {})}")
    
    # Check environment variables
    print("\n🌍 Environment Variables:")
    print(f"├── LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2', 'Not set')}")
    print(f"├── LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT', 'Not set')}")
    print(f"└── LANGCHAIN_API_KEY: {'Set' if os.getenv('LANGCHAIN_API_KEY') else 'Not set'}")
    
    if not LANGCHAIN_API_KEY:
        print("\n⚠️  WARNING: LANGCHAIN_API_KEY not found!")
        print("   Please set your LangSmith API key in .env file")
        return False
    
    return True

async def test_simple_workflow():
    """Test workflow với simple question"""
    print("\n🧪 Testing Simple Workflow...")
    
    question = "Thủ tục đăng ký cư trú cần giấy tờ gì?"
    session_id = f"test-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Create initial state
    initial_state = create_initial_state(question, [], session_id)
    
    # Prepare config with LangSmith metadata
    config_dict = {"configurable": {"thread_id": session_id}}
    
    if langsmith_cfg.get("tracing_enabled", False):
        config_dict["tags"] = langsmith_cfg.get("tags", []) + ["test", "demo"]
        config_dict["metadata"] = {
            **langsmith_cfg.get("metadata", {}),
            "session_id": session_id,
            "test_type": "simple_workflow",
            "timestamp": datetime.now().isoformat(),
            "question": question
        }
    
    config = cast(RunnableConfig, config_dict)
    
    try:
        print(f"├── Question: {question}")
        print(f"├── Session ID: {session_id}")
        print("├── Running workflow...")
        
        # Run workflow
        result = await rag_workflow.ainvoke(initial_state, config=config)
        
        print("├── ✅ Workflow completed successfully!")
        print(f"├── Intent: {result.get('intent', 'N/A')}")
        print(f"├── Sources found: {len(result.get('sources', []))}")
        print(f"└── Answer length: {len(result.get('answer', ''))}")
        
        return True
        
    except Exception as e:
        print(f"├── ❌ Error: {str(e)}")
        return False

async def test_multiple_scenarios():
    """Test nhiều scenarios khác nhau"""
    print("\n🔄 Testing Multiple Scenarios...")
    
    test_cases = [
        {
            "question": "Luật cư trú số 81/2020/QH14 quy định gì?",
            "scenario": "law_query",
            "expected_intent": "law"
        },
        {
            "question": "Cách điền biểu mẫu CT01?",
            "scenario": "form_query", 
            "expected_intent": "form"
        },
        {
            "question": "Thường trú là gì?",
            "scenario": "term_query",
            "expected_intent": "term"
        },
        {
            "question": "Chào bạn!",
            "scenario": "general_greeting",
            "expected_intent": "general"
        }
    ]
    
    success_count = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n  Test {i}/4 - {case['scenario']}:")
        session_id = f"test-{case['scenario']}-{datetime.now().strftime('%H%M%S')}"
        
        initial_state = create_initial_state(case["question"], [], session_id)
        
        config_dict = {"configurable": {"thread_id": session_id}}
        
        if langsmith_cfg.get("tracing_enabled", False):
            config_dict["tags"] = langsmith_cfg.get("tags", []) + ["test", case["scenario"]]
            config_dict["metadata"] = {
                **langsmith_cfg.get("metadata", {}),
                "session_id": session_id,
                "test_scenario": case["scenario"],
                "expected_intent": case["expected_intent"],
                "timestamp": datetime.now().isoformat()
            }
        
        config = cast(RunnableConfig, config_dict)
        
        try:
            result = await rag_workflow.ainvoke(initial_state, config=config)
            actual_intent = result.get('intent', 'unknown')
            
            if actual_intent == case["expected_intent"]:
                print(f"    ✅ Intent: {actual_intent} (Expected: {case['expected_intent']})")
                success_count += 1
            else:
                print(f"    ⚠️  Intent: {actual_intent} (Expected: {case['expected_intent']})")
            
            print(f"    📊 Sources: {len(result.get('sources', []))}")
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
    
    print(f"\n📈 Test Results: {success_count}/{len(test_cases)} scenarios passed")
    return success_count == len(test_cases)

def print_dashboard_info():
    """In thông tin về cách truy cập dashboard"""
    print("\n📊 LangSmith Dashboard Access:")
    print("├── URL: https://smith.langchain.com/")
    print(f"├── Project: {langsmith_cfg.get('project_name', 'cutru-chatbot')}")
    print("├── Login with your LangSmith account")
    print("└── You should see traces from the tests above")
    
    print("\n🎯 What to look for in Dashboard:")
    print("├── Workflow visualization showing all nodes")
    print("├── Execution times for each step")
    print("├── Input/output data for debugging")
    print("├── Tags and metadata for filtering")
    print("└── Performance metrics and trends")

async def main():
    """Main test function"""
    print("🚀 LangSmith Integration Test")
    print("=" * 50)
    
    # Check configuration
    if not check_langsmith_config():
        print("\n❌ Configuration check failed!")
        print("Please fix the configuration and try again.")
        return
    
    print("\n✅ Configuration looks good!")
    
    # Test simple workflow
    simple_test_passed = await test_simple_workflow()
    
    if not simple_test_passed:
        print("\n❌ Simple test failed!")
        print("Please check the error messages and fix issues.")
        return
    
    # Test multiple scenarios
    multiple_tests_passed = await test_multiple_scenarios()
    
    # Print dashboard info
    print_dashboard_info()
    
    # Final summary
    print(f"\n{'🎉' if simple_test_passed and multiple_tests_passed else '⚠️'} Test Summary:")
    print(f"├── Simple Workflow: {'✅ Passed' if simple_test_passed else '❌ Failed'}")
    print(f"├── Multiple Scenarios: {'✅ Passed' if multiple_tests_passed else '❌ Failed'}")
    print(f"└── LangSmith Integration: {'✅ Working' if simple_test_passed else '❌ Issues'}")
    
    if simple_test_passed:
        print("\n🎊 LangSmith integration is working!")
        print("Check your dashboard to see the beautiful workflow visualization!")
    else:
        print("\n🔧 Please fix the issues and run the test again.")

if __name__ == "__main__":
    asyncio.run(main())