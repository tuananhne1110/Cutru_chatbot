import json
import os
import time
import re
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
            try:
                self.llamaguard_input = LlamaGuard(policy=Path("agents/policy_input.yaml"))
                self.llamaguard_output = LlamaGuard(policy=Path("agents/policy_output.yaml"))
                print("[Guardrails] LlamaGuard initialized successfully")
            except Exception as e:
                print(f"[Guardrails] Failed to initialize LlamaGuard: {e}")
                self.llamaguard_input = None
                self.llamaguard_output = None
        else:
            print("[Guardrails] LlamaGuard not available, using rule-based filtering")
            self.llamaguard_input = None
            self.llamaguard_output = None

    def rule_based_safety_check(self, text: str) -> Dict:
        """Rule-based safety check khi không có LlamaGuard."""
        text_lower = text.lower()
        
        # Danh sách từ khóa nguy hiểm
        dangerous_keywords = [
            # Hành vi nguy hiểm
            "giết người", "tự tử", "lừa đảo", "hack", "crack", "virus", "malware",
            "bom", "vũ khí", "ma túy", "heroin", "cocaine", "amphetamine",
            "buôn bán ma túy", "rửa tiền", "trốn thuế", "lách luật",
            
            # Bạo lực và thù hận
            "khủng bố", "bạo lực", "thù hận", "phân biệt chủng tộc", "xâm hại",
            "hiếp dâm", "bắt cóc", "tra tấn", "hành hạ",
            
            # Nội dung nhạy cảm
            "khiêu dâm", "sex", "porn", "nude", "tục tĩu", "thô tục",
            
            # Chính trị nhạy cảm
            "lật đổ", "phản động", "chống phá", "xuyên tạc", "bôi nhọ",
            
            # Hành vi trái pháp luật
            "làm giả", "giả mạo", "ăn cắp", "trộm cắp", "cướp", "bắt cóc",
            "buôn lậu", "vận chuyển ma túy", "tổ chức đánh bạc"
        ]
        
        # Kiểm tra từ khóa nguy hiểm
        for keyword in dangerous_keywords:
            if keyword in text_lower:
                return {
                    "is_safe": False,
                    "safety_level": SafetyLevel.BLOCKED,
                    "block_reason": f"Chứa từ khóa nguy hiểm: {keyword}",
                    "warnings": [f"Detected dangerous keyword: {keyword}"],
                    "need_clarification": False,
                    "clarification_message": None,
                }
        
        # Kiểm tra pattern nguy hiểm
        dangerous_patterns = [
            r"cách\s+(giết|hack|lừa|trộm|cướp|bắt cóc)",
            r"hướng dẫn\s+(giết|hack|lừa|trộm|cướp|bắt cóc)",
            r"làm sao\s+để\s+(giết|hack|lừa|trộm|cướp|bắt cóc)",
            r"cách\s+(tự tử|tự sát)",
            r"hướng dẫn\s+(tự tử|tự sát)",
            r"cách\s+(làm bom|chế tạo vũ khí)",
            r"hướng dẫn\s+(làm bom|chế tạo vũ khí)",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text_lower):
                return {
                    "is_safe": False,
                    "safety_level": SafetyLevel.BLOCKED,
                    "block_reason": f"Chứa pattern nguy hiểm: {pattern}",
                    "warnings": [f"Detected dangerous pattern: {pattern}"],
                    "need_clarification": False,
                    "clarification_message": None,
                }
        
        # Nếu không vi phạm, trả về an toàn
        return {
            "is_safe": True,
            "safety_level": SafetyLevel.SAFE,
            "block_reason": None,
            "warnings": [],
            "need_clarification": False,
            "clarification_message": None,
        }

    def llamaguard_check(self, text: str, is_output: bool = False) -> Dict:
        """Kiểm tra văn bản theo chính sách Guardrails."""
        guard = self.llamaguard_output if is_output else self.llamaguard_input

        if not guard:
            # Sử dụng rule-based filtering khi không có LlamaGuard
            print(f"[Guardrails] Using rule-based filtering for {'output' if is_output else 'input'}")
            return self.rule_based_safety_check(text)

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
            # Fallback về rule-based khi có lỗi
            print(f"[Guardrails] Falling back to rule-based filtering")
            return self.rule_based_safety_check(text)

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
