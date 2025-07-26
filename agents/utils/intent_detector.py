from dataclasses import dataclass
import json
import re
import logging
from typing import Any, Dict, List, Tuple
from enum import Enum
import boto3
from langfuse.decorators import observe
import yaml
# from .prompt_templates import prompt_templates, CategoryType

logger = logging.getLogger(__name__)

# =========================== CONFIG ============================
class IntentType(Enum):
    """Các loại intent của câu hỏi"""
    LAW = "law"           # Tra cứu luật pháp
    FORM = "form"         # Hướng dẫn điền biểu mẫu
    TERM = "term"         # Tra cứu thuật ngữ, định nghĩa
    PROCEDURE = "procedure"  # Thủ tục hành chính
    TEMPLATE = "template"     # Biểu mẫu gốc (template)
    GENERAL = "general"   # câu hỏi chung

COLLECTION_MAP = {
    "procedure": "thủ tục hành chính về lĩnh vực cư trú",
    "law": "văn bản pháp lý về lĩnh vực cư trú",
    "form": "hướng dẫn điền giấy tờ/biểu mẫu về lĩnh vực cư trú",
    "term": "thuật ngữ/định nghĩa về lĩnh vực cư trú",
    "template": "biểu mẫu gốc được dùng làm nền để trích xuất dữ liệu tự động hoặc điền thông tin trong lĩnh vực cư trú",
    "general": "các tình huống giao tiếp thông thường hoặc câu hỏi không liên quan đến cư trú" 
}

COLLECTION_DESCRIPTIONS = {
    IntentType.PROCEDURE: "Tra cứu thủ tục hành chính trong lĩnh vực cư trú: tên thủ tục, trình tự, thành phần hồ sơ, cách thực hiện.",
    IntentType.LAW: "Tra cứu văn bản pháp lý, căn cứ pháp lý, chương điều khoản, mục liên quan đến cư trú,",
    IntentType.FORM: "Hướng dẫn điền biểu mẫu, giấy tờ dùng trong lĩnh vực cư trú.",
    IntentType.TERM: "Tìm kiếm định nghĩa, thuật ngữ pháp lý trong lĩnh vực cư trú.",
    IntentType.TEMPLATE: "Biểu mẫu hành chính chính thức dùng để công dân hoặc người nước ngoài khai báo, đăng ký, thay đổi thông tin cư trú. Bao gồm các tờ khai như: Phiếu khai báo tạm trú, Tờ khai thay đổi thông tin cư trú,... thường được sử dụng trong các thủ tục hành chính liên quan đến cư trú.",
    IntentType.GENERAL: "Trả lời các câu hỏi giao tiếp đơn giản, chào hỏi, cảm ơn, giới thiệu,... hoặc những nội dung không liên quan đến cư trú."
}

MAPPING_IntentType = {
    "procedure": IntentType.PROCEDURE,
    "law": IntentType.LAW,
    "form": IntentType.FORM,
    "term": IntentType.TERM,
    "template": IntentType.TEMPLATE,
    "general": IntentType.GENERAL,

}

ROUTER_SYSTEM_PROMPT = """
Bạn là một trợ lý thông minh có khả năng định tuyến truy vấn người dùng đến MỘT hoặc NHIỀU cơ sở dữ liệu chuyên biệt.
Hiện có 6 cơ sở dữ liệu mà bạn có thể sử dụng:
1. **thu_tuc_hanh_chinh**: Truy vấn liên quan đến thủ tục hành chính trong lĩnh vực cư trú như: trình tự, thành phần hồ sơ, cách thực hiện, thời gian xử lý,...
2. **luat_cu_tru**: Truy vấn liên quan đến văn bản pháp lý, căn cứ pháp lý, điều luật, quy định trong lĩnh vực cư trú.
3. **giay_to_cu_tru**: Truy vấn liên quan đến giấy tờ, biểu mẫu, tờ khai, đơn, phiếu đề nghị,... dùng trong lĩnh vực cư trú.
4. **thuat_ngu_cu_tru**: Truy vấn cần định nghĩa, giải thích các thuật ngữ, khái niệm chuyên ngành liên quan đến cư trú.
6. **giao_tiep_chung**: Truy vấn không liên quan đến cư trú, bao gồm các câu hỏi chào hỏi, cảm ơn, hỏi vu vơ, giới thiệu bản thân,... hoặc những nội dung giao tiếp hàng ngày.
## Chú ý: 
    - Với mỗi truy vấn, bạn **cần liệt kê đầy đủ tất cả các cơ sở dữ liệu liên quan**, không bỏ sót (có thể từ 1 đến nhiều).
    - Nếu truy vấn thuộc về nhiều lĩnh vực cùng lúc, trả về nhiều cơ sở dữ liệu.

"""

def load_intent_config(yaml_path="config/config.yaml"):
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get("intent", {})
    except Exception:
        return {}

intent_cfg = load_intent_config()
ROUTER_SYSTEM_PROMPT = intent_cfg.get("router_system_prompt", ROUTER_SYSTEM_PROMPT)
KEYWORDS = intent_cfg.get("keywords", {})


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {"json": self.input_schema}
            }
        }


