import os
from typing import Iterator, List, Tuple
from copy import deepcopy
import sqlite3
import json
import time
import hashlib

import litellm
from filelock import FileLock

from .base import BaseLLMConfig, LLMConfig
from ..utils.llm_utils import TextChatMessage
from ..utils.logger_utils import get_logger

logger = get_logger(__name__)



class LLM_Cache:
    def __init__(self, cache_dir: str, cache_filename):
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_filepath =  os.path.join(cache_dir, f"{cache_filename}.sqlite")
        self.lock_file = self.cache_filepath + ".lock"

        self.__db_operation("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                message TEXT,
                metadata TEXT
            )
        """, commit=True)
    
    def __db_operation(self, sql, parameters=(), commit=False, fetchone=False):
        with FileLock(self.lock_file):
            conn = sqlite3.connect(self.cache_filepath)
            c = conn.cursor()
            c.execute(sql, parameters)
            if commit:
                conn.commit()
            if fetchone:
                row = c.fetchone()
            conn.close()
            if fetchone:
                return row

    def __params_to_key(self, params):
        key_str = f"Model: {params['model']}, Temperature: {params['temperature']}, Messages: {params['messages']}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def read(self, params):
        key = self.__params_to_key(params)
        row = self.__db_operation("SELECT message, metadata FROM cache WHERE key = ?", (key,), fetchone=True)
        if row is None:
            return None
        message, metadata_str = row
        metadata = json.loads(metadata_str)
        return message, metadata

    def write(self, params, message, metadata):
        key = self.__params_to_key(params)
        metadata_str = json.dumps(metadata)
        self.__db_operation("INSERT OR REPLACE INTO cache (key, message, metadata) VALUES (?, ?, ?)", (key, message, metadata_str), commit=True)

# cache này quá phế , cần xây dựng lại

class BedrockLLM(BaseLLMConfig):
    """
    To select this implementation you can initialise HippoRAG with:
        Model-ID: llm_model_name="us.meta.llama4-scout-17b-instruct-v1:0"
    """
    def __init__(self, global_config = None):
        self.global_config = global_config
        super().__init__(global_config)
        self._init_llm_config()

        self.cache = LLM_Cache(
            os.path.join(global_config.save_dir, "llm_cache"),
            self.llm_name.replace('/', '_'))        
        
        self.retry = 5
        
        logger.info(f"[BedrockLLM] Model-ID: {self.global_config.llm_name}, Cache: {self.cache.cache_filepath}")

    def _init_llm_config(self) -> None:
        config_dict = self.global_config.__dict__
        
        config_dict['llm_name'] = self.global_config.llm_name

        config_dict['generate_params'] = {
                "model": self.global_config.llm_name,
                "temperature": config_dict.get("temperature", 0.0),
                "aws_region_name": config_dict.get("region_name", "us-east-1")
            }

        self.llm_config = LLMConfig.from_dict(config_dict=config_dict)
        # logger.info(f"[BedrockLLM] Config: {self.llm_config}")

    def __llm_call(self, params):
        num, wait_s = 0, 0.5
        while True:
            try:
                return litellm.completion(**params)
            except Exception as e:
                num += 1
                if num > self.retry:
                    raise e
                
                logger.warning(f"Bedrock LLM Exception: {e}\nRetry #{num} after {wait_s} seconds")
                time.sleep(wait_s)
                wait_s *= 2
    
    def infer(self, messages: List[TextChatMessage], **kwargs) -> Tuple[List[TextChatMessage], dict]:
        params = deepcopy(self.llm_config.generate_params)
        if kwargs:
            params.update(kwargs)
        params["messages"] = messages
        
        # cache_lookup = self.cache.read(params)

        cache_lookup = None
        if cache_lookup is not None:
            cached = True
            message, metadata = cache_lookup
        else:
            cached = False
            response = self.__llm_call(params)
            message = response.choices[0].message.content
            metadata = {
                "prompt_tokens": response.usage.prompt_tokens, 
                "completion_tokens": response.usage.completion_tokens,
                "finish_reason": response.choices[0].finish_reason,
            }
            self.cache.write(params, message, metadata)

        return message, metadata, cached

    # def infer(self, messages: List[TextChatMessage], **kwargs) -> Tuple[List[TextChatMessage], dict]:
    #     params = deepcopy(self.llm_config.generate_params)
    #     if kwargs:
    #         params.update(kwargs)
    #     params["messages"] = messages

    #     # ===== 1) Cache lookup =====
    #     cache_lookup = self.cache.read(params)
    #     if cache_lookup is not None:
    #         cached = True
    #         message, metadata = cache_lookup

    #         # Log 1 span ngắn cho cache hit (để nhìn tỉ lệ cache vs non-cache)
    #         with LANGFUSE.start_as_current_span(name="llm.cache_hit") as s:
    #             s.update(metadata={
    #                 "model": params.get("model"),
    #                 "cached": True,
    #                 "temperature": params.get("temperature"),
    #                 "region": params.get("region_name"),
    #             })
    #             # tránh log cả prompt dài -> chỉ preview vài dòng
    #             try:
    #                 preview = [{"role": m.get("role"), "content": str(m.get("content"))[:200]}
    #                         for m in messages[-3:]]
    #                 s.update(input={"messages_preview": preview})
    #                 s.update(output={"answer_preview": str(message)[:200]})
    #             except Exception:
    #                 pass

    #         return message, metadata, cached

    #     # ===== 2) Non-cache: gọi LLM và log Generation =====
    #     cached = False
    #     with LANGFUSE.start_as_current_generation(
    #         name="bedrock_llm.completion",
    #         model=params.get("model"),
    #     ) as gen:
    #         # log input + hyperparams để dễ debug/cost analysis
    #         try:
    #             gen.update(
    #                 input=messages,
    #                 metadata={
    #                     "temperature": params.get("temperature"),
    #                     "region": params.get("region_name"),
    #                 },
    #             )
    #         except Exception:
    #             # nếu input quá lớn/không serialize được, cứ bỏ qua
    #             pass

    #         # Gọi thực sự
    #         response = self.__llm_call(params)

    #         # Trích kết quả + usage
    #         message = response.choices[0].message.content
    #         usage = {
    #             "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
    #             "completion_tokens": getattr(response.usage, "completion_tokens", None),
    #             "total_tokens": (
    #                 (getattr(response.usage, "prompt_tokens", 0) or 0) +
    #                 (getattr(response.usage, "completion_tokens", 0) or 0)
    #             ),
    #         }
    #         metadata = {
    #             "prompt_tokens": usage["prompt_tokens"],
    #             "completion_tokens": usage["completion_tokens"],
    #             "finish_reason": response.choices[0].finish_reason,
    #         }

    #         # Cập nhật output + usage cho Langfuse
    #         try:
    #             gen.update(output=message, usage=usage)
    #         except Exception:
    #             # vẫn tiếp tục ngay cả khi update fail (vd: output quá dài)
    #             pass

    #         # Lưu cache
    #         self.cache.write(params, message, metadata)

    #     return message, metadata, cached

    
    
    def stream_infer(self, messages: List[TextChatMessage], **kwargs) -> Iterator[str]:
        """
        Streaming sinh đáp án từng phần.
        - Yield: các mảnh văn bản (delta) từ mô hình.
        - Khi stream kết thúc, kết quả đầy đủ sẽ được ghi vào cache (nếu có nội dung).

        Cách dùng:
            gen = bedrock_llm.stream_infer(messages, max_tokens=512)
            for delta in gen:
                print(delta, end="", flush=True)
        """
        # 1) Chuẩn bị params
        params = deepcopy(self.llm_config.generate_params)
        if kwargs:
            params.update(kwargs)
        params["messages"] = messages

        # 2) Thử lấy từ cache trước (nếu có thì yield luôn 1 lần)
        cache_lookup = self.cache.read(params)
        if cache_lookup is not None:
            message, _metadata = cache_lookup
            if message:
                yield message
            return

        # 3) Gọi LLM ở chế độ streaming
        params["stream"] = True
        response_iter = self.__llm_call(params)

        # 4) Duyệt stream, yield token/delta và ghép lại để lưu cache khi xong
        full_chunks = []
        finish_reason = None
        last_usage = None

        try:
            for part in response_iter:
                # litellm chuẩn OpenAI: choices[0].delta.content
                delta = ""
                try:
                    delta = getattr(part.choices[0].delta, "content", "") or ""
                except Exception:
                    # một số provider dùng choices[0].text
                    delta = getattr(part.choices[0], "text", "") or ""

                if delta:
                    full_chunks.append(delta)
                    yield delta

                # có thể có finish_reason ở cuối
                try:
                    fr = getattr(part.choices[0], "finish_reason", None)
                    if fr:
                        finish_reason = fr
                except Exception:
                    pass

                # một số SDK đính kèm usage ở chunk cuối
                try:
                    last_usage = getattr(part, "usage", None) or last_usage
                except Exception:
                    pass

        finally:
            # 5) Ghi cache nếu có nội dung
            final_text = "".join(full_chunks).strip()
            if final_text:
                metadata = {
                    "prompt_tokens": getattr(last_usage, "prompt_tokens", None) if last_usage else None,
                    "completion_tokens": getattr(last_usage, "completion_tokens", None) if last_usage else None,
                    "finish_reason": finish_reason or "stop",
                }
                # Lưu ý: khoá cache của bạn chỉ dựa vào (model, temperature, messages),
                # nên việc có/không có 'stream' trong params không ảnh hưởng.
                self.cache.write(params, final_text, metadata)

                
# # run: python -m backend.src.langgraph_rag.llm.bedrock_llm
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     bedrock_llm = BedrockLLM(global_config= global_config)

#     messages: List[TextChatMessage] = [
#         {"role": "system", "content": "Bạn là một trợ lý hữu ích"},
#         {"role": "user", "content": "Cầu vồng có mấy màu? và nguyên lý hình thành nên cầu vồng là gì ?"},
#     ]

#     response_text, metadata, cached = bedrock_llm.infer(messages)

#     # 📤 In kết quả
#     print("🔁 Cached:", cached)
#     print("📨 Response:", response_text)
#     print("📊 Metadata:", metadata)
