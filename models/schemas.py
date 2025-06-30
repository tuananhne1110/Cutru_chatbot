from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class Source(BaseModel):
    law_name: str
    article: Optional[str] = None
    chapter: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str
    timestamp: str

class ChatHistoryResponse(BaseModel):
    messages: List[dict]
    session_id: str 