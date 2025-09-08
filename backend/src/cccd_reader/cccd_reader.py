import asyncio
import logging
import os
import random
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import socketio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ReadStatus:
    id: int = -1
    status: str = "Chưa có thẻ được đọc"
    message: str = "Chưa có thẻ được đọc"
    data: Optional[Dict[str, Any]] = None
    validated: bool = False

DEFAULT_STATUS = ReadStatus()

# Trạng thái mới nhất (mutable dict để dễ update trong event-loop)
latest_status: Dict[str, Any] = asdict(DEFAULT_STATUS)

# SocketIO client (toàn cục cho module)
sio = socketio.AsyncClient()
_socket_started: bool = False

# --- Helpers ---------------------------------------------------------------
def _standardize_result(**kwargs) -> Dict[str, Any]:
    """
    Merge với DEFAULT_STATUS để đảm bảo đủ key
    """
    base = asdict(DEFAULT_STATUS).copy()
    base.update(kwargs)
    return base

def get_latest_status() -> Dict[str, Any]:
    """
    Truy vấn trạng thái mới nhất (trả về bản copy để tránh mutate từ ngoài).
    """
    return latest_status.copy()

def validate_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuẩn hoá event từ Socket.IO về dict gồm:
    id, status, message, data, validated
    """
    event_id = payload.get("id")

    if event_id == 1:
        logger.info("Phát hiện thẻ CCCD, chuẩn bị đọc QR")
        return _standardize_result(
            id=1,
            status="Phát hiện thẻ CCCD, chuẩn bị đọc thông tin QR",
            message="Phát hiện thẻ mới, đang đọc",
            data=None,
            validated=False,  # tạm thời False cho bước phát hiện
        )

    if event_id == 3:
        message = payload.get("message", "Lỗi không xác định")
        logger.warning("Đã xảy ra lỗi %s trong quá trình đọc thẻ", message)
        return _standardize_result(
            id=3,
            status=f"Không đọc được thẻ, vui lòng thử lại. Lỗi {message}",
            message=message,
            data=None,
            validated=False,
        )

    if event_id == 2:
        data = payload.get("data") or {}
        id_code = data.get("idCode")
        person_name = data.get("personName")
        if not id_code or not person_name:
            logger.warning("Lỗi khi đọc QR: Không đọc được thông tin thẻ")
            return _standardize_result(
                id=2,
                status="Lỗi khi đọc QR: Không đọc được thông tin thẻ",
                message="Lỗi khi đọc QR: Không đọc được thông tin thẻ",
                data=data,
                validated=False,
            )
        logger.info("Đọc dữ liệu CCCD thành công (idCode=%s)", id_code)
        return _standardize_result(
            id=2,
            status="Đọc thẻ thành công",
            message="Đọc thẻ thành công",
            data=data,
            validated=True,
        )

    logger.info("Bỏ qua event không xử lý, id = %s", event_id)
    return _standardize_result(
        id=-1,
        status=f"Bỏ qua event không xử lý, id = {event_id}",
        message=f"Bỏ qua event không xử lý, id = {event_id}",
        data=None,
        validated=False,
    )

# --- Socket.IO Event Handlers ----------------------------------------------
@sio.event
async def connect():
    logger.info("Đã kết nối tới Socket.IO server")

@sio.event
async def disconnect():
    logger.warning("Mất kết nối với Socket.IO server")

# Lưu ý: tên event phải khớp với backend.
# Nếu backend phát "/event" thì giữ nguyên; còn không thì đổi thành "event".
@sio.on("/event")
async def on_event(data: Dict[str, Any]):
    global latest_status
    try:
        result = validate_event(data)
    except Exception as exc:  # phòng thủ
        logger.exception("Lỗi khi xử lý dữ liệu event: %s", exc)
        result = _standardize_result(
            id=-1,
            status="Lỗi khi xử lý dữ liệu",
            message="Lỗi khi xử lý dữ liệu",
            data=None,
            validated=False,
        )
    latest_status.update(result)

# --- Runner ----------------------------------------------------------------
async def start_socket_connection():
    """
    Kết nối tới server Socket.IO và tự động retry với exponential backoff + jitter.
    - Đặt biến môi trường READER_ADDRESS, ví dụ: http://localhost:8000
    """
    global _socket_started
    if _socket_started:
        logger.info("Socket.IO client đã được khởi động trước đó")
        return
    _socket_started = True

    reader_address = os.getenv("READER_ADDRESS")
    if not reader_address:
        raise RuntimeError("Thiếu biến môi trường READER_ADDRESS")

    attempt = 0
    max_backoff = 30  # giây
    logger.info("Bắt đầu kết nối tới Socket.IO tại %s", reader_address)

    while True:
        attempt += 1
        try:
            # Kết nối, đặt timeout vừa phải để tránh treo
            await sio.connect(reader_address, wait_timeout=10)
            # Nếu connect thành công, reset số lần thử
            attempt = 0
            # Blocking cho đến khi disconnect
            await sio.wait()
        except asyncio.CancelledError:
            # Cho phép task bị huỷ một cách sạch sẽ
            logger.info("Task start_socket_connection bị huỷ")
            raise
        except Exception as exc:
            # Backoff theo 2^n với trần và random jitter để tránh bão reconnect
            backoff = min(2 ** min(attempt, 6), max_backoff)
            jitter = random.uniform(0, 1.0)
            sleep_s = backoff + jitter
            logger.warning(
                "Không thể kết nối (%s). Sẽ thử lại sau %.1fs (attempt=%d)",
                exc,
                sleep_s,
                attempt,
            )
            await asyncio.sleep(sleep_s)
        finally:
            # Nhỏ nhẹ một nhịp để nhường event loop
            await asyncio.sleep(0.2)

# --- Optional: chạy trực tiếp ----------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(start_socket_connection())
    except KeyboardInterrupt:
        logger.info("Đã dừng bởi người dùng")