TOOL_CONFIGS: List[ToolSpec] = [
    ToolSpec(
        name=collection.value,
        description=COLLECTION_DESCRIPTIONS[collection],
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f"Truy vấn tìm kiếm liên quan đến {COLLECTION_MAP[collection.value]}."
                }
            },
            "required": ["query"]
        }
    )
    for collection in IntentType
]


class TextUtils:
    """Tiện ích xử lý văn bản"""
    
    @staticmethod
    def contains_special_characters(text: str) -> bool:
        """Kiểm tra xem chuỗi có chứa các ký tự đặc biệt (escape, unicode, điều khiển)."""
        pattern = r'(\\[ntr"\'\\])|(\\u[0-9a-fA-F]{4})'
        return bool(re.search(pattern, text))

    @staticmethod
    def decode_tool_output(content: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Giải mã nội dung từ assistant trả về ở dạng text chứa JSON bị escape nhiều lần.
        
        Args:
            content: List chứa dict với key "text" (kiểu string).

        Returns:
            Danh sách dict đã parse từ JSON thực sự.
        """
        try:
            raw_text = content[0]["text"]
            json_str_list = json.loads(raw_text)
            decoded = [json.loads(item) for item in json_str_list]
            return decoded
        except Exception as e:
            print(f"Lỗi khi giải mã nội dung: {e}")
            return []

    @staticmethod
    def decode_text_json(text_value: str) -> List[Dict[str, Any]]:
        """
        Giải mã chuỗi text JSON bị escape nhiều lần.
        
        Args:
            text_value: Chuỗi JSON dạng list chứa các string bị escape nhiều lần.

        Returns:
            List các dict giải mã được.
        """
        try:
            raw_list = json.loads(text_value)
            result = [json.loads(item) for item in raw_list]
            return result
        except Exception as e:
            print(f"❌ Lỗi khi decode text JSON: {e}")
            return []



class IntentDetector:
    def __init__(self, 
                service_name='bedrock-runtime', 
                model_id = "us.meta.llama4-scout-17b-instruct-v1:0", 
                region_name = "us-east-1"):
        self.bedrock_runtime_client = boto3.client(service_name=service_name, region_name = region_name)
        self.model_id = model_id
    
    @observe()
    def detect_intent(self, query: str, trace_id: str = None) -> List[Tuple[IntentType, str]]:
        messages = [{"role": "user", "content": [{"text": query}]}]
        tool_config = {"tools": [tool.to_dict() for tool in TOOL_CONFIGS]}
        list_intent_type: List[Tuple[IntentType, str]] = []
        try:
            response = self.bedrock_runtime_client.converse(
                modelId=self.model_id,
                messages=messages,
                system=[{"text": ROUTER_SYSTEM_PROMPT}],
                toolConfig=tool_config
            )

            output = response["output"]["message"]["content"]
            print(response)
            for item in output:
                # Trường hợp toolUse (định tuyến trực tiếp)
                if "toolUse" in item:
                    tool_name = item['toolUse']['name']
                    new_query = item['toolUse']['input'].get('query', query)
                    intent = MAPPING_IntentType.get(tool_name, IntentType.GENERAL)
                    list_intent_type.append((intent, new_query))
                    continue

                # Trường hợp trả về dưới dạng text (có thể là JSON)
                if "text" in item and isinstance(item["text"], str):
                    try:
                        tool_results = TextUtils.decode_text_json(item["text"])
                        for tool_result in tool_results:
                            new_query = tool_result['parameters'].get('query', query)
                            tool_name = tool_result.get('name')
                            intent = MAPPING_IntentType.get(tool_name, IntentType.GENERAL)
                            list_intent_type.append((intent, new_query))
                    except (json.JSONDecodeError, KeyError, TypeError):
                        list_intent_type.append((IntentType.GENERAL, query))
                else:
                    list_intent_type.append((IntentType.GENERAL, query))
        except Exception as e:
            return [(IntentType.GENERAL, query)]

        # Loại trùng intent (theo loại intent, giữ lại query đầu tiên cho mỗi intent)
        seen = set()
        unique_intents = []
        for intent, q in list_intent_type:
            if intent not in seen:
                unique_intents.append((intent, q))
                seen.add(intent)

        # Nếu có PROCEDURE thì tự động thêm LAW và FORM nếu chưa có
        has_procedure = any(intent == IntentType.PROCEDURE for intent, _ in unique_intents)
        if has_procedure:
            for extra_intent in [IntentType.LAW, IntentType.FORM]:
                if not any(intent == extra_intent for intent, _ in unique_intents):
                    unique_intents.append((extra_intent, query))

        return unique_intents


    def get_search_collections(self, intents: List[Tuple[IntentType, str]]) -> List[str]:
        list_collections = []
        for intent in intents:
            if intent[0] == IntentType.LAW:
                list_collections.append("legal_chunks")
            elif intent[0] == IntentType.FORM:
                list_collections.append("form_chunks")
            elif intent[0] == IntentType.TERM:
                list_collections.append("term_chunks")
            elif intent[0] == IntentType.PROCEDURE:
                list_collections.append("procedure_chunks")
            elif intent[0] == IntentType.TEMPLATE:
                list_collections.append("template_chunks")
            else :
                list_collections.append("general_chunks")
        return list_collections


intent_detector = IntentDetector(service_name='bedrock-runtime', model_id = "us.meta.llama4-scout-17b-instruct-v1:0")
