from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from agents.state import ChatState

def convert_messages_to_langchain(messages: List[Dict]) -> List[BaseMessage]:
    """Convert messages từ format hiện tại sang LangChain format"""
    langchain_messages = []
    for msg in messages:
        if msg.get('role') == 'user':
            langchain_messages.append(HumanMessage(content=msg.get('content', '')))
        elif msg.get('role') == 'assistant':
            langchain_messages.append(AIMessage(content=msg.get('content', '')))
    return langchain_messages

def create_initial_state(question: str, messages: List[Dict], session_id: str) -> ChatState:
    """Tạo initial state cho LangGraph workflow"""
    langchain_messages = convert_messages_to_langchain(messages)
    langchain_messages.append(HumanMessage(content=question))
    return {
        "messages": langchain_messages,
        "question": question,
        "session_id": session_id,
        "intent": None,
        "all_intents": [],
        "context_docs": [],
        "rewritten_query": None,
        "sources": [],
        "answer": None,
        "error": None,
        "metadata": {},
        "processing_time": {},
        "prompt": None,
        "answer_chunks": None
    }  # type: ignore

def extract_results_from_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract kết quả từ state và in log thời gian xử lý từng bước"""
    result = {
        "answer": state.get("answer", ""),
        "sources": state.get("sources", []),
        "intent": state.get("intent"),
        "processing_time": state.get("processing_time", {}),
        "error": state.get("error")
    }
    print("=== Thời gian xử lý từng bước ===")
    for step, t in result["processing_time"].items():
        print(f"{step}: {t:.4f} giây")
    return result 