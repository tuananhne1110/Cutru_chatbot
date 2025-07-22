from agents.utils.intent_detector import intent_detector, IntentType
from agents.state import ChatState

async def set_intent(state: ChatState) -> ChatState:
    """Bước 1: Phân tích intent từ câu hỏi"""
    question = state["question"]
    intents = intent_detector.detect_intent(question)
    state["all_intents"] = intents
    primary_intent = intents[0][0] if intents else IntentType.GENERAL
    state["intent"] = primary_intent
    return state 