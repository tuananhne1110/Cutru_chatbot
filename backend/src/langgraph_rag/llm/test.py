import json
from typing import Iterable, Iterator, List, Optional, Dict, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from ..utils.logger_utils import get_logger

from .base import BaseConfig

logger = get_logger(__name__)


def _to_converse_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chuẩn hoá messages sang định dạng Bedrock Converse:
    [{"role":"user|assistant|system", "content":[{"text":"..."}]}]
    - Hỗ trợ input dạng [{"role":"user","content":"..."}] hoặc [{"role":"user","content":[{"text":"..."}]}]
    """
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # đã đúng định dạng content-blocks
            out.append({"role": role, "content": content})
        else:
            out.append({"role": role, "content": [{"text": str(content)}]})
    return out


def _build_guardrail_config(cfg: BaseConfig) -> Optional[Dict[str, Any]]:
    """
    Guardrails chỉ đính kèm nếu được bật và đủ thông tin.
    """
    if not getattr(cfg, "guardrails_enabled", False):
        return None
    if not cfg.guardrails_id or not cfg.guardrails_version:
        logger.warning("Guardrails enabled but id/version is missing.")
        return None
    return {
        "guardrailIdentifier": cfg.guardrails_id,
        "guardrailVersion": cfg.guardrails_version,
    }


class BedrockLLM:
    """
    Thin wrapper cho Bedrock `converse` / `converse_stream`.
    Đọc cấu hình từ BaseConfig (load từ YAML).
    """

    def __init__(self, config: BaseConfig):
        self.cfg = config
        self.model_id = config.llm_name
        self.region = getattr(config, "region_name", config.guardrails_region_name)
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

        # Gán sẵn inference config cơ bản
        self.inference_config = {
            "maxTokens": config.max_new_tokens or 2000,
            "temperature": float(config.temperature or 0.0),
        }
        # Optional: topP nếu bạn muốn set tuỳ model
        # self.inference_config["topP"] = 0.9

        self.guardrail_config = _build_guardrail_config(config)

        logger.info(
            "[BedrockLLM] Ready: model=%s region=%s guardrails=%s",
            self.model_id,
            self.region,
            bool(self.guardrail_config),
        )

    # ---------- Public APIs ----------
    def chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        extra_model_fields: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Gọi non-stream, trả về text hợp nhất.
        """
        try:
            msg_blocks = _to_converse_messages(messages)
            if system:
                msg_blocks = [{"role": "system", "content": [{"text": system}]}] + msg_blocks

            kwargs: Dict[str, Any] = dict(
                modelId=self.model_id,
                messages=msg_blocks,
                inferenceConfig=self.inference_config,
            )

            if self.guardrail_config:
                kwargs["guardrailConfig"] = self.guardrail_config
            if tool_config:
                kwargs["toolConfig"] = tool_config
            if extra_model_fields:
                # Vendor-specific fields (đính kèm)
                kwargs["additionalModelRequestFields"] = extra_model_fields

            resp = self.client.converse(**kwargs)
            return self._extract_text(resp)

        except (ClientError, BotoCoreError) as e:
            logger.exception("Bedrock converse error: %s", e)
            # Thử fallback invoke_model (Meta Llama) khi converse không hỗ trợ
            return self._fallback_invoke(messages, system)

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        extra_model_fields: Optional[Dict[str, Any]] = None,
    ) -> Iterator[str]:
        """
        Gọi stream, yield từng delta text.
        """
        try:
            msg_blocks = _to_converse_messages(messages)
            if system:
                msg_blocks = [{"role": "system", "content": [{"text": system}]}] + msg_blocks

            kwargs: Dict[str, Any] = dict(
                modelId=self.model_id,
                messages=msg_blocks,
                inferenceConfig=self.inference_config,
            )
            if self.guardrail_config:
                kwargs["guardrailConfig"] = self.guardrail_config
            if tool_config:
                kwargs["toolConfig"] = tool_config
            if extra_model_fields:
                kwargs["additionalModelRequestFields"] = extra_model_fields

            stream = self.client.converse_stream(**kwargs)
            for ev in stream.get("stream", []):
                # Các event: messageStart, contentBlockDelta, messageStop, metadata...
                if "contentBlockDelta" in ev:
                    delta = ev["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        yield delta["text"]
        except (ClientError, BotoCoreError) as e:
            logger.exception("Bedrock converse_stream error: %s", e)
            # Fallback non-stream
            text = self._fallback_invoke(messages, system)
            if text:
                yield text

    # ---------- Helpers ----------
    def _extract_text(self, resp: Dict[str, Any]) -> str:
        """
        Rút text từ response của converse.
        """
        try:
            out = []
            for c in resp.get("output", {}).get("message", {}).get("content", []):
                if "text" in c:
                    out.append(c["text"])
            return "".join(out).strip()
        except Exception:
            return ""

    def _fallback_invoke(self, messages: List[Dict[str, Any]], system: Optional[str]) -> str:
        """
        Fallback dùng invoke_model cho một số model (ví dụ Meta Llama).
        Ghép prompt đơn giản từ conversation.
        """
        try:
            prompt = self._messages_to_prompt(messages, system)
            body = {
                "prompt": prompt,
                "temperature": float(self.cfg.temperature or 0.0),
                "max_gen_len": int(self.cfg.max_new_tokens or 2000),
                # "top_p": 0.9,   # tuỳ chọn
            }
            resp = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body).encode("utf-8"),
                accept="application/json",
                contentType="application/json",
            )
            payload = json.loads(resp.get("body").read().decode("utf-8"))
            # Meta Llama trả {"generation":"..."} hoặc {"outputs":[{"text":"..."}]} tuỳ phiên bản
            if "generation" in payload:
                return payload["generation"]
            if "outputs" in payload and payload["outputs"]:
                return payload["outputs"][0].get("text", "")
            # Anthropics (nếu rơi vào đây) có format khác — cố gắng gom text
            return payload.get("output_text") or payload.get("content", "")
        except Exception as e:
            logger.exception("Fallback invoke_model failed: %s", e)
            return ""

    def _messages_to_prompt(self, messages: List[Dict[str, Any]], system: Optional[str]) -> str:
        """
        Ghép prompt từ messages theo format đơn giản.
        """
        parts: List[str] = []
        if system:
            parts.append(f"[SYSTEM]\n{system}\n")
        for m in messages:
            role = m.get("role", "user").upper()
            content = m.get("content", "")
            if isinstance(content, list):
                # lấy text blocks
                text = " ".join([b.get("text", "") for b in content if isinstance(b, dict)])
            else:
                text = str(content)
            parts.append(f"[{role}]\n{text}\n")
        parts.append("[ASSISTANT]\n")
        return "\n".join(parts)
