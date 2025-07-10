import os
import sys
import logging
import asyncio
from typing import Dict, List, Optional, Union, Any, Generator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AWS Bedrock client
from aws_bedrock import ModelClient, ClaudeConfig, LlamaConfig, Message, MessageContent, ClaudeHandler, LlamaHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS Bedrock client
try:
    bedrock_client = ModelClient()
    logger.info("AWS Bedrock client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AWS Bedrock client: {e}")
    bedrock_client = None

def call_llm_stream(prompt, model="claude", max_tokens=2000, temperature=0.3):
    """
    Stream response from AWS Bedrock
    """
    if not bedrock_client:
        yield "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
        return
    
    try:
        # Create configuration based on model type
        if model.lower() == "claude":
            config = ClaudeConfig(
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            config = LlamaConfig(
                model_id="us.meta.llama4-scout-17b-instruct-v1:0",
                max_gen_len=max_tokens,
                temperature=temperature
            )
        
        # Create message
        message = bedrock_client.create_message("user", prompt)
        logger.info(f"[call_llm_stream] Calling Bedrock model: {config.model_id}, prompt[:100]: {prompt[:100]}")
        import time
        t0 = time.time()
        # Generate response
        response = bedrock_client.generate_message([message], config_overrides=config)
        logger.info(f"[call_llm_stream] Raw response from Bedrock: {repr(response)[:1000]}")
        t1 = time.time()
        logger.info(f"[call_llm_stream] Received response from Bedrock in {t1-t0:.2f}s")
        
        # Extract text using the correct handler
        if model.lower() == "claude":
            handler = ClaudeHandler(config)  # type: ignore
        else:
            handler = LlamaHandler(config)  # type: ignore
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_stream] response_text length: {len(response_text)}, preview: {response_text[:200]}")
        # Simulate streaming by yielding chunks
        chunk_size = 100
        if not response_text:
            logger.error("[call_llm_stream] response_text is empty!")
            yield "Xin lỗi, không có dữ liệu trả về từ LLM."
            return
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            logger.info(f"[call_llm_stream] Yield chunk: {repr(chunk)}")
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in call_llm_stream: {e}")
        yield f"Xin lỗi, có lỗi xảy ra: {str(e)}"

def call_llm_full(prompt, model="claude", max_tokens=2000, temperature=0.3):
    """
    Get full response from AWS Bedrock
    """
    if not bedrock_client:
        return "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
    
    try:
        # Create configuration based on model type
        if model.lower() == "claude":
            config = ClaudeConfig(
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            config = LlamaConfig(
                model_id="us.meta.llama4-scout-17b-instruct-v1:0",
                max_gen_len=max_tokens,
                temperature=temperature
            )
        # Create message
        message = bedrock_client.create_message("user", prompt)
        logger.info(f"[call_llm_full] Calling Bedrock model: {config.model_id}, prompt[:100]: {prompt[:100]}")
        import time
        t0 = time.time()
        # Generate response
        response = bedrock_client.generate_message([message], config_overrides=config)
        logger.info(f"[call_llm_full] Raw response from Bedrock: {repr(response)[:1000]}")
        t1 = time.time()
        logger.info(f"[call_llm_full] Received response from Bedrock in {t1-t0:.2f}s")
        
        # Extract and return text using the correct handler
        if model.lower() == "claude":
            handler = ClaudeHandler(config)  # type: ignore
        else:
            handler = LlamaHandler(config)  # type: ignore
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_full] Generated response with {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in call_llm_full: {e}")
        return f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"

def call_llm_with_system_prompt(prompt, system_prompt, model="claude", max_tokens=2000, temperature=0.3):
    """
    Call LLM with system prompt
    """
    if not bedrock_client:
        return "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
    
    try:
        # Create configuration based on model type
        if model.lower() == "claude":
            config = ClaudeConfig(
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            config = LlamaConfig(
                model_id="us.meta.llama4-scout-17b-instruct-v1:0",
                max_gen_len=max_tokens,
                temperature=temperature
            )
        # Create message
        message = bedrock_client.create_message("user", prompt)
        logger.info(f"[call_llm_with_system_prompt] Calling Bedrock model: {config.model_id}, prompt[:100]: {prompt[:100]}")
        import time
        t0 = time.time()
        # Generate response with system prompt
        response = bedrock_client.generate_message([message], system_prompt=system_prompt, config_overrides=config)
        t1 = time.time()
        logger.info(f"[call_llm_with_system_prompt] Received response from Bedrock in {t1-t0:.2f}s")
        
        # Extract and return text using the correct handler
        if model.lower() == "claude":
            handler = ClaudeHandler(config)  # type: ignore
        else:
            handler = LlamaHandler(config)  # type: ignore
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_with_system_prompt] Generated response with {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in call_llm_with_system_prompt: {e}")
        return f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"

def call_llm_conversation(messages, system_prompt=None, model="claude", max_tokens=2000, temperature=0.3):
    """
    Call LLM with conversation history
    """
    if not bedrock_client:
        return "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
    
    try:
        # Create configuration based on model type
        if model.lower() == "claude":
            config = ClaudeConfig(
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            config = LlamaConfig(
                model_id="us.meta.llama4-scout-17b-instruct-v1:0",
                max_gen_len=max_tokens,
                temperature=temperature
            )
        # Convert messages to AWS Bedrock format
        bedrock_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                bedrock_messages.append(bedrock_client.create_message(role, content))
            else:
                bedrock_messages.append(bedrock_client.create_message("user", str(msg)))
        logger.info(f"[call_llm_conversation] Calling Bedrock model: {config.model_id}, first message[:100]: {messages[0] if messages else ''}")
        import time
        t0 = time.time()
        # Generate response
        response = bedrock_client.generate_message(bedrock_messages, system_prompt=system_prompt, config_overrides=config)
        t1 = time.time()
        logger.info(f"[call_llm_conversation] Received response from Bedrock in {t1-t0:.2f}s")
        
        # Extract and return text using the correct handler
        if model.lower() == "claude":
            handler = ClaudeHandler(config)  # type: ignore
        else:
            handler = LlamaHandler(config)  # type: ignore
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_conversation] Generated response with {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in call_llm_conversation: {e}")
        return f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}" 