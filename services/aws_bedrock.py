import boto3
import logging
import json
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps
from abc import ABC, abstractmethod
import time
import yaml

class ModelVersion(Enum):
    # Claude Models
    CLAUDE_3_5_SONNET_V1 = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    LLAMA_4_17B_SCOUT = "us.meta.llama4-scout-17b-instruct-v1:0"


class ModelType(Enum):
    CLAUDE = "claude"
    LLAMA = "llama"

@dataclass
class MessageContent:
    """Dataclass cho nội dung tin nhắn"""
    type: str
    text: str

@dataclass
class Message:
    """Dataclass cho một tin nhắn trong cuộc trò chuyện."""
    role: str
    content: List[MessageContent]

# ----------------------------------------------------------------------------------
# MODEL CONFIGURATIONS
# ----------------------------------------------------------------------------------

@dataclass
class ClaudeConfig:
    """Cấu hình cho Claude API"""
    model_id: str = ModelVersion.CLAUDE_3_5_SONNET_V1.value
    max_tokens: int = 1000
    temperature: float = 0.1
    top_p: float = 0.99
    top_k: Optional[int] = None
    anthopic_version: str = "bedrock-2023-05-31"
    stop_sequences: Optional[List[str]] = None

@dataclass
class LlamaConfig:
    """Cấu hình cho Llama API"""
    model_id: str = ModelVersion.LLAMA_4_17B_SCOUT.value
    max_gen_len: int = 2000
    temperature: float = 0.5
    top_p: float = 0.9
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None

# ----------------------------------------------------------------------------------
# CUSTOM EXCEPTIONS AND RETRY LOGIC
# ----------------------------------------------------------------------------------


class LlamaClientError(Exception):
    """Lỗi tùy chỉnh cho LlamaClient"""
    pass

class ClaudeClientError(Exception):
    """Lỗi tùy chỉnh cho ClaudeClient"""
    pass

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator để tự động retry khi gặp lỗi Boto3Error hoặc ClientError."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ClientError, BotoCoreError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logging.error(f"All {max_retries} attempts failed")
            raise ClaudeClientError(f"Failed after {max_retries} attempts: {last_exception}")
        return wrapper
    return decorator

# ----------------------------------------------------------------------------------
# MODEL HANDLERS
# ----------------------------------------------------------------------------------


