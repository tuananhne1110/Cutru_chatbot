from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
import logging
from models.schemas import ChatRequest, ChatResponse, Source
from agents.workflow import rag_workflow
from agents.utils.message_conversion import create_initial_state, extract_results_from_state
from agents.state import ChatState
from langchain_core.runnables import RunnableConfig
from typing import cast
from fastapi.responses import StreamingResponse
import json
from config.settings import settings
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["LangGraph Chat"])

@router.post("/", response_model=ChatResponse)
async def langgraph_chat(request: ChatRequest):
    """Chat endpoint sử dụng LangGraph workflow"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question
        
        # Build initial state for LangGraph
        initial_state: ChatState = create_initial_state(question, messages, session_id)
        
        # Prepare config with LangSmith metadata
        config_dict = {"configurable": {"thread_id": session_id}}
        
        # Add LangSmith tags and metadata if tracing is enabled
        if settings.langsmith_config.get("tracing_enabled", False):
            config_dict["tags"] = settings.langsmith_config.get("tags", [])
            config_dict["metadata"] = {
                **settings.langsmith_config.get("metadata", {}),
                "session_id": session_id,
                "endpoint": "/chat",
                "timestamp": datetime.now().isoformat(),
                "question_length": len(question) if question else 0,
                "message_count": len(messages)
            }
        
        config = cast(RunnableConfig, config_dict)
        
        # Run LangGraph workflow
        result = await rag_workflow.ainvoke(initial_state, config=config)
        
        # Extract results
        results = extract_results_from_state(result)
        answer = results["answer"]
        sources = results["sources"]
        
        return ChatResponse(
            answer=answer,
            sources=[Source(**src) for src in sources],
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Exception in /langgraph-chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def langgraph_chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint sử dụng LangGraph workflow.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question
        initial_state: ChatState = create_initial_state(question, messages, session_id)
        
        # Prepare config with LangSmith metadata
        config_dict = {"configurable": {"thread_id": session_id}}
        
        # Add LangSmith tags and metadata if tracing is enabled
        if settings.langsmith_config.get("tracing_enabled", False):
            config_dict["tags"] = settings.langsmith_config.get("tags", []) + ["streaming"]
            config_dict["metadata"] = {
                **settings.langsmith_config.get("metadata", {}),
                "session_id": session_id,
                "endpoint": "/chat/stream",
                "timestamp": datetime.now().isoformat(),
                "question_length": len(question) if question else 0,
                "message_count": len(messages),
                "streaming": True
            }
        
        config = cast(RunnableConfig, config_dict)
        
        # Run workflow to get result
        result = await rag_workflow.ainvoke(initial_state, config=config)
        
        # Kiểm tra nếu guardrails đã chặn
        if result.get("error") == "input_validation_failed":
            answer = result.get("answer", "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam.")
            def guardrails_blocked_stream():
                # Stream từng ký tự của answer
                for char in answer:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': char})}\n\n"
                # Gửi chunk done để báo hiệu kết thúc
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
            # Yield một chuỗi dummy lớn để phá buffer
            yield " " * 2048 + "\n"
            for chunk in call_llm_stream(prompt, model="llama"):
                if chunk:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            # Gửi sources cho frontend
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            # Gửi chunk done để báo hiệu kết thúc
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(stream_llm(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Exception in /chat/stream endpoint: {e}",exc_info=True)
        def error_stream(e=e):
            yield f"data: {{\"type\": \"error\", \"content\": \"Đã xảy ra lỗi: {str(e)}\"}}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream") 