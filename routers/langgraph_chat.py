# routers/langgraph_chat_graph.py
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
import logging
from models.schemas import ChatRequest, ChatResponse, Source
from agents.workflow_graph_rag import graph_rag_workflow  # Use new workflow
from agents.utils.message_conversion import create_initial_state, extract_results_from_state
from agents.state_graph import GraphChatState  # Use extended state
from langchain_core.runnables import RunnableConfig
from typing import cast
from fastapi.responses import StreamingResponse
import json
from config.app_config import langsmith_cfg, graph_rag_service
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/graph", tags=["Graph RAG Chat"])

@router.post("/", response_model=ChatResponse)
async def graph_rag_chat(request: ChatRequest):
    """Chat endpoint using Graph RAG workflow"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question
        
        # Check if Graph RAG is available
        if not graph_rag_service:
            logger.warning("Graph RAG not available, falling back to vector RAG")
            # Fallback to original endpoint
            from routers.langgraph_chat import langgraph_chat
            return await langgraph_chat(request)
        
        # Build initial state
        initial_state: GraphChatState = create_initial_state(question, messages, session_id)
        
        # Add Graph RAG specific fields
        initial_state.update({
            "graph_context": None,
            "graph_entities": [],
            "graph_relationships": [],
            "context_source": "hybrid"
        })
        
        # Prepare config
        config_dict = {"configurable": {"thread_id": session_id}}
        
        if langsmith_cfg.get("tracing_enabled", False):
            config_dict["tags"] = langsmith_cfg.get("tags", []) + ["graph-rag"]
            config_dict["metadata"] = {
                **langsmith_cfg.get("metadata", {}),
                "session_id": session_id,
                "endpoint": "/chat/graph",
                "timestamp": datetime.now().isoformat(),
                "question_length": len(question) if question else 0,
                "message_count": len(messages),
                "rag_type": "graph_rag"
            }
        
        config = cast(RunnableConfig, config_dict)
        
        # Run Graph RAG workflow
        result = await graph_rag_workflow.ainvoke(initial_state, config=config)
        
        # Extract results
        results = extract_results_from_state(result)
        answer = results["answer"]
        sources = results["sources"]
        
        # Add Graph RAG metadata
        metadata = {
            "rag_type": "graph_rag",
            "graph_context_used": bool(result.get("graph_context")),
            "context_source": result.get("context_source", "hybrid")
        }
        
        return ChatResponse(
            answer=answer,
            sources=[Source(**src) for src in sources],
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Exception in Graph RAG endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def graph_rag_chat_stream(request: ChatRequest):
    """Streaming Graph RAG chat endpoint"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question
        
        # Check if Graph RAG is available
        if not graph_rag_service:
            logger.warning("Graph RAG not available, falling back to vector RAG")
            from routers.langgraph_chat import langgraph_chat_stream
            return await langgraph_chat_stream(request)
        
        # Build initial state with Graph RAG fields
        initial_state: GraphChatState = create_initial_state(question, messages, session_id)
        initial_state.update({
            "graph_context": None,
            "graph_entities": [],
            "graph_relationships": [],
            "context_source": "hybrid"
        })
        
        # Config
        config_dict = {"configurable": {"thread_id": session_id}}
        
        if langsmith_cfg.get("tracing_enabled", False):
            config_dict["tags"] = langsmith_cfg.get("tags", []) + ["graph-rag", "streaming"]
            config_dict["metadata"] = {
                **langsmith_cfg.get("metadata", {}),
                "session_id": session_id,
                "endpoint": "/chat/graph/stream",
                "timestamp": datetime.now().isoformat(),
                "question_length": len(question) if question else 0,
                "message_count": len(messages),
                "streaming": True,
                "rag_type": "graph_rag"
            }
        
        config = cast(RunnableConfig, config_dict)
        
        # Run workflow
        result = await graph_rag_workflow.ainvoke(initial_state, config=config)
        
        # Check for guardrails blocking
        if result.get("error") == "input_validation_failed":
            answer = result.get("answer", "Xin lỗi, tôi không thể hỗ trợ câu hỏi này.")
            def guardrails_blocked_stream():
                for char in answer:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': char})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return StreamingResponse(guardrails_blocked_stream(), media_type="text/event-stream")
        
        prompt = result.get("prompt")
        sources = result.get("sources", [])
        
        if not prompt:
            answer = result.get("answer", "Xin lỗi, không thể tạo prompt.")
            def fallback_stream():
                for char in answer:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': char})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return StreamingResponse(fallback_stream(), media_type="text/event-stream")
        
        # Stream LLM output
        from services.llm_service import call_llm_stream
        def stream_llm():
            yield " " * 2048 + "\n"  # Buffer breaker
            for chunk in call_llm_stream(prompt, model="llama"):
                if chunk:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # Send Graph RAG metadata
            graph_metadata = {
                "graph_context_used": bool(result.get("graph_context")),
                "context_source": result.get("context_source", "hybrid"),
                "rag_type": "graph_rag"
            }
            yield f"data: {json.dumps({'type': 'metadata', 'metadata': graph_metadata})}\n\n"
            
            # Send sources
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            
            # Done
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        return StreamingResponse(stream_llm(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"Exception in Graph RAG streaming: {e}", exc_info=True)
        def error_stream(e=e):
            yield f"data: {{\"type\": \"error\", \"content\": \"Đã xảy ra lỗi: {str(e)}\"}}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")