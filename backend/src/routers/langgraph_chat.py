from typing import List, Optional
from datetime import datetime
import uuid
import os
from fastapi import APIRouter
from pydantic import BaseModel

# from src.langgraph_rag.utils.llm_utils import TextChatMessage
from src.langgraph_rag.utils.config_utils import BaseConfig
from src.langgraph_rag.nodes import RAGWorkflowNodes, create_default_rag_state
from src.langgraph_rag.workflows import create_rag_workflow
# Langfuse tracking removed

from fastapi.responses import StreamingResponse
import json
from typing import AsyncGenerator

# --- Khởi tạo một lần ở mức module để tái sử dụng giữa các request ---
router = APIRouter(prefix="/chat", tags=["LangGraph Chat"])  # noqa: E305

_GLOBAL_CONFIG = BaseConfig()
_NODES = RAGWorkflowNodes(global_config=_GLOBAL_CONFIG)
_WORKFLOW = create_rag_workflow(rag_nodes=_NODES)


# --- Schemas ---
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    # Giữ đúng kiểu lịch sử hội thoại: List[TextChatMessage]
    messages: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    timestamp: str


# --- Endpoint ---
@router.post("/", response_model=ChatResponse)
async def langgraph_chat(request: ChatRequest) -> ChatResponse:
    """Nhận câu hỏi + lịch sử hội thoại, chạy workflow và trả lời gọn nhẹ."""
    session_id = request.session_id or str(uuid.uuid4())
    
    initial_state = create_default_rag_state(
        question=request.question,
        conversation_history=request.messages or [],
    )



    # result = _WORKFLOW.invoke(initial_state)
    # answer = result.get("final_response") or "Không có câu trả lời phù hợp."

    result = _WORKFLOW.invoke(initial_state)
    answer = result.get("final_response") or "Không có câu trả lời phù hợp."

    return ChatResponse(
        answer=answer,
        sources = [],
        session_id=session_id,
        timestamp=datetime.now().isoformat(),
    )


@router.post("/stream")
async def langgraph_chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint sử dụng LangGraph workflow
    (KHÔNG còn Langfuse).
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        messages = request.messages or []
        question = request.question

        initial_state = create_default_rag_state(
            question=question,
            conversation_history=messages,
        )

        # Chỉ invoke workflow
        result = await _WORKFLOW.ainvoke(initial_state)
        answer = result.get("final_response", "Xin lỗi, không thể tạo prompt.")

        # Stream SSE chunk-by-chunk
        async def fallback_stream() -> AsyncGenerator[str, None]:
            sent_chars = 0
            try:
                for char in answer:
                    payload = {"type": "chunk", "content": char}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    sent_chars += 1
                # kết thúc stream
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                yield "event: end\ndata: {}\n\n"
            except Exception as stream_err:
                payload = {"type": "error", "content": f"Stream lỗi: {stream_err}"}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                yield "event: end\ndata: {}\n\n"

        return StreamingResponse(
            fallback_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:

        # chuẩn bị message trước để tránh lỗi scope
        err_msg = f"Đã xảy ra lỗi: {e}"

        async def error_stream():
            payload = {"type": "error", "content": err_msg}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "event: end\ndata: {}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
