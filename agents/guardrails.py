import json
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

# Chỉ dùng Guardrails AI Hub (LlamaGuard7B)
try:
    from guardrails.hub import LlamaGuard  # type: ignore
    LLAMAGUARD_AVAILABLE = True
except ImportError:
    LLAMAGUARD_AVAILABLE = False


class SafetyLevel(Enum):
    SAFE = "safe"
    BLOCKED = "blocked"


class Guardrails:
    """Bộ kiểm duyệt đầu vào và đầu ra sử dụng Guardrails LlamaGuard."""

    def __init__(self):
        # Khởi tạo Guardrails nếu có sẵn
        if LLAMAGUARD_AVAILABLE:
            self.llamaguard_input = LlamaGuard(policy=Path("agents/policy_input.yaml"))
            self.llamaguard_output = LlamaGuard(policy=Path("agents/policy_output.yaml"))
        else:
            self.llamaguard_input = None
            self.llamaguard_output = None

    def llamaguard_check(self, text: str, is_output: bool = False) -> Dict:
        """Kiểm tra văn bản theo chính sách Guardrails."""
        guard = self.llamaguard_output if is_output else self.llamaguard_input

        if not guard:
            # Nếu không có Guardrails, mặc định cho phép
            return {
                "is_safe": True,
                "safety_level": SafetyLevel.SAFE,
                "block_reason": None,
                "warnings": [],
                "need_clarification": False,
                "clarification_message": None,
            }

        try:
            result = guard.validate(text)
            if result.get("valid", True):
                return {
                    "is_safe": True,
                    "safety_level": SafetyLevel.SAFE,
                    "block_reason": None,
                    "warnings": [],
                    "need_clarification": False,
                    "clarification_message": None,
                }
            else:
                return {
                    "is_safe": False,
                    "safety_level": SafetyLevel.BLOCKED,
                    "block_reason": result.get("reason", "Vi phạm chính sách Guardrails"),
                    "warnings": [],
                    "need_clarification": False,
                    "clarification_message": None,
                }
        except Exception as e:
            print(f"[Guardrails] Lỗi khi gọi LlamaGuard: {e}")
            return {
                "is_safe": True,
                "safety_level": SafetyLevel.SAFE,
                "block_reason": None,
                "warnings": [str(e)],
                "need_clarification": False,
                "clarification_message": None,
            }

    def extract_law_from_history(self, messages: list) -> Optional[str]:
        """Trích xuất thông tin về luật từ lịch sử hội thoại."""
        for msg in reversed(messages):
            if msg.get("role") == "user" and "luật" in msg.get("content", "").lower():
                return msg["content"]
        return None

    def validate_input(self, question: str, messages: Optional[list] = None) -> Dict:
        """Kiểm tra đầu vào người dùng."""
        return self.llamaguard_check(question, is_output=False)

    def validate_output(self, text: str) -> Dict:
        """Kiểm tra đầu ra từ mô hình."""
        start_time = time.time()
        result = self.llamaguard_check(text, is_output=True)
        result["processing_time"] = time.time() - start_time
        self.log_validation_result("OUTPUT", text, result)
        return result

    def log_validation_result(self, validation_type: str, text: str, result: Dict):
        """Ghi log kết quả kiểm duyệt."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": validation_type,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_safe": result["is_safe"],
            "safety_level": result["safety_level"].value
            if hasattr(result["safety_level"], "value")
            else str(result["safety_level"]),
            "block_reason": result["block_reason"],
            "warnings": result.get("warnings", []),
            "processing_time": result.get("processing_time", 0),
            "need_clarification": result.get("need_clarification", False),
            "clarification_message": result.get("clarification_message", None),
        }
        print(f"[Guardrails {validation_type}] {json.dumps(log_entry, ensure_ascii=False)}")

    def get_fallback_message(self, block_reason: str) -> str:
        """Trả về tin nhắn fallback nếu nội dung bị chặn."""
        return "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam."

    def is_ambiguous(self, text: str) -> bool:
        """Không sử dụng. Mặc định trả về False."""
        return False

    def is_safe(self, text: str) -> bool:
        """Không sử dụng. Mặc định luôn trả về True."""
        return True
