import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum
from agents.utils.intent_detector import IntentType, intent_detector

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RewriteStrategy(Enum):
    """Các chiến lược rewrite khác nhau"""
    HYDE = "HyDE"  # Hypothetical Document Embedding
    SUB_QUERY = "Sub-Query"  # Chia nhỏ câu hỏi
    MULTI_QUERY = "Multi-Query"  # Tạo nhiều biến thể
    STANDARD = "Standard"  # Rewrite chuẩn

class QueryRewriteTester:
    """
    Test class để thử nghiệm các chiến lược rewrite khác nhau
    """
    
    def __init__(self):
        self.intent_detector = intent_detector
        self._setup_intent_strategy_mapping()
        
    def _setup_intent_strategy_mapping(self):
        """Thiết lập mapping giữa intent và chiến lược rewrite"""
        self.intent_strategy_mapping = {
            IntentType.LAW: RewriteStrategy.HYDE,
            IntentType.PROCEDURE: RewriteStrategy.SUB_QUERY,
            IntentType.FORM: RewriteStrategy.MULTI_QUERY,
            IntentType.TERM: RewriteStrategy.STANDARD,
            IntentType.TEMPLATE: RewriteStrategy.MULTI_QUERY,
            IntentType.GENERAL: RewriteStrategy.MULTI_QUERY,
        }
        
    def detect_intent_and_strategy(self, question: str) -> Tuple[List[Tuple[IntentType, str]], RewriteStrategy]:
        """
        Phát hiện intent và chọn chiến lược rewrite phù hợp
        """
        # Phát hiện intent
        intents = self.intent_detector.detect_intent(question)
        logger.info(f"Detected intents: {[(intent.value, query) for intent, query in intents]}")
        
        # Chọn chiến lược dựa trên intent chính (đầu tiên)
        if intents:
            main_intent = intents[0][0]
            strategy = self.intent_strategy_mapping.get(main_intent, RewriteStrategy.STANDARD)
            logger.info(f"Main intent: {main_intent.value} -> Strategy: {strategy.value}")
        else:
            strategy = RewriteStrategy.STANDARD
            logger.info(f"No intent detected -> Strategy: {strategy.value}")
            
        return intents, strategy
    
    def create_strategy_specific_prompt(self, strategy: RewriteStrategy, question: str, context: str = "") -> str:
        """
        Tạo prompt phù hợp với từng chiến lược rewrite
        """
        base_prompt = f"""
Câu hỏi hiện tại: {question}

"""
        
        if context:
            base_prompt += f"Context: {context}\n\n"
        
        if strategy == RewriteStrategy.HYDE:
            return base_prompt + """
Chiến lược HyDE (Hypothetical Document Embedding):
Hãy tạo một câu hỏi giả định như thể bạn đang tìm kiếm một tài liệu pháp lý cụ thể chứa thông tin này.
Tập trung vào việc tìm đúng Điều, Khoản, Điểm của luật.
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.

Ví dụ:
- "Điều kiện đăng ký tạm trú" → "Điều 30 Luật Cư trú quy định về điều kiện đăng ký tạm trú"
- "Thời hạn tạm trú" → "Khoản 2 Điều 31 Luật Cư trú quy định thời hạn tạm trú"
"""
        
        elif strategy == RewriteStrategy.SUB_QUERY:
            return base_prompt + """
Chiến lược Sub-Query:
Hãy chia nhỏ câu hỏi thành các phần riêng biệt để tránh hiểu sai.
Tập trung vào từng điều kiện, bước thực hiện cụ thể.
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.

Ví dụ:
- "Thủ tục đăng ký thường trú" → "Các bước thực hiện đăng ký thường trú và giấy tờ cần thiết"
- "Điều kiện cấp CCCD" → "Điều kiện về độ tuổi, nơi cư trú và giấy tờ cần thiết để cấp CCCD"
"""
        
        elif strategy == RewriteStrategy.MULTI_QUERY:
            return base_prompt + """
Chiến lược Multi-Query:
Hãy tạo nhiều biến thể của câu hỏi để tăng khả năng tìm kiếm.
Với FORM: thử các tên gọi khác nhau của biểu mẫu
Với GENERAL: mở rộng nhiều hướng tìm tài liệu phù hợp
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.

Ví dụ:
- "Mẫu đơn đăng ký tạm trú" → "Tờ khai đăng ký tạm trú, phiếu khai báo tạm trú, mẫu đơn tạm trú"
- "Giấy tờ cư trú" → "Sổ hộ khẩu, sổ tạm trú, giấy chứng nhận nhân khẩu tập thể"
"""
        
        else:  # STANDARD
            return base_prompt + """
Chiến lược Standard:
Hãy diễn giải lại câu hỏi cho rõ ràng hơn nếu cần.
Nếu câu hỏi đã rõ ràng thì giữ nguyên.
Chỉ trả lời bằng câu hỏi đã rewrite, không thêm giải thích.

Ví dụ:
- "Tạm trú là gì?" → "Định nghĩa tạm trú theo quy định pháp luật"
- "Thời hạn tạm trú bao lâu?" → "Thời hạn tạm trú được quy định như thế nào"
"""
    
    def simulate_llm_response(self, prompt: str, strategy: RewriteStrategy) -> str:
        """
        Mô phỏng response từ LLM (cho test)
        """
        # Đây là mock response, trong thực tế sẽ gọi LLM thật
        mock_responses = {
            RewriteStrategy.HYDE: "Điều 30 Luật Cư trú quy định về điều kiện đăng ký tạm trú",
            RewriteStrategy.SUB_QUERY: "Các bước thực hiện đăng ký thường trú và giấy tờ cần thiết",
            RewriteStrategy.MULTI_QUERY: "Tờ khai đăng ký tạm trú, phiếu khai báo tạm trú, mẫu đơn tạm trú",
            RewriteStrategy.STANDARD: "Định nghĩa tạm trú theo quy định pháp luật"
        }
        
        return mock_responses.get(strategy, "Câu hỏi đã được rewrite")
    
    def test_query_rewrite(self, question: str, context: str = "") -> Dict:
        """
        Test toàn bộ quy trình rewrite
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing query: {question}")
        logger.info(f"Context: {context}")
        
        # 1. Phát hiện intent và chọn strategy
        intents, strategy = self.detect_intent_and_strategy(question)
        
        # 2. Tạo prompt phù hợp
        prompt = self.create_strategy_specific_prompt(strategy, question, context)
        logger.info(f"Generated prompt for {strategy.value}:")
        logger.info(prompt)
        
        # 3. Mô phỏng LLM response
        rewritten_query = self.simulate_llm_response(prompt, strategy)
        logger.info(f"Rewritten query: {rewritten_query}")
        
        return {
            "original_question": question,
            "detected_intents": [(intent.value, query) for intent, query in intents],
            "selected_strategy": strategy.value,
            "rewritten_query": rewritten_query,
            "prompt_used": prompt
        }

def run_tests():
    """
    Chạy các test case
    """
    tester = QueryRewriteTester()
    
    # Test cases
    test_cases = [
        {
            "question": "Điều kiện đăng ký tạm trú",
            "context": "User hỏi về thủ tục cư trú",
            "expected_intent": IntentType.LAW
        },
        {
            "question": "Thủ tục đăng ký thường trú",
            "context": "User muốn biết quy trình thực hiện",
            "expected_intent": IntentType.PROCEDURE
        },
        {
            "question": "Mẫu đơn đăng ký tạm trú",
            "context": "User cần tìm biểu mẫu",
            "expected_intent": IntentType.FORM
        },
        {
            "question": "Tạm trú là gì?",
            "context": "User hỏi định nghĩa",
            "expected_intent": IntentType.TERM
        },
        {
            "question": "Xin chào",
            "context": "User chào hỏi",
            "expected_intent": IntentType.GENERAL
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\nTest case {i}:")
        result = tester.test_query_rewrite(
            test_case["question"], 
            test_case["context"]
        )
        results.append(result)
        
        # Kiểm tra intent có đúng không
        detected_intents = [intent for intent, _ in result["detected_intents"]]
        expected_intent = test_case["expected_intent"]
        
        if expected_intent in detected_intents:
            logger.info(f"✅ Intent detection PASSED: Expected {expected_intent.value}, got {detected_intents}")
        else:
            logger.warning(f"⚠️ Intent detection FAILED: Expected {expected_intent.value}, got {detected_intents}")
    
    return results

if __name__ == "__main__":
    # Chạy tests
    results = run_tests()
    
    # Tổng kết
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY:")
    logger.info(f"Total test cases: {len(results)}")
    
    for i, result in enumerate(results, 1):
        logger.info(f"\nTest {i}:")
        logger.info(f"  Original: {result['original_question']}")
        logger.info(f"  Intents: {result['detected_intents']}")
        logger.info(f"  Strategy: {result['selected_strategy']}")
        logger.info(f"  Rewritten: {result['rewritten_query']}") 