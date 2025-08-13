import asyncio
import logging
import json
from dataclasses import asdict
from typing import Optional, AsyncIterator

from fastapi import APIRouter, FastAPI
from fastapi.responses import StreamingResponse, JSONResponse

from services.cccd_reader import DEFAULT_STATUS, latest_status, start_socket_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reader", tags=["CCCD Reader"])


# --------------------------- App lifecycle hooks ---------------------------

def init_socket_connection(app: FastAPI) -> None:
    """
    Gắn startup/shutdown handler để chạy socket client nền.
    Lưu task trong app.state.socket_task để không dùng biến global module.
    """

    async def _startup() -> None:
        task: Optional[asyncio.Task] = getattr(app.state, "socket_task", None)
        if task is None or task.done():
            logger.info("Starting CCCD socket task...")
            app.state.socket_task = asyncio.create_task(start_socket_connection())
        else:
            logger.info("CCCD socket task already running.")

    async def _shutdown() -> None:
        task: Optional[asyncio.Task] = getattr(app.state, "socket_task", None)
        if task and not task.done():
            logger.info("Cancelling CCCD socket task...")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("CCCD socket task cancelled.")

    app.add_event_handler("startup", _startup)
    app.add_event_handler("shutdown", _shutdown)


# --------------------------------- Routes ----------------------------------

@router.post("", summary="Start CCCD reader - Connect to Socket.IO")
async def start_reader():
    """
    Chủ động khởi động socket client (nếu chưa chạy).
    Nếu đã chạy rồi, trả về lý do.
    """
    # Tạo task mới nếu chưa có hoặc đã kết thúc
    if not getattr(start_reader, "_socket_task", None) or start_reader._socket_task.done():
        start_reader._socket_task = asyncio.create_task(start_socket_connection())
        return JSONResponse({"started": True})
    return JSONResponse({"started": False, "reason": "already_running"})


@router.get("/validate", summary="SSE stream status until validated")
async def reader_validate():
    """
    Trả SSE (Server-Sent Events) cập nhật trạng thái đọc thẻ cho đến khi validated=True.
    Mỗi ~0.8s gửi một trạng thái. Kết thúc stream khi validated.
    """

    # Reset trạng thái về mặc định trước khi bắt đầu stream
    latest_status.clear()
    latest_status.update(asdict(DEFAULT_STATUS))

    async def event_stream() -> AsyncIterator[str]:
        # Gửi initial snapshot ngay lập tức
        while True:
            st = latest_status
            payload = {
                "status": st.get("status"),
                "message": st.get("message"),
                "validated": bool(st.get("validated", False)),
            }
            # Định dạng SSE: mỗi message bắt đầu bằng "data: " và kết thúc bằng "\n\n"
            yield f"event: status\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

            if payload["validated"]:
                break
            await asyncio.sleep(0.8)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # tránh buffer khi dùng Nginx
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@router.get("/data", summary="Return validated CCCD data as JSON")
async def reader_validated_endpoint():
    """
    Trả về dữ liệu CCCD đã validate. 404 nếu chưa có dữ liệu hợp lệ.
    """
    st = latest_status
    if st.get("validated") and st.get("data"):
        return JSONResponse(content=st["data"])
    return JSONResponse(content={"error": "No validated data"}, status_code=404)