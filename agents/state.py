from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
from agents.utils.intent_detector import IntentType

class ChatState(TypedDict):
    """State cho LangGraph chat system"""
    messages: List[BaseMessage]
    question: str
    session_id: str
    intent: Optional[IntentType]
    all_intents: List[tuple]  # Lưu tất cả intents
    context_docs: List[Document]
    rewritten_query: Optional[str]
    sources: List[Dict[str, Any]]
    answer: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    processing_time: Dict[str, float]
    prompt: Optional[str]  # Add prompt for streaming
    answer_chunks: Optional[List[str]]  # Add for streaming real chunks 