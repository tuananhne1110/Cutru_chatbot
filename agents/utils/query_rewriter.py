import logging
from typing import List, Dict, Optional
from agents.utils.context_manager import context_manager
from agents.utils.intent_detector import IntentType

logger = logging.getLogger(__name__)

class QueryRewriter:
    """
    Query Rewriter đơn giản để làm rõ câu hỏi dựa trên context
    """
    
    def __init__(self):
        self.context_manager = context_manager
    
    async def rewrite_query_with_context(self, 
                                       current_question: str, 
                                       messages: List,
                                       llm_client=None,
                                       intent: Optional[IntentType]=None) -> str:
        """
        Rewrite câu hỏi để làm rõ nghĩa dựa trên context (chỉ khi cần thiết)
        """
        try:
            # Kiểm tra xem câu hỏi có cần rewrite không
            if self._is_question_clear(current_question):
                logger.info(f"[QueryRewriter] Question is clear, no rewrite needed: {current_question}")
                return current_question
            
            # Lấy lịch sử gần nhất cho LLM
            history_context = self.context_manager.get_recent_history_for_llm(
                messages, current_question
            )
            
            # Nếu không có context hoặc LLM client, trả về câu hỏi gốc
            if not llm_client or not history_context.strip():
                logger.info(f"[QueryRewriter] No LLM client or context, returning original: {current_question}")
                return current_question
            
            # Tạo prompt đơn giản để làm rõ câu hỏi
            prompt = self._create_simple_rewrite_prompt(history_context, current_question)
            
            # Gọi LLM để rewrite
            rewritten_query = await self._call_llm_for_rewrite(prompt, llm_client)
            
            # Nếu rewrite thất bại hoặc không hợp lý, trả về câu hỏi gốc
            if not rewritten_query or len(rewritten_query.strip()) == 0:
                logger.info(f"[QueryRewriter] Empty rewrite result, returning original: {current_question}")
                return current_question
            
            # Log kết quả
            logger.info(f"[QueryRewriter] Original question: {current_question}")
            logger.info(f"[QueryRewriter] Rewritten question: {rewritten_query}")
            
            return rewritten_query
            
        except Exception as e:
            logger.error(f"[QueryRewriter] Error in query rewrite: {e}")
            logger.info(f"[QueryRewriter] Exception fallback - Original question: {current_question}")
            return current_question
    
    def _is_question_clear(self, question: str) -> bool:
        """
        Kiểm tra xem câu hỏi có cần rewrite không dựa trên độ dài và độ rõ ràng
        """
        question = question.strip()
        words = question.split()
        
        # Câu hỏi quá ngắn thường thiếu context
        if len(words) < 6:
            logger.info(f"[QueryRewriter] Short question ({len(words)} words), likely needs context")
            return False
            
        # Kiểm tra độ rõ ràng dựa trên từ khóa tham chiếu/mơ hồ
        unclear_patterns = [
            "nào", "này", "đó", "kia", "ấy", "nữa", "còn", 
            "thế", "sao", "vậy", "thì", "như"
        ]
        
        question_lower = question.lower()
        unclear_count = sum(1 for pattern in unclear_patterns if pattern in question_lower)
        
        # Nếu có quá nhiều từ tham chiếu/mơ hồ thì có thể cần context
        if unclear_count >= 2:
            logger.info(f"[QueryRewriter] High unclear word count ({unclear_count}), likely needs context")
            return False
                
        return True
    
    def _create_simple_rewrite_prompt(self, history_context: str, question: str) -> str:
        """
        Tạo prompt đơn giản để làm rõ câu hỏi
        """
        return f"""
Nhiệm vụ: Viết lại câu hỏi để nó rõ ràng và tự đứng được, không phụ thuộc vào ngữ cảnh.

Phân tích:
1. Xem xét lịch sử hội thoại để hiểu ngữ cảnh
2. Xác định những thông tin thiếu trong câu hỏi hiện tại
3. Bổ sung thông tin cần thiết từ lịch sử để câu hỏi hoàn chỉnh

Yêu cầu:
- CHỈ viết lại câu hỏi, không trả lời
- Giữ nguyên ý định của người hỏi
- Đảm bảo câu hỏi sau khi viết lại có thể hiểu được mà không cần context
- Nếu câu hỏi đã đủ rõ ràng, giữ nguyên

Lịch sử hội thoại:
{history_context}

Câu hỏi cần làm rõ: {question}

Câu hỏi đã được làm rõ:"""
    
    async def _call_llm_for_rewrite(self, prompt: str, llm_client) -> str:
        try:
            logger.info(f"[QueryRewriter] Calling LLM for rewrite...")
            response = await llm_client.agenerate([prompt])
            if response and response.generations:
                raw_response = response.generations[0][0].text.strip()
                logger.info(f"[QueryRewriter] Raw LLM response: {raw_response}")
                
                rewritten_query = self._clean_llm_response(raw_response)
                logger.info(f"[QueryRewriter] Cleaned response: {rewritten_query}")
                
                return rewritten_query
            else:
                logger.warning("[QueryRewriter] Empty response from LLM")
                return ""
        except Exception as e:
            logger.error(f"[QueryRewriter] Error calling LLM for rewrite: {e}")
            return ""
    
    def _clean_llm_response(self, response: str) -> str:
        """
        Làm sạch response từ LLM
        """
        response = response.strip()
        
        # Remove quotes
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1].strip()
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1].strip()
        
        # Remove unwanted prefixes
        unwanted_prefixes = [
            "Câu hỏi được viết lại:",
            "Câu hỏi đã được rewrite:",
            "Câu hỏi mới:",
            "Câu hỏi:",
            "Rewrite:",
            "Đã rewrite:",
            "Viết lại:"
        ]
        
        for prefix in unwanted_prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
                break
        
        return response

# Singleton instance
query_rewriter = QueryRewriter()