class ModelHandler(ABC):
    """Abstract base class cho các model handlers"""
    
    @abstractmethod
    def build_request_body(self, messages: List[Message], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Xây dựng request body cho mô hình cụ thể"""
        pass
    
    @abstractmethod 
    def extract_response_text(self, response: Dict[str, Any]) -> str:
        """Trích xuất text từ response của mô hình"""
        pass

class ClaudeHandler(ModelHandler):
    """Handler cho các mô hình Claude"""
    
    def __init__(self, config: ClaudeConfig):
        self.config = config
    
    def build_request_body(self, messages: List[Message], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Xây dựng request body cho Claude"""
        body = {
            "anthropic_version": self.config.anthopic_version,
            "max_tokens": self.config.max_tokens,
            "messages": [
                {
                    "role": msg.role,
                    "content": [{"type": content.type, "text": content.text} for content in msg.content]
                } for msg in messages
            ],
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }

        if system_prompt:
            body["system"] = system_prompt
        
        if self.config.top_k is not None:
            body["top_k"] = self.config.top_k 
        
        if self.config.stop_sequences:
            body["stop_sequences"] = self.config.stop_sequences

        return body
    
    def extract_response_text(self, response: Dict[str, Any]) -> str:
        """Trích xuất text từ Claude response"""
        if 'content' in response and response['content']:
            return response['content'][0].get('text', '')
        return ""

class LlamaHandler(ModelHandler):
    """Handler cho các mô hình Llama"""
    
    def __init__(self, config: LlamaConfig):
        self.config = config
    
    def build_request_body(self, messages: List[Message], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Xây dựng request body cho Llama"""
        # Chuyển đổi messages thành format của Llama
        prompt = self._format_messages_to_llama_prompt(messages, system_prompt)
        
        body = {
            "prompt": prompt,
            "max_gen_len": self.config.max_gen_len,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }
        
        if self.config.top_k is not None:
            body["top_k"] = self.config.top_k
            
        if self.config.stop_sequences:
            body["stop_sequences"] = self.config.stop_sequences

        return body
    
    def _format_messages_to_llama_prompt(self, messages: List[Message], system_prompt: Optional[str] = None) -> str:
        """Chuyển đổi messages thành format prompt của Llama"""
        formatted_parts = []
        
        if system_prompt:
            formatted_parts.append(f"System: {system_prompt}\n\n")
        
        for msg in messages:
            role = msg.role
            content = " ".join([c.text for c in msg.content])
            if role == "user":
                formatted_parts.append(f"Human: {content}\n\n")
            elif role == "assistant":
                formatted_parts.append(f"Assistant: {content}\n\n")
        
        formatted_parts.append("Assistant:")
        
        return "".join(formatted_parts)
    
    def extract_response_text(self, response: Dict[str, Any]) -> str:
        """Trích xuất text từ Llama response"""
        # Try different possible response formats for Llama
        if "generation" in response:
            return response.get("generation", "")
        elif "completion" in response:
            return response.get("completion", "")
        elif "text" in response:
            return response.get("text", "")
        elif "response" in response:
            return response.get("response", "")
        else:
            return str(response)

# ----------------------------------------------------------------------------------
# MODEL CLIENT
# ----------------------------------------------------------------------------------

class ModelClient:
    """Enhanced Model Client hỗ trợ nhiều mô hình"""

    def __init__(self, config: Optional[Union[ClaudeConfig, LlamaConfig]] = None, region_name: str = "us-east-1"):
        """Khởi tạo client với cấu hình tùy chọn."""
        self.config = config or ClaudeConfig()
        self.region_name = region_name
        self.logger = self._setup_logger()
        self._bedrock_runtime = None
        
        # Xác định loại mô hình và handler
        self.model_type = self._determine_model_type()
        self.handler = self._create_handler()
    
    def _determine_model_type(self) -> ModelType:
        """Xác định loại mô hình dựa trên model_id"""
        model_id = self.config.model_id
        
        if any(claude_model.value == model_id for claude_model in [
            ModelVersion.CLAUDE_3_5_SONNET_V1, 
        ]):
            return ModelType.CLAUDE
        elif any(llama_model.value == model_id for llama_model in [
            ModelVersion.LLAMA_4_17B_SCOUT,
        ]):
            return ModelType.LLAMA
        else:
            # Mặc định là Claude nếu không xác định được
            return ModelType.CLAUDE
    
    def _create_handler(self) -> ModelHandler:
        """Tạo handler phù hợp cho mô hình"""
        if self.model_type == ModelType.CLAUDE:
            # Nếu config không phải ClaudeConfig, tạo mới
            if not isinstance(self.config, ClaudeConfig):
                claude_config = ClaudeConfig(model_id=self.config.model_id)
                return ClaudeHandler(claude_config)
            return ClaudeHandler(self.config)
        else:  # LLAMA
            # Nếu config không phải LlamaConfig, tạo mới
            if not isinstance(self.config, LlamaConfig):
                llama_config = LlamaConfig(model_id=self.config.model_id)
                return LlamaHandler(llama_config)
            return LlamaHandler(self.config)
    
    def _setup_logger(self) -> logging.Logger:
        """Thiết lập logger cho ClaudeClient."""
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    @property
    def bedrock_runtime(self):
        """Lấy client Bedrock Runtime, khởi tạo nếu chưa có."""
        if self._bedrock_runtime is None:
            try:
                self._bedrock_runtime = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=self.region_name,
                )
                self.logger.info(f"Khởi tạo client Bedrock Runtime cho vùng: {self.region_name} thành công.")
            except (BotoCoreError, ClientError) as e:
                raise ClaudeClientError(f"Failed to create Bedrock Runtime client: {e}")
        return self._bedrock_runtime

    def create_message_content(self, text: str) -> List[MessageContent]:
        """Tạo nội dung tin nhắn từ văn bản."""
        return [MessageContent(type="text", text=text)]

    def create_message(self, role: str, content: Union[str, List[MessageContent]]) -> Message:
        """Tạo một tin nhắn từ vai trò và nội dung."""
        if isinstance(content, str):
            content = self.create_message_content(content)
        return Message(role=role, content=content)

    def _build_request_body(
            self,
            messages: List[Message],
            system_prompt: Optional[str] = None,
            config_overrides: Optional[Union[ClaudeConfig, LlamaConfig]] = None
    ) -> Dict[str, Any]:
        """Xây dựng body cho request gửi đến API."""
        if config_overrides:
            # Tạo handler mới cho config override
            if isinstance(config_overrides, ClaudeConfig):
                handler = ClaudeHandler(config_overrides)
            else:
                handler = LlamaHandler(config_overrides)
            return handler.build_request_body(messages, system_prompt)
        
        return self.handler.build_request_body(messages, system_prompt)
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_message(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        config_overrides: Optional[Union[ClaudeConfig, LlamaConfig]] = None
    ) -> Dict[str, Any]:
        """Gửi tin nhắn đến mô hình và nhận phản hồi với retry logic."""
        try:
            body = self._build_request_body(messages, system_prompt, config_overrides)

            # Use model_id from config_overrides if provided, otherwise use default
            model_id = config_overrides.model_id if config_overrides else self.config.model_id
            self.logger.debug(f"Gửi request tới mô hình: {model_id}")

            # print(f"json.dumps(body) \n{json.dumps(body)}")
            
            response = self.bedrock_runtime.invoke_model(
                body=json.dumps(body),
                modelId=model_id,
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response.get("body").read())



            # Log tokens usage khác nhau cho từng loại mô hình
            # Determine model type from config_overrides or default config
            current_model_type = ModelType.LLAMA if config_overrides and isinstance(config_overrides, LlamaConfig) else self.model_type
            
            if current_model_type == ModelType.CLAUDE:
                tokens_used = response_body.get('usage', {}).get('output_tokens', 'N/A')
                self.logger.info(f"Successfully generated message với mô hình Claude. Tokens Used: {tokens_used}")
            else:  # LLAMA
                # Llama không có usage info trong response
                # Llama models trên Bedrock hiện tại CÓ usage info trong response
                prompt_tokens = response_body.get('prompt_token_count', 'N/A')
                generation_tokens = response_body.get('generation_token_count', 'N/A')
                self.logger.info(f"Successfully generated message với mô hình Llama. Input Tokens: {prompt_tokens}, Output Tokens: {generation_tokens}, Total Token: {prompt_tokens + generation_tokens}")
                # Lưu ý: Một số mô hình Llama có thể không trả về prompt_token_count nếu sử dụng InvokeModel với prompt.
                # Tuy nhiên, Converse API và các phiên bản Llama mới hơn thường cung cấp đủ thông tin. [5-8]

            return response_body
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"AWS Client Error [{error_code}]: {error_message}")
            raise ClaudeClientError(f"AWS Error: {error_message}")
        
        except BotoCoreError as e:
            self.logger.error(f"Boto Core Error: {e}")
            raise ClaudeClientError(f"Boto Core Error: {e}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise ClaudeClientError(f"Unexpected error: {e}")
        
    def generate_simple_message(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Wrapper method cho single message đơn giản"""
        message = self.create_message("user", user_input)
        response = self.generate_message([message], system_prompt)
        
        # Sử dụng handler để extract text
        return self.handler.extract_response_text(response)
    
    def continue_conversation(
        self,
        conversation_history: List[Message],
        new_user_message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Wrapper method tiếp tục cuộc hội thoại với lịch sử"""
        message = self.create_message("user", new_user_message)
        conversation_history.append(message)
        
        response = self.generate_message(conversation_history, system_prompt)
        answer = self.handler.extract_response_text(response)
        message = self.create_message("assistant", answer)
        conversation_history.append(message)
        # Sử dụng handler để extract text
        return answer

    def stream_message(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        config_overrides: Optional[Union[ClaudeConfig, LlamaConfig]] = None
    ):
        """Stream response từ Bedrock (chỉ hỗ trợ cho model có streaming, ví dụ Llama 4)."""
        body = self._build_request_body(messages, system_prompt, config_overrides)
        model_id = config_overrides.model_id if config_overrides else self.config.model_id
        # self.logger.info(f"[stream_message] Starting stream for model: {model_id}")
        try:
            response = self.bedrock_runtime.invoke_model_with_response_stream(
                body=json.dumps(body),
                modelId=model_id,
                contentType="application/json",
                accept="application/json"
            )
            # Bedrock trả về response stream, mỗi chunk là bytes
            for event in response['body']:
                if 'chunk' in event:
                    chunk_data = event['chunk']
                    # self.logger.debug(f"[stream_message] Raw chunk data: {repr(chunk_data)}")
                    
                    try:
                        # Bedrock có thể trả về dạng {'bytes': b'...'} hoặc bytes trực tiếp
                        if isinstance(chunk_data, dict) and 'bytes' in chunk_data:
                            # Trường hợp {'bytes': b'...'}
                            chunk_bytes = chunk_data['bytes']
                            chunk_str = chunk_bytes.decode('utf-8')
                        elif isinstance(chunk_data, bytes):
                            # Trường hợp bytes trực tiếp
                            chunk_str = chunk_data.decode('utf-8')
                        else:
                            # Trường hợp string hoặc dict khác
                            chunk_str = chunk_data
                        
                        # self.logger.debug(f"[stream_message] Decoded chunk: {repr(chunk_str)}")
                        
                        # Parse JSON
                        if isinstance(chunk_str, dict):
                            chunk_json = chunk_str
                        else:
                            chunk_json = json.loads(chunk_str)
                        
                        # self.logger.debug(f"[stream_message] Parsed JSON: {chunk_json}")
                        
                        # Thử nhiều field khác nhau
                        text = None
                        if "generation" in chunk_json:
                            text = chunk_json["generation"]
                        elif "completion" in chunk_json:
                            text = chunk_json["completion"]
                        elif "text" in chunk_json:
                            text = chunk_json["text"]
                        elif "content" in chunk_json:
                            # Có thể là format Claude-style
                            content = chunk_json["content"]
                            if isinstance(content, list) and len(content) > 0:
                                text = content[0].get("text", "")
                            elif isinstance(content, str):
                                text = content
                        elif "delta" in chunk_json:
                            # Có thể là format delta
                            delta = chunk_json["delta"]
                            if isinstance(delta, dict) and "text" in delta:
                                text = delta["text"]
                        
                        if text:
                            # self.logger.debug(f"[stream_message] Extracted text: {repr(text)}")
                            yield text
                        else:
                            # if chunk_json and len(str(chunk_json)) > 10:  # Chỉ log nếu chunk có nội dung đáng kể
                            #     self.logger.warning(f"[stream_message] No text found in chunk: {chunk_json}")
                            # else:
                            #     self.logger.debug(f"[stream_message] Skipping empty/metadata chunk: {chunk_json}")
                            pass
                    except json.JSONDecodeError as e:
                        # self.logger.warning(f"[stream_message] Failed to parse JSON: {e}, chunk: {repr(chunk_str)}")
                        continue
                    except Exception as e:
                        # self.logger.error(f"[stream_message] Error processing chunk: {e}")
                        continue
        except Exception as e:
            # self.logger.error(f"Error in stream_message: {e}")
            yield f"[STREAM_ERROR] {str(e)}"


# ----------------------------------------------------------------------------------
# CREATE MODEL CONFIG
# ----------------------------------------------------------------------------------

# Convenience functions để tạo config dễ dàng
def create_claude_config(**kwargs) -> ClaudeConfig:
    """Tạo ClaudeConfig với các tham số tùy chọn"""
    return ClaudeConfig(**kwargs)

def create_llama_config(**kwargs) -> LlamaConfig:
    """Tạo LlamaConfig với các tham số tùy chọn"""
    return LlamaConfig(**kwargs)

def load_config_from_yaml(yaml_path: str, model_type: str = "claude") -> Union[ClaudeConfig, LlamaConfig]:
    """Load config từ file yaml cho Claude hoặc Llama"""
    with open(yaml_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    if model_type.lower() == "claude":
        return ClaudeConfig(**config_dict.get("claude", {}))
    elif model_type.lower() == "llama":
        return LlamaConfig(**config_dict.get("llama", {}))
    else:
        raise ValueError(f"Unknown model_type: {model_type}")
