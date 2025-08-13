# agents/nodes/graph_retrieve_node.py
import time
import asyncio
import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from agents.state import ChatState
from services.graph_rag_service import GraphRAGService
from langfuse.decorators import observe

logger = logging.getLogger(__name__)

@observe()
async def graph_retrieve_context(state: ChatState) -> ChatState:
    """Node mới để retrieve context từ knowledge graph"""
    start_time = time.time()
    
    # Kiểm tra nếu đã có error từ guardrails
    if state.get("error") == "input_validation_failed":
        logger.info(f"[GraphRetrieve] Skipping graph retrieval due to guardrails error")
        state["processing_time"]["graph_retrieval"] = time.time() - start_time
        return state
    
    query = state.get("rewritten_query") or state["question"] or ""
    
    try:
        # Get graph context
        from services.graph_rag_service import graph_rag_service
        loop = asyncio.get_running_loop()
        graph_context = await loop.run_in_executor(
            None, 
            graph_rag_service.get_graph_context, 
            query
        )
        
        if graph_context:
            # Add graph context to state
            state["graph_context"] = graph_context
            logger.info(f"[GraphRetrieve] Found graph context: {len(graph_context)} characters")
        else:
            state["graph_context"] = ""
            logger.info(f"[GraphRetrieve] No relevant graph context found")
            
    except Exception as e:
        logger.error(f"[GraphRetrieve] Error in graph retrieval: {e}")
        state["graph_context"] = ""
    
    duration = time.time() - start_time
    state["processing_time"]["graph_retrieval"] = duration
    logger.info(f"[GraphRetrieve] Graph retrieval time: {duration:.4f}s")
    
    return state