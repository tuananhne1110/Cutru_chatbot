import logging
from typing import List, Dict, Optional
from agents.utils.context_manager import context_manager
from agents.utils.intent_detector import IntentType
from enum import Enum

logger = logging.getLogger(__name__)

class RewriteStrategy(Enum):
    SUB_QUERY = "Sub-Query"
    MULTI_QUERY = "Multi-Query"
    STANDARD = "Standard"

class QueryRewriter:
    """
    Query Rewriter sử dụng LLM để tự động xử lý follow-up questions
    """
    
    def __init__(self):
        self.context_manager = context_manager
        self._setup_intent_strategy_mapping()
    
    def _setup_intent_strategy_mapping(self):
        # LAW không dùng HyDE, dùng STANDARD
        self.intent_strategy_mapping = {
            IntentType.LAW: RewriteStrategy.STANDARD,
            IntentType.PROCEDURE: RewriteStrategy.SUB_QUERY,
            IntentType.FORM: RewriteStrategy.MULTI_QUERY,
            IntentType.TERM: RewriteStrategy.STANDARD,
            IntentType.TEMPLATE: RewriteStrategy.MULTI_QUERY,
            IntentType.GENERAL: RewriteStrategy.MULTI_QUERY,
        }
    
    async def rewrite_query_with_context(self, 
                                       current_question: str, 
                                       messages: List,
                                       llm_client=None,
                                       intent: Optional[IntentType]=None) -> str:
        """
        Rewrite câu hỏi sử dụng LLM dựa trên context và intent
        """
        try:
            # Lấy lịch sử gần nhất cho LLM
            history_context = self.context_manager.get_recent_history_for_llm(
                messages, current_question
            )
            # Chọn strategy dựa vào intent
            if intent is None:
                # fallback: GENERAL
                strategy = RewriteStrategy.STANDARD
            else:
                strategy = self.intent_strategy_mapping.get(intent, RewriteStrategy.STANDARD)
            prompt = self._create_strategy_specific_prompt(strategy, history_context, current_question)
            # Nếu không có LLM client, trả về câu hỏi gốc
            if not llm_client:
                logger.warning("No LLM client provided, returning original question")
                return current_question
            # Gọi LLM để rewrite
            rewritten_query = await self._call_llm_for_rewrite(prompt, llm_client)
            return rewritten_query
        except Exception as e:
            logger.error(f"Error in query rewrite: {e}")
            # Fallback: trả về câu hỏi gốc
            return current_question
    
    def _create_strategy_specific_prompt(self, strategy: RewriteStrategy, history_context: str, question: str) -> str:
        base_prompt = f"""
Lịch sử hội thoại:
{history_context}

Câu hỏi hiện tại: {question}

"""
        if strategy == RewriteStrategy.SUB_QUERY:
            return base_prompt + """
Chiến lược Sub-Query:
Hãy chia nhỏ câu hỏi thành các phần riêng biệt để tránh hiểu sai.
Tập trung vào từng điều kiện, bước thực hiện cụ thể.
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.
"""
        elif strategy == RewriteStrategy.MULTI_QUERY:
            return base_prompt + """
Chiến lược Multi-Query:
Hãy tạo nhiều biến thể của câu hỏi để tăng khả năng tìm kiếm.
Với FORM: thử các tên gọi khác nhau của biểu mẫu
Với GENERAL: mở rộng nhiều hướng tìm tài liệu phù hợp
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.
"""
        else:  # STANDARD
            return base_prompt + """
Chiến lược Standard:
Hãy diễn giải lại câu hỏi cho rõ ràng hơn nếu cần.
Nếu câu hỏi đã rõ ràng thì giữ nguyên.
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.
"""
    
    async def _call_llm_for_rewrite(self, prompt: str, llm_client) -> str:
        try:
            response = await llm_client.agenerate([prompt])
            if response and response.generations:
                rewritten_query = response.generations[0][0].text.strip()
                rewritten_query = self._clean_llm_response(rewritten_query)
                return rewritten_query
            else:
                logger.warning("Empty response from LLM")
                return ""
        except Exception as e:
            logger.error(f"Error calling LLM for rewrite: {e}")
            return ""
    def _clean_llm_response(self, response: str) -> str:
        response = response.strip()
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        unwanted_prefixes = [
            "Câu hỏi đã được rewrite:",
            "Câu hỏi mới:",
            "Câu hỏi:",
            "Rewrite:",
            "Đã rewrite:"
        ]
        for prefix in unwanted_prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
                break
        return response
    def create_rewrite_prompt_template(self) -> str:
        return """
Hãy dựa vào toàn bộ lịch sử hội thoại và câu hỏi mới của user, nếu câu hỏi mới không đủ rõ/ngắn/gãy ý, hãy tự động diễn giải lại thành một câu hỏi hoàn chỉnh, đầy đủ thông tin từ lịch sử. Nếu đã rõ thì giữ nguyên.

Lưu ý:
- Nếu câu hỏi ngắn, thiếu context, hãy bổ sung thông tin từ lịch sử
- Nếu câu hỏi dùng từ \"cái nào\", \"nữa\", \"còn\", \"thì sao\", hãy hiểu ngầm và diễn giải rõ ràng
- Nếu câu hỏi đã rõ ràng, đầy đủ, thì giữ nguyên
- Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích

{history_context}

Hãy trả lời chỉ với câu hỏi đã được rewrite (hoặc giữ nguyên nếu đã rõ ràng), không thêm giải thích.
"""

# Singleton instance
query_rewriter = QueryRewriter() 