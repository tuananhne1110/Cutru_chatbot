
from typing import Any, Dict, List
from typing_extensions import TypedDict
from .utils.llm_utils import TextChatMessage


class RagState(TypedDict):
    # === Core Input/Output ===
    question: str                                 
    conversation_history: List[TextChatMessage]   
    final_response: str

    intents: Dict[str, Any]

    # === Document Retrieval ===
    raw_documents: List[Dict[str, Any]]
    retrieval_keywork: List[str]
    relevant_context: str

    # === Workflow Control ===
    current_status: str
    error_count: int

    # === Processing Metadata ===
    processing_steps: List[str]
    execution_metadata: Dict[str, Any]


    generated_answer: str
    cache: List[Any]

    # cost
    total_token: int  

