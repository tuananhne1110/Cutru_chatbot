from typing import Dict, List, Optional, Tuple
import logging
from agents.prompt.prompt_templates import prompt_templates, CategoryType
from agents.utils.intent_detector import IntentType, intent_detector

logger = logging.getLogger(__name__)

class PromptManager:
    """Quản lý việc tạo prompt động dựa trên category và context"""
    
    def __init__(self):
        self.prompt_templates = prompt_templates
        self.intent_detector = intent_detector
    
    def create_dynamic_prompt(self, 
                            question: str, 
                            chunks: List[Dict], 
                            ) -> str:
        """
        Tạo prompt động dựa trên câu hỏi, chunks và intent/category
        
        Args:
            question: Câu hỏi của người dùng
            chunks: Danh sách chunks từ search
            intent: Intent đã detect (optional)
            category: Category cụ thể (optional)
            
        Returns:
            str: Prompt hoàn chỉnh
        """

        # Lấy prompt template theo category
        prompt_template = self.prompt_templates.get_prompt_by_category()
        
        # Format context theo category
        formatted_context = self.prompt_templates.format_context_by_category(chunks)
        
        # Thêm log để kiểm tra context truyền vào prompt
        logger.info("[PromptManager] THÔNG TIN THAM KHẢO (context) truyền vào prompt:")
        logger.info(formatted_context)
        
        # Tạo prompt hoàn chỉnh
        final_prompt = prompt_template.format(
            context=formatted_context,
            question=question
        )
        
   
        return final_prompt
    

# Singleton instance
prompt_manager = PromptManager() 