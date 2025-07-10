#!/usr/bin/env python3
"""
Test script để kiểm tra AWS Bedrock integration
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm_service import call_llm_full, call_llm_with_system_prompt
from aws_bedrock import ModelClient, ClaudeConfig, LlamaConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bedrock_client():
    """Test AWS Bedrock client initialization"""
    try:
        client = ModelClient()
        logger.info("✅ AWS Bedrock client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize AWS Bedrock client: {e}")
        return False

# def test_claude_model():
#     """Test Claude model"""
#     try:
#         prompt = "Xin chào! Bạn có thể giúp tôi hiểu về luật cư trú Việt Nam không?"
#         response = call_llm_full(prompt, model="claude", max_tokens=500, temperature=0.3)
        
#         # Check if response is a fallback error message
#         if response.startswith("Xin lỗi, có lỗi xảy ra"):
#             logger.error(f"❌ Claude test failed: Got fallback message")
#             logger.error(f"Response: {response}")
#             return False
            
#         logger.info(f"✅ Claude test successful. Response length: {len(response)}")
#         logger.info(f"Response preview: {response[:200]}...")
#         return True
#     except Exception as e:
#         logger.error(f"❌ Claude test failed: {e}")
#         return False

def test_llama_model():
    """Test Llama model"""
    try:
        prompt = "Xin chào! Bạn có thể giúp tôi hiểu về luật cư trú Việt Nam không?"
        response = call_llm_full(prompt, model="llama", max_tokens=500, temperature=0.3)
        
        # Check if response is a fallback error message
        if response.startswith("Xin lỗi, có lỗi xảy ra"):
            logger.error(f"❌ Llama test failed: Got fallback message")
            logger.error(f"Response: {response}")
            return False
            
        logger.info(f"✅ Llama test successful. Response length: {len(response)}")
        logger.info(f"Response preview: {response[:200]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Llama test failed: {e}")
        return False

def test_system_prompt():
    """Test with system prompt"""
    try:
        system_prompt = "Bạn là một trợ lý pháp luật Việt Nam chuyên nghiệp. Hãy trả lời ngắn gọn và chính xác."
        user_prompt = "Thế nào là thường trú?"
        response = call_llm_with_system_prompt(user_prompt, system_prompt, model="claude")
        
        # Check if response is a fallback error message
        if response.startswith("Xin lỗi, có lỗi xảy ra"):
            logger.error(f"❌ System prompt test failed: Got fallback message")
            logger.error(f"Response: {response}")
            return False
            
        logger.info(f"✅ System prompt test successful. Response length: {len(response)}")
        logger.info(f"Response preview: {response[:200]}...")
        return True
    except Exception as e:
        logger.error(f"❌ System prompt test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting AWS Bedrock integration tests...")
    
    # Check environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.info("Please set the following environment variables:")
        for var in missing_vars:
            logger.info(f"  - {var}")
        return False
    
    logger.info("✅ Environment variables configured")
    
    # Run tests
    tests = [
        ("Bedrock Client", test_bedrock_client),
        # ("Claude Model", test_claude_model),
        ("Llama Model", test_llama_model),
        ("System Prompt", test_system_prompt),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} test...")
        if test_func():
            passed += 1
            logger.info(f"✅ {test_name} test passed")
        else:
            logger.error(f"❌ {test_name} test failed")
        
        # Add delay between tests to avoid rate limiting
        if test_name != "Bedrock Client":  # Don't delay after client test
            logger.info("⏳ Waiting 3 seconds to avoid rate limiting...")
            time.sleep(3)
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! AWS Bedrock integration is working correctly.")
        return True
    else:
        logger.error("💥 Some tests failed. Please check the configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 