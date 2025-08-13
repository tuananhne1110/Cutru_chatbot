# agents/workflow_graph_rag.py
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from agents.state import ChatState
from agents.nodes.intent_node import set_intent
from agents.nodes.rewrite_node import rewrite_query_with_context
from agents.nodes.retrieve_node import retrieve_context
from agents.nodes.graph_retrieve_node import graph_retrieve_context
from agents.nodes.generate_node import generate_answer_with_graph
from agents.nodes.validate_node import validate_output
from agents.nodes.memory_node import update_memory
from agents.nodes.semantic_cache_node import semantic_cache
from agents.nodes.guardrails_node import guardrails_input
from config.app_config import langsmith_cfg

def create_graph_rag_workflow():
    """Tạo workflow kết hợp Graph RAG và Vector RAG"""
    workflow = StateGraph(ChatState)
    
    # Add all nodes
    workflow.add_node("set_intent", set_intent)
    workflow.add_node("semantic_cache", semantic_cache)
    workflow.add_node("guardrails_input", guardrails_input)
    workflow.add_node("rewrite", rewrite_query_with_context)
    workflow.add_node("graph_retrieve", graph_retrieve_context)  # NEW: Graph RAG
    workflow.add_node("retrieve", retrieve_context)  # Vector RAG
    workflow.add_node("generate", generate_answer_with_graph)  # Modified to use both contexts
    workflow.add_node("validate", validate_output)
    workflow.add_node("update_memory", update_memory)
    
    # Edges - Graph RAG runs parallel to Vector RAG
    workflow.add_edge(START, "set_intent")
    workflow.add_edge("set_intent", "semantic_cache")
    workflow.add_edge("semantic_cache", "guardrails_input")
    workflow.add_edge("guardrails_input", "rewrite")
    workflow.add_edge("rewrite", "graph_retrieve")  # Graph retrieval first
    workflow.add_edge("graph_retrieve", "retrieve")  # Then vector retrieval
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", "update_memory")
    workflow.add_edge("update_memory", END)
    
    # Compile
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    if langsmith_cfg.get("tracing_enabled", False):
        app.metadata = langsmith_cfg.get("metadata", {})
        
    return app

# Global instance
graph_rag_workflow = create_graph_rag_workflow()