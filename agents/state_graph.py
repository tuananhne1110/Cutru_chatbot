# agents/state_graph.py - Extended state for Graph RAG
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
from agents.utils.intent_detector import IntentType

class GraphChatState(TypedDict):
    """Extended state cho Graph RAG system"""
    # Original fields
    messages: List[BaseMessage]
    question: str
    session_id: str
    intent: Optional[IntentType]
    all_intents: List[tuple]
    context_docs: List[Document]
    rewritten_query: Optional[str]
    sources: List[Dict[str, Any]]
    answer: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    processing_time: Dict[str, float]
    prompt: Optional[str]
    answer_chunks: Optional[List[str]]
    
    # New Graph RAG fields
    graph_context: Optional[str]  # Context from knowledge graph
    graph_entities: List[Dict[str, Any]]  # Relevant entities
    graph_relationships: List[Dict[str, Any]]  # Relevant relationships
    context_source: str  # "vector", "graph", or "hybrid"