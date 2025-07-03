import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None
    relevance_score: Optional[float] = None

class ContextManager:
    """
    Quản lý context hội thoại với các tính năng:
    - Giới hạn số lượt đối thoại
    - Tóm tắt lịch sử khi quá dài
    - Ưu tiên những lượt đối thoại có liên quan
    - Tối ưu prompt cho LLM
    """
    
    def __init__(self, max_turns: int = 5, max_tokens: int = 2000):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        
    def process_conversation_history(self, 
                                   messages: List[Dict], 
                                   current_question: str) -> Tuple[str, List[ConversationTurn]]:
        """
        Xử lý lịch sử hội thoại và tạo context tối ưu
        
        Args:
            messages: Danh sách messages từ request
            current_question: Câu hỏi hiện tại
            
        Returns:
            Tuple[str, List[ConversationTurn]]: (context_string, processed_turns)
        """
        if not messages:
            return "", []
        
        # Chuyển đổi messages thành ConversationTurn
        turns = []
        for msg in messages:
            if msg.get('role') in ['user', 'assistant']:
                turns.append(ConversationTurn(
                    role=msg['role'],
                    content=msg['content'],
                    timestamp=msg.get('timestamp')
                ))
        
        # Tính relevance score cho từng turn
        self._calculate_relevance_scores(turns, current_question)
        
        # Lọc và sắp xếp turns theo relevance
        relevant_turns = self._filter_relevant_turns(turns)
        
        # Tạo context string
        context_string = self._create_context_string(relevant_turns, current_question)
        
        # Log để debug
        logger.info(f"Context processing: {len(messages)} original messages -> {len(relevant_turns)} relevant turns")
        logger.info(f"Context length: {len(context_string)} characters")
        
        return context_string, relevant_turns
    
    def _calculate_relevance_scores(self, turns: List[ConversationTurn], current_question: str):
        """Tính điểm relevance cho từng turn dựa trên câu hỏi hiện tại"""
        current_keywords = self._extract_keywords(current_question.lower())
        
        for turn in turns:
            if turn.role == 'user':
                turn_keywords = self._extract_keywords(turn.content.lower())
                # Tính similarity đơn giản bằng số từ chung
                common_keywords = current_keywords.intersection(turn_keywords)
                turn.relevance_score = len(common_keywords) / max(len(current_keywords), 1)
            else:
                # Assistant messages có relevance thấp hơn
                turn.relevance_score = 0.3
    
    def _extract_keywords(self, text: str) -> set:
        """Trích xuất keywords từ text"""
        # Loại bỏ stopwords và ký tự đặc biệt
        stopwords = {'là', 'và', 'của', 'cho', 'với', 'có', 'không', 'như', 'được', 'trong', 'khi', 'đã', 'này', 'đó', 'thì', 'lại', 'nên', 'rồi', 'nữa', 'vẫn', 'đang', 'tôi', 'bạn', 'mình', 'em', 'anh', 'chị'}
        
        # Tách từ và lọc
        words = re.findall(r'\b\w+\b', text)
        keywords = {word for word in words if len(word) > 2 and word not in stopwords}
        
        return keywords
    
    def _filter_relevant_turns(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        """Lọc và sắp xếp turns theo relevance và giới hạn"""
        # Sắp xếp theo relevance score (cao nhất trước)
        sorted_turns = sorted(turns, key=lambda x: x.relevance_score or 0, reverse=True)
        
        # Lấy turns gần nhất nếu có ít hơn max_turns
        if len(sorted_turns) <= self.max_turns:
            return sorted_turns
        
        # Nếu có nhiều turns, ưu tiên relevance cao và gần đây
        recent_turns = turns[-self.max_turns:]  # Lấy max_turns gần nhất
        high_relevance_turns = [t for t in sorted_turns[:self.max_turns//2] if t.relevance_score and t.relevance_score > 0.3]
        
        # Kết hợp: ưu tiên relevance cao + một số turns gần đây
        combined_turns = list(set(high_relevance_turns + recent_turns))
        
        # Sắp xếp lại theo thứ tự thời gian
        combined_turns.sort(key=lambda x: turns.index(x))
        
        return combined_turns[:self.max_turns]
    
    def _create_context_string(self, turns: List[ConversationTurn], current_question: str) -> str:
        """Tạo context string từ các turns đã lọc"""
        if not turns:
            return ""
        
        # Nếu có ít turns, sử dụng trực tiếp
        if len(turns) <= 3:
            context_parts = ["LỊCH SỬ HỘI THOẠI:"]
            for turn in turns:
                role_name = "Người dùng" if turn.role == 'user' else "Trợ lý"
                context_parts.append(f"{role_name}: {turn.content}")
            return "\n".join(context_parts)
        
        # Nếu có nhiều turns, tạo tóm tắt
        return self._create_summarized_context(turns, current_question)
    
    def _create_summarized_context(self, turns: List[ConversationTurn], current_question: str) -> str:
        """Tạo context có tóm tắt cho cuộc hội thoại dài"""
        # Tách user và assistant messages
        user_messages = [t.content for t in turns if t.role == 'user']
        assistant_messages = [t.content for t in turns if t.role == 'assistant']
        
        # Tạo tóm tắt
        summary_parts = ["LỊCH SỬ HỘI THOẠI:"]
        
        if len(user_messages) > 3:
            # Tóm tắt các câu hỏi trước
            summary_parts.append(f"[TÓM TẮT: Người dùng đã hỏi {len(user_messages)} câu hỏi]")
            # Giữ lại 2 câu hỏi gần nhất
            summary_parts.extend([f"Người dùng: {msg}" for msg in user_messages[-2:]])
        else:
            summary_parts.extend([f"Người dùng: {msg}" for msg in user_messages])
        
        # Thêm assistant responses gần nhất
        if assistant_messages:
            summary_parts.extend([f"Trợ lý: {msg}" for msg in assistant_messages[-2:]])
        
        return "\n".join(summary_parts)
    
    def create_optimized_prompt(self, 
                              base_prompt: str, 
                              context_string: str, 
                              current_question: str) -> str:
        """
        Tạo prompt tối ưu với cấu trúc rõ ràng
        
        Args:
            base_prompt: Prompt cơ bản từ prompt manager
            context_string: Context string đã xử lý
            current_question: Câu hỏi hiện tại
            
        Returns:
            str: Prompt tối ưu
        """
        if not context_string:
            return base_prompt
        
        # Tìm vị trí để chèn context
        if "VAI TRÒ VÀ TRÁCH NHIỆM:" in base_prompt:
            # Chèn sau phần system prompt
            system_end = base_prompt.find("CÂU HỎI:")
            if system_end != -1:
                optimized_prompt = (
                    base_prompt[:system_end] + 
                    f"\n\n{context_string}\n" +
                    base_prompt[system_end:]
                )
                return optimized_prompt
        
        # Fallback: thêm vào đầu
        return f"{base_prompt}\n\n{context_string}\n\nCÂU HỎI HIỆN TẠI: {current_question}"
    
    def log_context_processing(self, 
                             original_messages: List[Dict], 
                             processed_turns: List[ConversationTurn],
                             context_string: str,
                             current_question: str):
        """Log quá trình xử lý context để debug"""
        logger.info("=== CONTEXT PROCESSING LOG ===")
        logger.info(f"Original messages: {len(original_messages)}")
        logger.info(f"Processed turns: {len(processed_turns)}")
        logger.info(f"Context length: {len(context_string)} chars")
        logger.info(f"Current question: {current_question}")
        
        if processed_turns:
            logger.info("Relevance scores:")
            for i, turn in enumerate(processed_turns):
                logger.info(f"  Turn {i+1} ({turn.role}): {turn.relevance_score:.2f} - {turn.content[:50]}...")

# Singleton instance
context_manager = ContextManager() 