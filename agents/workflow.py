from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from agents.state import ChatState
from agents.nodes.intent_node import set_intent
from agents.nodes.rewrite_node import rewrite_query_with_context
from agents.nodes.retrieve_node import retrieve_context
from agents.nodes.generate_node import generate_answer
from agents.nodes.validate_node import validate_output
from agents.nodes.memory_node import update_memory
from agents.nodes.semantic_cache_node import semantic_cache
from agents.nodes.guardrails_node import guardrails_input
from config.app_config import langsmith_cfg
import os

class LangChainRAGComponents:
    def __init__(self):
        self.embeddings = None
        self.memory = None
    def create_conversational_chain(self):
        return {"type": "conversational_chain", "description": "LangChain conversational retrieval chain"}
    def create_retrieval_chain(self, intent: str):
        return {"type": "retrieval_chain", "intent": intent, "description": f"LangChain retrieval chain for {intent}"}

def should_continue_after_guardrails(state: ChatState) -> str:
    """Kiểm tra xem có nên tiếp tục sau guardrails hay không."""
    if state.get("error") == "input_validation_failed":
        return "update_memory"  # Chuyển thẳng đến update_memory nếu bị chặn
    return "rewrite"  # Tiếp tục bình thường

def create_rag_workflow():
    workflow = StateGraph(ChatState)
    workflow.add_node("set_intent", set_intent)
    workflow.add_node("semantic_cache", semantic_cache)
    workflow.add_node("guardrails_input", guardrails_input)
    workflow.add_node("rewrite", rewrite_query_with_context)
    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("validate", validate_output)
    workflow.add_node("update_memory", update_memory)
    
    # Edges
    workflow.add_edge(START, "set_intent")
    workflow.add_edge("set_intent", "semantic_cache")
    workflow.add_edge("semantic_cache", "guardrails_input")
    workflow.add_edge("guardrails_input", "rewrite")
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", "update_memory")
    workflow.add_edge("update_memory", END)
    
    # Compile với LangSmith metadata nếu được bật
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    # Thêm metadata từ config cho LangSmith tracking
    if langsmith_cfg.get("tracing_enabled", False):
        app.metadata = langsmith_cfg.get("metadata", {})
        
    return app

rag_workflow = create_rag_workflow()
langchain_components = LangChainRAGComponents() 