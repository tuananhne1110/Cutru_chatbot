import re
import time
import os
import requests
import json
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime

from services.llm_service import call_llm_full

class SafetyLevel(Enum):
    SAFE = "safe"
    WARNING = "warning"
    BLOCKED = "blocked"

class ContentType(Enum):
    LEGAL_QUERY = "legal_query"
    PERSONAL_INFO = "personal_info"
    HARMFUL_CONTENT = "harmful_content"
    OFF_TOPIC = "off_topic"
    SPAM = "spam"
    POLITICAL = "political"

class Guardrails:
    def __init__(self):
        # OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_moderation_url = "https://api.openai.com/v1/moderations"
        
        # Lớp 1: Rule-based/Regex filter
        self.setup_rule_based_filters()
        
        # Các từ khóa liên quan đến pháp luật (để kiểm tra relevance)
        self.legal_keywords = [
            "luật", "nghị định", "thông tư", "quyết định", "pháp lệnh",
            "điều", "khoản", "điểm", "chương", "mục", "phần",
            "tòa án", "viện kiểm sát", "công an", "chính phủ", "quốc hội",
            "ly hôn", "kết hôn", "thừa kế", "đất đai", "nhà ở",
            "lao động", "thuế", "hình sự", "dân sự", "hành chính",
            "quyền", "nghĩa vụ", "trách nhiệm", "vi phạm", "xử phạt",
            "cư trú", "hộ khẩu", "giấy tờ", "thủ tục", "quy định",
            # Thêm các từ khóa về đấu thầu, mua sắm công
            "đấu thầu", "mua sắm", "hồ sơ", "dự thầu", "nhà thầu",
            "gói thầu", "phương án", "giá dự thầu", "đánh giá",
            "lựa chọn", "trúng thầu", "hợp đồng", "thanh toán",
            "nghiệm thu", "quyết toán", "thẩm định", "phê duyệt"
        ]

    def setup_rule_based_filters(self):
        """Thiết lập các filter rule-based"""
        # Từ khóa nhạy cảm (tục tĩu, bạo lực, chính trị...)
        self.sensitive_keywords = [
            # Tục tĩu
            "fuck", "shit", "bitch", "dick", "pussy", "cock", "ass",
            "lồn", "địt", "đụ", "đéo", "đcm", "đm", "clm", "cl",
            "xxx", "sex", "nude", "porn", "adult", "18+",
            
            # Bạo lực
            "kill", "death", "die", "murder", "suicide", "bom", "bomb",
            "chết", "giết", "tự tử", "bạo lực", "đánh", "đấm", "đá",
            
            # Chính trị nhạy cảm
            "Việt Tân", "phản động", "chống phá", "lật đổ", "cách mạng",
            "biểu tình", "đình công", "bãi công", "chống đối",
            
            # Ma túy, tội phạm
            "ma túy", "heroin", "cocaine", "marijuana", "drugs",
            "buôn bán", "vận chuyển", "sử dụng", "nghiện",
            
            # Lừa đảo, hack
            "hack", "virus", "malware", "phishing", "scam",
            "lừa đảo", "rửa tiền", "tham nhũng", "hối lộ"
        ]
        
        # Regex patterns cho thông tin cá nhân
        self.pii_patterns = [
            r'\b\d{9,12}\b',  # CMND/CCCD
            r'\b\d{10,11}\b',  # Số điện thoại
            r'\b[A-Z]{2}\d{7}\b',  # Passport
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Số thẻ tín dụng
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
        
        # Regex cho spam
        self.spam_patterns = [
            r'!{3,}',  # Nhiều dấu chấm than
            r'\?{3,}',  # Nhiều dấu hỏi
            r'[A-Z]{5,}',  # Nhiều chữ hoa liên tiếp
            r'\b(?:FREE|FREE|FREE|FREE|FREE)\b',  # Từ FREE lặp lại
        ]

    def layer1_rule_based_check(self, text: str) -> Tuple[SafetyLevel, List[str], Dict]:
        """Lớp 1: Rule-based/Regex filter (siêu nhanh, free)"""
        start_time = time.time()
        text_lower = text.lower()
        violations = []
        details = {
            "sensitive_keywords": [],
            "pii_found": [],
            "spam_indicators": [],
            "processing_time": 0
        }
        
        # Kiểm tra từ khóa nhạy cảm
        for keyword in self.sensitive_keywords:
            if keyword.lower() in text_lower:
                details["sensitive_keywords"].append(keyword)
                violations.append(f"sensitive_keyword:{keyword}")
        
        # Kiểm tra PII patterns
        for pattern in self.pii_patterns:
            matches = re.findall(pattern, text)
            if matches:
                details["pii_found"].extend(matches)
                violations.append(f"pii_pattern:{pattern}")
        
        # Kiểm tra spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, text):
                details["spam_indicators"].append(pattern)
                violations.append(f"spam_pattern:{pattern}")
        
        # Quyết định safety level
        if len(details["sensitive_keywords"]) >= 2 or len(details["pii_found"]) >= 2:
            safety_level = SafetyLevel.BLOCKED
        elif len(violations) >= 1:
            safety_level = SafetyLevel.WARNING
        else:
            safety_level = SafetyLevel.SAFE
        
        details["processing_time"] = time.time() - start_time
        
        return safety_level, violations, details

    def layer2_openai_moderation(self, text: str) -> Tuple[SafetyLevel, Dict]:
        """Lớp 2: OpenAI Moderation API (có phí, dùng cho nội dung vượt qua lớp 1)"""
        if not self.openai_api_key:
            return SafetyLevel.SAFE, {"error": "No OpenAI API key"}
        
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": text,
                "model": "text-moderation-latest"
            }
            
            response = requests.post(
                self.openai_moderation_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                return SafetyLevel.SAFE, {"error": f"API error: {response.status_code}"}
            
            result = response.json()
            results = result.get("results", [])
            
            if not results:
                return SafetyLevel.SAFE, {}
            
            moderation_result = results[0]
            flagged = moderation_result.get("flagged", False)
            categories = moderation_result.get("category_scores", {})
            
            # Kiểm tra các category nguy hiểm
            dangerous_categories = [
                "harassment", "hate", "self_harm", "sexual", "violence"
            ]
            
            flagged_categories = []
            max_score = 0
            
            for category in dangerous_categories:
                score = categories.get(category, 0)
                if score > 0.5:  # Threshold 0.5
                    flagged_categories.append({
                        "category": category,
                        "score": score
                    })
                    max_score = max(max_score, score)
            
            details = {
                "flagged": flagged,
                "categories": flagged_categories,
                "max_score": max_score,
                "processing_time": time.time() - start_time
            }
            
            if flagged or max_score > 0.7:
                return SafetyLevel.BLOCKED, details
            elif max_score > 0.3:
                return SafetyLevel.WARNING, details
            
            return SafetyLevel.SAFE, details
            
        except Exception as e:
            return SafetyLevel.SAFE, {"error": str(e), "processing_time": time.time() - start_time}

    def layer3_policy_guardrails(self, text: str, is_output: bool = False) -> str:
        """Lớp 3: Policy guardrails bằng prompt LLM"""
        if is_output:
            # Kiểm tra output từ LLM
            prompt = f"""
Bạn là hệ thống kiểm duyệt nội dung pháp luật. Hãy kiểm tra câu trả lời sau có vi phạm quy định không:

Câu trả lời: "{text}"

Quy định cần tuân thủ:
1. Chỉ trả lời trong phạm vi pháp luật Việt Nam (hành chính, dân sự, hình sự, lao động, thuế, đất đai, nhà ở, đấu thầu, mua sắm công, v.v.)
2. Không tư vấn cá nhân, không đưa ra ý kiến chủ quan
3. Không bịa thông tin, phải trích dẫn Điều/Khoản cụ thể
4. Không nói xấu, tuyên truyền trái pháp luật
5. Không trả lời nội dung nhạy cảm, chính trị

Nếu vi phạm, trả về: "VIOLATION: [lý do]"
Nếu an toàn, trả về: "SAFE"
"""
        else:
            # Kiểm tra input từ user
            prompt = f"""
Bạn là hệ thống kiểm duyệt câu hỏi pháp luật. Hãy kiểm tra câu hỏi sau có phù hợp không:

Câu hỏi: "{text}"

Tiêu chí:
1. Phải liên quan đến pháp luật Việt Nam (hành chính, dân sự, hình sự, lao động, thuế, đất đai, nhà ở, đấu thầu, mua sắm công, v.v.)
2. Không chứa nội dung nhạy cảm, chính trị
3. Không yêu cầu tư vấn cá nhân cụ thể
4. Không spam, không quá dài

Nếu không phù hợp, trả về: "VIOLATION: [lý do]"
Nếu phù hợp, trả về: "SAFE"
"""
        
        try:
            response = call_llm_full(prompt, max_tokens=100, temperature=0.1)
            return response.strip()
        except Exception as e:
            print(f"[Guardrails] Policy check failed: {e}")
            return "SAFE"

    def extract_law_from_history(self, messages):
        # Đơn giản: tìm luật gần nhất trong messages
        for msg in reversed(messages):
            if msg.get('role') == 'user' and 'luật' in msg.get('content', '').lower():
                return msg['content']
        return None

    def validate_input(self, question, messages=None):
        # Nếu có messages, kiểm tra context
        if messages:
            last_law = self.extract_law_from_history(messages)
            if last_law and self.is_ambiguous(question):
                # Nếu context đã rõ, không cần clarification
                return {"is_safe": True, "need_clarification": False}
        # Nếu không có context, kiểm tra mơ hồ như cũ
        if self.is_ambiguous(question):
            return {
                "is_safe": True,
                "need_clarification": True,
                "clarification_message": "Bạn vui lòng nói rõ văn bản pháp luật hoặc tên luật (ví dụ: Điều 11 Luật Cư trú 2020, hoặc Điều 11 của Nghị định số ...) để tôi có thể trả lời chính xác."
            }
        return {"is_safe": True, "need_clarification": False}

    def validate_output(self, text: str) -> Dict:
        """Kiểm tra output từ LLM"""
        start_time = time.time()
        
        result = {
            "is_safe": True,
            "safety_level": SafetyLevel.SAFE,
            "block_reason": None,
            "warnings": [],
            "processing_time": 0,
            "layers_passed": [],
            "need_clarification": False,
            "clarification_message": None
        }
        
        # Lớp 1: Rule-based check
        layer1_level, violations, layer1_details = self.layer1_rule_based_check(text)
        result["layers_passed"].append("layer1_rule_based")
        
        if layer1_level == SafetyLevel.BLOCKED:
            result["is_safe"] = False
            result["safety_level"] = SafetyLevel.BLOCKED
            result["block_reason"] = f"Output vi phạm quy tắc: {violations}"
            result["processing_time"] = time.time() - start_time
            return result
        elif layer1_level == SafetyLevel.WARNING:
            result["warnings"].append(f"Output cảnh báo rule-based: {violations}")
        
        # Lớp 2: OpenAI Moderation (ưu tiên cho output)
        layer2_level, layer2_details = self.layer2_openai_moderation(text)
        result["layers_passed"].append("layer2_openai_moderation")
        
        if layer2_level == SafetyLevel.BLOCKED:
            result["is_safe"] = False
            result["safety_level"] = SafetyLevel.BLOCKED
            result["block_reason"] = f"Output OpenAI Moderation: {layer2_details.get('categories', [])}"
        elif layer2_level == SafetyLevel.WARNING:
            result["warnings"].append(f"Output OpenAI cảnh báo: {layer2_details.get('categories', [])}")
        
        # Lớp 3: Policy guardrails
        policy_result = self.layer3_policy_guardrails(text, is_output=True)
        result["layers_passed"].append("layer3_policy")
        
        if "VIOLATION:" in policy_result:
            result["is_safe"] = False
            result["safety_level"] = SafetyLevel.BLOCKED
            result["block_reason"] = f"Output vi phạm chính sách: {policy_result}"
        
        result["processing_time"] = time.time() - start_time
        
        # Log kết quả
        self.log_validation_result("OUTPUT", text, result)
        
        # Kiểm tra mơ hồ
        if self.is_ambiguous(text):
            result["need_clarification"] = True
            result["clarification_message"] = "Bạn vui lòng nói rõ văn bản pháp luật hoặc tên luật (ví dụ: Điều 11 Luật Cư trú 2020, hoặc Điều 11 của Nghị định số ...) để tôi có thể trả lời chính xác."
        
        return result

    def log_validation_result(self, validation_type: str, text: str, result: Dict):
        """Lớp 4: Logging + Fallback"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": validation_type,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_safe": result["is_safe"],
            "safety_level": result["safety_level"].value,
            "block_reason": result["block_reason"],
            "warnings": result["warnings"],
            "processing_time": result["processing_time"],
            "layers_passed": result["layers_passed"],
            "need_clarification": result["need_clarification"],
            "clarification_message": result["clarification_message"]
        }
        
        print(f"[Guardrails {validation_type}] {json.dumps(log_entry, ensure_ascii=False)}")
        
        # TODO: Lưu vào database/file log để audit sau này
        # self.save_log_to_database(log_entry)

    def get_fallback_message(self, block_reason: str) -> str:
        """Trả về message chuẩn khi bị block"""
        return "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam."

    def is_ambiguous(self, text: str) -> bool:
        # Implementation of is_ambiguous method
        # This is a placeholder and should be implemented based on your specific requirements
        return False

    def is_safe(self, text: str) -> bool:
        # Implementation of is_safe method
        # This is a placeholder and should be implemented based on your specific requirements
        return True 