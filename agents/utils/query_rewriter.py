import logging
from typing import List, Dict, Optional
from agents.utils.context_manager import context_manager

logger = logging.getLogger(__name__)

class QueryRewriter:
    """
    Query Rewriter sử dụng LLM để tự động xử lý follow-up questions
    """
    
    def __init__(self):
        self.context_manager = context_manager
        
    async def rewrite_query_with_context(self, 
                                       current_question: str, 
                                       messages: List,
                                       llm_client=None) -> str:
        """
        Rewrite câu hỏi sử dụng LLM dựa trên context
        """
        try:
            # Lấy lịch sử gần nhất cho LLM
            history_context = self.context_manager.get_recent_history_for_llm(
                messages, current_question
            )
            
            # Tạo prompt cho LLM
            prompt = self.context_manager.create_query_rewrite_prompt(history_context)
                        
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
    
    async def _call_llm_for_rewrite(self, prompt: str, llm_client) -> str:
        """
        Gọi LLM để rewrite câu hỏi
        """
        try:
            # Gọi LLM với prompt
            response = await llm_client.agenerate([prompt])
            
            if response and response.generations:
                rewritten_query = response.generations[0][0].text.strip()
                
                # Clean up response - chỉ lấy câu hỏi, không lấy giải thích
                rewritten_query = self._clean_llm_response(rewritten_query)
                
                return rewritten_query
            else:
                logger.warning("Empty response from LLM")
                return ""
                
        except Exception as e:
            logger.error(f"Error calling LLM for rewrite: {e}")
            return ""

    def _clean_llm_response(self, response: str) -> str:
        """
        Clean up response từ LLM
        Loại bỏ các phần không cần thiết, chỉ giữ lại câu hỏi
        """
        # Loại bỏ các prefix/suffix không cần thiết
        response = response.strip()
        
        # Loại bỏ dấu ngoặc kép nếu có
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # Loại bỏ các từ khóa không cần thiết
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
        """
        Template prompt cho query rewrite
        """
        return """
Hãy dựa vào toàn bộ lịch sử hội thoại và câu hỏi mới của user, nếu câu hỏi mới không đủ rõ/ngắn/gãy ý, hãy tự động diễn giải lại thành một câu hỏi hoàn chỉnh, đầy đủ thông tin từ lịch sử. Nếu đã rõ thì giữ nguyên.

Lưu ý:
- Nếu câu hỏi ngắn, thiếu context, hãy bổ sung thông tin từ lịch sử
- Nếu câu hỏi dùng từ "cái nào", "nữa", "còn", "thì sao", hãy hiểu ngầm và diễn giải rõ ràng
- Nếu câu hỏi đã rõ ràng, đầy đủ, thì giữ nguyên
- Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích

{history_context}

Hãy trả lời chỉ với câu hỏi đã được rewrite (hoặc giữ nguyên nếu đã rõ ràng), không thêm giải thích.
"""

# Singleton instance
query_rewriter = QueryRewriter() 