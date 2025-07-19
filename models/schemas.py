from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    messages: Optional[List[dict]] = None

class Source(BaseModel):
    law_name: Optional[str] = None
    article: Optional[str] = None
    chapter: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    file_url: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[dict] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str
    timestamp: str
