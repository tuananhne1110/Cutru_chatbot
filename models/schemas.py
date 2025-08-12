from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    messages: Optional[List[dict]] = None

class Source(BaseModel):
    # Common fields
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Optional[dict] = None
    
    # Legal chunks fields (cấu trúc mới: chỉ có Chương và Điều)
    law_name: Optional[str] = None
    law_code: Optional[str] = None
    law_type: Optional[str] = None
    promulgator: Optional[str] = None
    promulgation_date: Optional[str] = None
    effective_date: Optional[str] = None
    chapter: Optional[str] = None
    chapter_content: Optional[str] = None
    id: Optional[str] = None
    category: Optional[str] = None
    
    # Form chunks fields
    form_code: Optional[str] = None
    form_name: Optional[str] = None
    field_no: Optional[str] = None
    field_name: Optional[str] = None
    chunk_type: Optional[str] = None
    category: Optional[str] = None
    
    # Term chunks fields
    term: Optional[str] = None
    definition: Optional[str] = None
    category: Optional[str] = None
    
    # Procedure chunks fields
    procedure_code: Optional[str] = None
    procedure_name: Optional[str] = None
    procedure_type: Optional[str] = None
    implementation_level: Optional[str] = None
    implementation_subject: Optional[str] = None
    implementation_result: Optional[str] = None
    implementing_agency: Optional[str] = None
    coordinating_agency: Optional[str] = None
    competent_authority: Optional[str] = None
    authorized_agency: Optional[str] = None
    application_receiving_address: Optional[str] = None
    field: Optional[str] = None
    source_section: Optional[str] = None
    content_type: Optional[str] = None
    table_title: Optional[str] = None
    decision_number: Optional[str] = None
    requirements: Optional[str] = None
    category: Optional[str] = None
    
    # Template chunks fields
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[str] = None
    procedures: Optional[str] = None
    category: Optional[str] = None
    
class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str
    timestamp: str
