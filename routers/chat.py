from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/chat", tags=["Chat (Deprecated)"])

DEPRECATION_MSG = "This endpoint is deprecated. Please use the new /chat endpoint (LangGraph-based)."

@router.post("/", status_code=410)
async def chat(*args, **kwargs):
    raise HTTPException(status_code=410, detail=DEPRECATION_MSG)

@router.post("/stream", status_code=410)
async def chat_stream(*args, **kwargs):
    raise HTTPException(status_code=410, detail=DEPRECATION_MSG)

@router.get("/history/{session_id}", status_code=410)
async def get_history(session_id: str, limit: int = 50):
    raise HTTPException(status_code=410, detail=DEPRECATION_MSG)

@router.post("/session", status_code=410)
async def create_session():
    raise HTTPException(status_code=410, detail=DEPRECATION_MSG)

@router.delete("/history/{session_id}", status_code=410)
async def delete_history(session_id: str):
    raise HTTPException(status_code=410, detail=DEPRECATION_MSG) 