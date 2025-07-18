from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
import logging
from models.schemas import ChatRequest, ChatResponse, Source
from agents.langgraph_implementation import rag_workflow, create_initial_state, extract_results_from_state, ChatState
from langchain_core.runnables import RunnableConfig
from typing import cast
from fastapi.responses import StreamingResponse
import json

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
        # Use cast to satisfy Pyright for config type
        config = cast(RunnableConfig, {"configurable": {"thread_id": session_id}})
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
        config = cast(RunnableConfig, {"configurable": {"thread_id": session_id}})
        # Run workflow to get prompt
        result = await rag_workflow.ainvoke(initial_state, config=config)
        prompt = result.get("prompt")
        sources = result.get("sources", [])
        if not prompt:
            answer = result.get("answer", "Xin lỗi, không thể tạo prompt.")
            def fallback_stream():
                yield f"data: {{\"type\": \"error\", \"content\": \"{answer}\"}}\n\n"
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