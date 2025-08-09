import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.aws_bedrock import (
    ClaudeConfig,
    ClaudeHandler,
    LlamaConfig,
    LlamaHandler,
    ModelClient,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    bedrock_client = ModelClient()
    logger.info("AWS Bedrock client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AWS Bedrock client: {e}")
    bedrock_client = None

def call_llm_stream(prompt, model="claude", max_tokens=4000, temperature=0.5):
    """Stream response from AWS Bedrock."""
    if not bedrock_client:
        yield "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
        return
    try:
        if model.lower() == "claude":
            config = ClaudeConfig(
                max_tokens=max_tokens,
                temperature=temperature
            )
            message = bedrock_client.create_message("user", prompt)
            response = bedrock_client.generate_message([message], config_overrides=config)
            logging.info(f"[DEBUG] Raw Bedrock Claude response: {response}")
            handler = ClaudeHandler(config)  
            response_text = handler.extract_response_text(response)
            chunk_size = 100
            if not response_text:
                yield "Xin lỗi, không có dữ liệu trả về từ LLM."
                return
            usage = response.get('usage', {})
            prompt_tokens = usage.get('inputTokens', 0)
            completion_tokens = usage.get('outputTokens', 0)
        else:
            config = LlamaConfig(
                model_id="us.meta.llama4-scout-17b-instruct-v1:0",
                max_gen_len=max_tokens,  
                temperature=temperature  
            )
            message = bedrock_client.create_message("user", prompt)
            response = bedrock_client.generate_message([message], config_overrides=config)
            logging.info(f"[DEBUG] Raw Bedrock Llama response: {response}")
            handler = LlamaHandler(config)
            response_text = handler.extract_response_text(response)
            chunk_size = 100
            if not response_text:
                yield "Xin lỗi, không có dữ liệu trả về từ LLM."
                return
            prompt_tokens = response.get('prompt_token_count', 0)
            completion_tokens = response.get('generation_token_count', 0)
        call_llm_stream.last_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        logging.info(f"[LLM USAGE] {model}: input={prompt_tokens}, output={completion_tokens}")
        for i in range(0, len(response_text), chunk_size):
            yield response_text[i:i + chunk_size]
    except Exception as e:
        yield f"Xin lỗi, có lỗi xảy ra: {str(e)}"
        call_llm_stream.last_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
        logging.error(f"[LLM ERROR] {str(e)}")

def call_llm_full(prompt, model="claude", max_tokens=4000, temperature=0.3):
    """Get full response from AWS Bedrock."""
    if not bedrock_client:
        return "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
    
    try:
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
        message = bedrock_client.create_message("user", prompt)
        logger.info(f"[call_llm_full] Calling Bedrock model: {config.model_id}, prompt[:100]: {prompt[:100]}")
        import time
        t0 = time.time()
        response = bedrock_client.generate_message([message], config_overrides=config)
        logger.info(f"[call_llm_full] Raw response from Bedrock: {repr(response)[:1000]}")
        t1 = time.time()
        logger.info(f"[call_llm_full] Received response from Bedrock in {t1-t0:.2f}s")
        
        if model.lower() == "claude":
            handler = ClaudeHandler(config)
        else:
            handler = LlamaHandler(config)
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_full] Generated response with {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in call_llm_full: {e}")
        return f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"

def call_llm_with_system_prompt(prompt, system_prompt, model="claude", max_tokens=2000, temperature=0.3):
    """Call LLM with system prompt."""
    if not bedrock_client:
        return "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
    
    try:
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
        message = bedrock_client.create_message("user", prompt)
        logger.info(f"[call_llm_with_system_prompt] Calling Bedrock model: {config.model_id}, prompt[:100]: {prompt[:100]}")
        import time
        t0 = time.time()
        response = bedrock_client.generate_message([message], system_prompt=system_prompt, config_overrides=config)
        t1 = time.time()
        logger.info(f"[call_llm_with_system_prompt] Received response from Bedrock in {t1-t0:.2f}s")
        
        if model.lower() == "claude":
            handler = ClaudeHandler(config)
        else:
            handler = LlamaHandler(config)
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_with_system_prompt] Generated response with {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in call_llm_with_system_prompt: {e}")
        return f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"

def call_llm_conversation(messages, system_prompt=None, model="claude", max_tokens=2000, temperature=0.3):
    """Call LLM with conversation history."""
    if not bedrock_client:
        return "Xin lỗi, không thể kết nối đến AWS Bedrock. Vui lòng thử lại sau."
    
    try:
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
        response = bedrock_client.generate_message(bedrock_messages, system_prompt=system_prompt, config_overrides=config)
        t1 = time.time()
        logger.info(f"[call_llm_conversation] Received response from Bedrock in {t1-t0:.2f}s")
        
        if model.lower() == "claude":
            handler = ClaudeHandler(config)
        else:
            handler = LlamaHandler(config)
        
        response_text = handler.extract_response_text(response)
        logger.info(f"[call_llm_conversation] Generated response with {len(response_text)} characters")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in call_llm_conversation: {e}")
        return f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}" 