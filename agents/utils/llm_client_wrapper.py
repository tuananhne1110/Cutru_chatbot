import logging
from typing import List
from services.llm_service import call_llm_full

logger = logging.getLogger(__name__)

class LLMClientWrapper:
    """
    Wrapper cho LLM client để sử dụng trong query rewrite
    """
    
    def __init__(self, model="llama", max_tokens=1000, temperature=0.3):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    async def agenerate(self, prompts: List[str]):
        """
        Generate response từ LLM
        """
        try:
            if not prompts:
                return None
            
            prompt = prompts[0]
            
            # Gọi LLM service
            response_text = call_llm_full(
                prompt=prompt,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Tạo mock response object để tương thích với LangChain
            return MockLLMResponse(response_text)
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None

class MockLLMResponse:
    """
    Mock response object để tương thích với LangChain
    """
    
    def __init__(self, text: str):
        self.generations = [[MockGeneration(text)]]

class MockGeneration:
    """
    Mock generation object
    """
    
    def __init__(self, text: str):
        self.text = text

# Singleton instance
llm_client_wrapper = LLMClientWrapper() 