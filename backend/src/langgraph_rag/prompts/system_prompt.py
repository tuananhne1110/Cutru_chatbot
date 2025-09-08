from typing import List
from ..llm.bedrock_llm import BedrockLLM
from ..utils.logger_utils import get_logger
from ..utils.config_utils import BaseConfig
from ..utils.llm_utils import TextChatMessage
from .one_shot import TTHC_ONESHOT


logger = get_logger(__name__)


class GenerateAnswer:
        def __init__(self, global_config : BaseConfig):
                self.bedrock_llm = BedrockLLM(global_config= global_config)

        def generate_intent(self, question: str, related_text: str, conversation_history: List[TextChatMessage]):


                prompt: List[TextChatMessage] = [
                        {
                        "role": "system", 
                        "content": f"""\
                        Bạn là một chuyên gia pháp lý, có nhiệm vụ hỗ trợ người dân và cán bộ trong việc tìm hiểu và hướng dẫn các **thủ tục hành chính tại Việt Nam**.
                        Bạn sẽ được cung cấp:

                        Một câu hỏi do người dùng đặt ra (User Question).

                        Một đoạn tài liệu trích xuất từ hệ thống văn bản quy phạm pháp luật hoặc cổng dịch vụ công (Context Documents).

                        Hãy đọc kỹ đoạn trích xuất và **chỉ trả lời dựa trên nội dung tài liệu** được cung cấp. Nếu không có đủ thông tin, hãy trả lời trung thực là **không tìm thấy** hoặc **không rõ**.
                        Hãy trả lời **rõ ràng, chi tiết, chính xác, đúng nội dung văn bản** và đầy đủ căn cứ nếu cần thiết.

                        Tài liệu trích xuất:
                        {related_text}

                        Dựa trên nội dung tài liệu được cung cấp, hãy trả lời câu hỏi trên.  
                        Nếu thông tin trong tài liệu không đủ để trả lời, hãy nói rõ là "Không tìm thấy thông tin trong tài liệu".
                        
                     
                        """
                        },
                        {
                        "role": "user", 
                        "content": f"""
                                Nhiệm vụ của bạn là phân tích
                                Câu hỏi người dùng:
                                \"\"\"{question}\"\"\"
                                Trả lời:
                        """
                        },
                ]

                        #Ví dụ: 

                        #{TTHC_ONESHOT}
                        #LƯU Ý: khi trả lời phải có nguồn trích dẫn và giấy tờ đính kèm nếu có

                messages: List[TextChatMessage] = conversation_history + prompt

                response_text, metadata, cached = self.bedrock_llm.infer(messages=messages)
                total_token = metadata['prompt_tokens'] + metadata['completion_tokens']
                return response_text, total_token


        def generate_general(self, question: str,  conversation_history: List[TextChatMessage]):
                prompt: List[TextChatMessage] = [
                        {
                        "role": "system", 
                        "content": f"""\
                        Bạn là một trợ lý AI thông minh, giàu kiến thức và luôn trả lời rõ ràng, chính xác.

                        Nguyên tắc khi trả lời:
                        1. Hiểu kỹ câu hỏi, nếu câu hỏi mơ hồ thì giả định hợp lý để trả lời.
                        2. Trình bày câu trả lời theo cấu trúc:
                        - Trả lời ngắn gọn, trực tiếp vào trọng tâm.
                        - Nếu cần, giải thích chi tiết và đưa ví dụ minh họa.
                        3. Luôn sử dụng tiếng Việt rõ ràng, dễ hiểu. Tránh từ ngữ mơ hồ.
                        Yêu cầu định dạng đầu ra:
                        - Chỉ trả lời, không lặp lại câu hỏi của người dùng.
                        - Giữ câu trả lời gọn gàng nhưng đầy đủ thông tin cần thiết.
                        """
                        },
                        {
                        "role": "user", 
                        "content": f"""
                                Nhiệm vụ của bạn là trả lời Câu hỏi người dùng:
                                \"\"\"{question}\"\"\"
                                Trả lời:
                        """
                        },
                ]
                messages: List[TextChatMessage] = conversation_history + prompt
                response_text, metadata, cached = self.bedrock_llm.infer(messages=messages)
                total_token = metadata['prompt_tokens'] + metadata['completion_tokens']
                return response_text, total_token


# # run: python -m langgraph_rag.prompts.system_prompt
# if __name__ == "__main__":
#     g_a = GenerateAnswer(global_config=BaseConfig())

#     response = g_a.generate_general(question="Chỗ nào không được phép đăng ký tạm trú mới?")

#     print("📨 Response:", response)


