import time
import os
import json
from typing import Dict, Optional
from enum import Enum
from datetime import datetime
from pathlib import Path

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
    def __init__(self):
        if LLAMAGUARD_AVAILABLE:
            self.llamaguard_input = LlamaGuard(policy=Path("agents/policy_input.yaml"))
            self.llamaguard_output = LlamaGuard(policy=Path("agents/policy_output.yaml"))
        else:
            self.llamaguard_input = None
            self.llamaguard_output = None

    def llamaguard_check(self, text: str, is_output: bool = False) -> Dict:
        guard = self.llamaguard_output if is_output else self.llamaguard_input
        if not guard:
            return {"is_safe": True, "safety_level": SafetyLevel.SAFE, "block_reason": None, "warnings": [], "need_clarification": False, "clarification_message": None}
        try:
            result = guard.validate(text)
            if result.get("valid", True):
                return {"is_safe": True, "safety_level": SafetyLevel.SAFE, "block_reason": None, "warnings": [], "need_clarification": False, "clarification_message": None}
            else:
                return {"is_safe": False, "safety_level": SafetyLevel.BLOCKED, "block_reason": result.get("reason", "Vi phạm chính sách Guardrails"), "warnings": [], "need_clarification": False, "clarification_message": None}
        except Exception as e:
            print(f"[Guardrails] LlamaGuard error: {e}")
            return {"is_safe": True, "safety_level": SafetyLevel.SAFE, "block_reason": None, "warnings": [str(e)], "need_clarification": False, "clarification_message": None}

    def extract_law_from_history(self, messages):
        for msg in reversed(messages):
            if msg.get('role') == 'user' and 'luật' in msg.get('content', '').lower():
                return msg['content']
        return None

    def validate_input(self, question, messages=None):
        return self.llamaguard_check(question, is_output=False)

    def validate_output(self, text: str) -> Dict:
        start_time = time.time()
        result = self.llamaguard_check(text, is_output=True)
        result["processing_time"] = time.time() - start_time
        self.log_validation_result("OUTPUT", text, result)
        return result

    def log_validation_result(self, validation_type: str, text: str, result: Dict):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": validation_type,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_safe": result["is_safe"],
            "safety_level": result["safety_level"].value if hasattr(result["safety_level"], 'value') else str(result["safety_level"]),
            "block_reason": result["block_reason"],
            "warnings": result.get("warnings", []),
            "processing_time": result.get("processing_time", 0),
            "need_clarification": result.get("need_clarification", False),
            "clarification_message": result.get("clarification_message", None)
        }
        print(f"[Guardrails {validation_type}] {json.dumps(log_entry, ensure_ascii=False)}")

    def get_fallback_message(self, block_reason: str) -> str:
        return "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam."

    def is_ambiguous(self, text: str) -> bool:
        # Không dùng nữa, luôn trả về False
        return False

    def is_safe(self, text: str) -> bool:
        # Không dùng nữa, luôn trả về True
        return True 