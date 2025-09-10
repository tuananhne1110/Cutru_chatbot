import json
import re
from typing import List
from ..llm.bedrock_llm import BedrockLLM
from ..utils.logger_utils import get_logger
from ..utils.config_utils import BaseConfig
from ..utils.llm_utils import TextChatMessage

logger = get_logger(__name__)


class QueryRoute:
    
    def __init__(self, global_config : BaseConfig):
        self.bedrock_llm = BedrockLLM(global_config= global_config)

    def query_route(self, question):
        prompt_route: List[TextChatMessage] = [
            {
                "role": "system", 
                "content": """
                    Bạn là một hệ thống định tuyến truy vấn thông minh và chính xác, bạn sẽ được cung cấp một câu hỏi. Nhiệm vụ của bạn là phân tích cẩn thận một yêu cầu của người dùng, sau đó xác định xem yêu cầu đó có liên quan đến bất kỳ lĩnh vực chuyên môn nào được liệt kê dưới đây hay không. Đối với mỗi lĩnh vực, bạn phải trả về giá trị boolean (true hoặc false) để chỉ ra sự liên quan.
                    Các lĩnh vực chuyên môn mà bạn cần xem xét:
                    - **procedure**: Thủ tục hành chính Là quy trình cụ thể để công dân hoặc tổ chức thực hiện quyền, nghĩa vụ được quy định trong luật, với vai trò Là cách thức thực tế để triển khai luật, có hướng dẫn chi tiết về hồ sơ, biểu mẫu, thời gian, cơ quan giải quyết
                    - **legal**: là văn bản pháp luật quy định các nguyên tắc, quyền và nghĩa vụ liên quan đến nơi cư trú của công dân Việt Nam, với vai trò Là đưa ra quy định chung, nguyên tắc, quyền - nghĩa vụ, và cơ sở pháp lý cho việc cư trú của công dân.
                    - **general**: là những câu hỏi không liên quan gì đến các lĩnh vực trên,thường là các câu hỏi giao tiếp đơn giản, chào hỏi, cảm ơn, giới thiệu,... hoặc những nội dung không liên quan đến cư trú.

                    # Trả lời dưới dạng **JSON thuần** (pure JSON), không giải thích, không chú thích, không kèm văn bản ngoài. Đặt toàn bộ kết quả trong ba dấu nháy ngược (```).
                    Đối tượng JSON phải tuân thủ cấu trúc sau:
                    ```json
                    {
                    "procedure": <boolean>,
                    "legal": <boolean>,
                    "general": <boolean>
                    }
                """
            },
            {
                "role": "user", 
                "content": f"""
                    Nhiệm vụ của bạn là phân tích...
                    Câu hỏi người dùng:
                    \"\"\"{question}\"\"\"
                    Assistant:
                    ```json
                    {{
                    "procedure": "Điền kết quả phân loại vào đây",
                    "legal": "Điền kết quả phân loại vào đây",
                    "general": "Điền kết quả phân loại vào đây"
                    }}
                """
            },
        ]

        response_text, metadata, cached = self.bedrock_llm.infer(messages=prompt_route)

        # Trích xuất JSON từ bên trong dấu ``` nếu có
        match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
        if match:
            json_text = match.group(1).strip()
        else:
            json_text = response_text.strip()

        response = json.loads(json_text)
        total_token = metadata['prompt_tokens'] + metadata['completion_tokens']
        return response, total_token

# # run: python -m langgraph_rag.prompts.query_route
# if __name__ == "__main__":
#     query_route = QueryRoute(global_config=BaseConfig())

#     response = query_route.query_route(question="Chỗ nào không được phép đăng ký tạm trú mới?")

#     print("📨 Response:", response)


