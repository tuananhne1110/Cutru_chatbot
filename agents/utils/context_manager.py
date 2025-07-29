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
    - Không hardcode patterns, sử dụng LLM để tự động xử lý follow-up questions
    """
    
    def __init__(self, max_turns: int = 20, max_tokens: int = 4000, history_window: int = 5):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.history_window = history_window  # Số lượt gần nhất để truyền vào LLM
        
    def process_conversation_history(self, 
                                   messages: List, 
                                   current_question: str) -> Tuple[str, List[ConversationTurn]]:
        """
        Xử lý lịch sử hội thoại và tạo context tối ưu
        
        Args:
            messages: Danh sách messages từ request (có thể là dict hoặc message objects)
            current_question: Câu hỏi hiện tại
            
        Returns:
            Tuple[str, List[ConversationTurn]]: (context_string, processed_turns)
        """
        if not messages:
            return "", []
        
        # Chuyển đổi messages thành ConversationTurn
        turns = []
        for msg in messages:
            # Handle cả dict và message objects
            if isinstance(msg, dict):
                if msg.get('role') in ['user', 'assistant']:
                    turns.append(ConversationTurn(
                        role=msg['role'],
                        content=msg['content'],
                        timestamp=msg.get('timestamp')
                ))
            else:
                # Handle message objects (HumanMessage, AIMessage, etc.)
                try:
                    if hasattr(msg, 'type') and hasattr(msg, 'content'):
                        role = 'user' if getattr(msg, 'type', None) == 'human' else 'assistant'
                        turns.append(ConversationTurn(
                            role=role,
                            content=msg.content,
                            timestamp=getattr(msg, 'timestamp', None)
                        ))
                    elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                        # Direct role/content attributes
                        turns.append(ConversationTurn(
                            role=msg.role,
                            content=msg.content,
                            timestamp=getattr(msg, 'timestamp', None)
                        ))
                except Exception as e:
                    logger.warning(f"Could not process message: {msg}, error: {e}")
                    continue
        
        # Tính relevance score cho từng turn
        self._calculate_relevance_scores(turns, current_question)
        
        # Lọc và sắp xếp turns theo relevance
        relevant_turns = self._filter_relevant_turns(turns)
        
        # Tạo context string - đơn giản, không hardcode
        context_string = self._create_context_string(relevant_turns, current_question)
        
        # Log để debug
        logger.info(f"Context processing: {len(messages)} original messages -> {len(relevant_turns)} relevant turns")
        logger.info(f"Context length: {len(context_string)} characters")
        logger.info(f"Max turns configured: {self.max_turns}")
        logger.info(f"History window: {self.history_window}")
        
        # Log chi tiết về relevance scores
        if relevant_turns:
            logger.info("Relevance scores for selected turns:")
            for i, turn in enumerate(relevant_turns[-5:]):  # Log 5 turns gần nhất
                logger.info(f"  Turn {i+1} ({turn.role}): {turn.relevance_score:.3f} - {turn.content[:100]}...")
        
        return context_string, relevant_turns
    
    def get_recent_history_for_llm(self, messages: List, current_question: str) -> str:
        """
        Lấy lịch sử gần nhất để truyền vào LLM cho query rewrite
        """
        if not messages:
            return f"Câu hỏi mới: {current_question}"
        
        # Lấy history window gần nhất
        recent_messages = messages[-self.history_window:]
        
        # Tạo format đơn giản cho LLM
        history_parts = []
        for msg in recent_messages:
            # Handle cả dict và message objects
            if isinstance(msg, dict):
                if msg.get('role') in ['user', 'assistant']:
                    role_name = "user" if msg['role'] == 'user' else "assistant"
                    history_parts.append(f"[{role_name}: {msg['content']}]")
            else:
                # Handle message objects
                try:
                    if hasattr(msg, 'type') and hasattr(msg, 'content'):
                        role_name = "user" if getattr(msg, 'type', None) == 'human' else "assistant"
                        history_parts.append(f"[{role_name}: {msg.content}]")
                    elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                        role_name = "user" if msg.role == 'user' else "assistant"
                        history_parts.append(f"[{role_name}: {msg.content}]")
                except Exception as e:
                    logger.warning(f"Could not process message for history: {msg}, error: {e}")
                    continue
        
        history_string = " ".join(history_parts)
        
        return f"Lịch sử hội thoại: {history_string}\n\nCâu hỏi mới: {current_question}"
    
    def create_query_rewrite_prompt(self, history_context: str) -> str:
        """
        Tạo prompt cho LLM để rewrite câu hỏi
        Không hardcode patterns, để LLM tự hiểu và xử lý
        """
        prompt = f"""
Hãy dựa vào toàn bộ lịch sử hội thoại và câu hỏi mới của user, nếu câu hỏi mới không đủ rõ/ngắn/gãy ý, hãy tự động diễn giải lại thành một câu hỏi hoàn chỉnh, đầy đủ thông tin từ lịch sử. Nếu đã rõ thì giữ nguyên.

{history_context}

Hãy trả lời chỉ với câu hỏi đã được rewrite (hoặc giữ nguyên nếu đã rõ ràng), không thêm giải thích.
"""
        return prompt.strip()
    
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
        # Tách từ và lọc - không loại bỏ stopwords
        words = re.findall(r'\b\w+\b', text)
        keywords = {word for word in words if len(word) > 2}
        
        return keywords
    
    def _filter_relevant_turns(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        """Lọc và sắp xếp turns theo relevance và giới hạn"""
        # Nếu có ít turns, trả về tất cả
        if len(turns) <= self.max_turns:
            return turns
        
        # Tính relevance scores nếu chưa có
        if not any(t.relevance_score for t in turns):
            self._calculate_relevance_scores(turns, "")
        
        # Lấy turns gần nhất (ưu tiên context gần đây)
        recent_turns = turns[-self.max_turns:]
        
        # Nếu có ít hơn max_turns, trả về tất cả
        if len(recent_turns) <= self.max_turns:
            return recent_turns
        
        # Nếu có nhiều turns, kết hợp relevance và recency
        # Lấy 70% turns gần nhất và 30% turns có relevance cao
        recent_count = int(self.max_turns * 0.7)
        relevance_count = self.max_turns - recent_count
        
        # Lấy turns gần nhất
        selected_turns = recent_turns[-recent_count:]
        
        # Lấy thêm turns có relevance cao từ toàn bộ lịch sử
        sorted_by_relevance = sorted(turns, key=lambda x: x.relevance_score or 0, reverse=True)
        high_relevance_turns = [t for t in sorted_by_relevance[:relevance_count] 
                               if t.relevance_score and t.relevance_score > 0.2 
                               and t not in selected_turns]
        
        # Kết hợp và sắp xếp theo thứ tự thời gian
        combined_turns = selected_turns + high_relevance_turns
        combined_turns.sort(key=lambda x: turns.index(x))
        
        # Đảm bảo không vượt quá max_turns
        return combined_turns[:self.max_turns]
    
    def _create_context_string(self, turns: List[ConversationTurn], current_question: str) -> str:
        """Tạo context string từ các turns đã lọc - đơn giản, không hardcode"""
        if not turns:
            return ""
        
        # Nếu có ít turns, sử dụng trực tiếp
        if len(turns) <= 6:  # Tăng từ 3 lên 6 để giữ nhiều context hơn
            context_parts = ["LỊCH SỬ HỘI THOẠI:"]
            for turn in turns:
                role_name = "Người dùng" if turn.role == 'user' else "Trợ lý"
                context_parts.append(f"{role_name}: {turn.content}")
            return "\n".join(context_parts)
        
        # Nếu có nhiều turns, tạo tóm tắt thông minh hơn
        return self._create_summarized_context(turns, current_question)
    
    def _create_summarized_context(self, turns: List[ConversationTurn], current_question: str) -> str:
        """Tạo context có tóm tắt cho cuộc hội thoại dài"""
        # Tách user và assistant messages
        user_messages = [t.content for t in turns if t.role == 'user']
        assistant_messages = [t.content for t in turns if t.role == 'assistant']
        
        # Tạo tóm tắt
        summary_parts = ["LỊCH SỬ HỘI THOẠI:"]
        
        if len(user_messages) > 4:
            # Tóm tắt các câu hỏi trước
            summary_parts.append(f"[TÓM TẮT: Người dùng đã hỏi {len(user_messages)} câu hỏi]")
            # Giữ lại 3 câu hỏi gần nhất thay vì 2
            summary_parts.extend([f"Người dùng: {msg}" for msg in user_messages[-3:]])
        else:
            summary_parts.extend([f"Người dùng: {msg}" for msg in user_messages])
        
        # Thêm assistant responses gần nhất (tăng từ 2 lên 3)
        if assistant_messages:
            summary_parts.extend([f"Trợ lý: {msg}" for msg in assistant_messages[-3:]])
        
        return "\n".join(summary_parts)
    
# Singleton instance
context_manager = ContextManager()
