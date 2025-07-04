"""
LangGraph Implementation cho RAG System
Tích hợp LangGraph và LangChain vào hệ thống chatbot hiện tại
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel
import logging
import time
from langchain_core.runnables import RunnableConfig
from typing import cast

# Import existing components
from agents.intent_detector import intent_detector, IntentType
from agents.query_rewriter import QueryRewriter
from agents.context_manager import context_manager
from agents.prompt_manager import prompt_manager
from agents.guardrails import Guardrails
from services.embedding import get_embedding
from services.qdrant_service import search_qdrant
from services.llm_service import call_llm_full
from services.reranker_service import get_reranker

logger = logging.getLogger(__name__)

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class ChatState(TypedDict):
    """State cho LangGraph chat system"""
    messages: List[BaseMessage]
    question: str
    session_id: str
    intent: Optional[IntentType]
    confidence: Optional[float]
    context_docs: List[Document]
    rewritten_query: Optional[str]
    sources: List[Dict[str, Any]]
    answer: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    processing_time: Dict[str, float]
    prompt: Optional[str]  # Add prompt for streaming

class ConversationMemory(BaseModel):
    """Memory cho conversation context"""
    session_id: str
    messages: List[BaseMessage]
    context_summary: Optional[str]
    relevant_entities: List[str]
    conversation_turns: int

# ============================================================================
# GRAPH NODES
# ============================================================================

class RAGNodes:
    """Các nodes cho RAG system với LangGraph"""
    
    def __init__(self):
        self.intent_detector = intent_detector
        self.query_rewriter = QueryRewriter()
        self.context_manager = context_manager
        self.prompt_manager = prompt_manager
        self.guardrails = Guardrails()
        
    def set_intent(self, state: ChatState) -> ChatState:
        question = state["question"]
        intent, metadata = self.intent_detector.detect_intent(question)
        state["intent"] = intent
        state["confidence"] = metadata.get("confidence", 0.0)
        return state
    
    def route_by_intent(self, state: ChatState) -> str:
        intent = state["intent"]
        if intent is None:
            return "general_search"
        if intent.value == "law":
            return "law_search"
        elif intent.value == "form":
            return "form_search"
        elif intent.value == "procedure":
            return "procedure_search"
        else:
            return "general_search"
    
    def rewrite_query_with_context(self, state: ChatState) -> ChatState:
        """Rewrite query với conversation context"""
        start_time = time.time()
        question = state["question"]
        messages = state["messages"]
        # Convert List[BaseMessage] to List[Dict] for context_manager
        messages_dict = []
        for m in messages:
            if hasattr(m, 'type') and hasattr(m, 'content'):
                role = 'user' if getattr(m, 'type', None) == 'human' else 'assistant'
                messages_dict.append({'role': role, 'content': m.content})
            elif isinstance(m, dict):
                messages_dict.append(m)
        context_string, _ = self.context_manager.process_conversation_history(messages_dict, question)
        rewritten = self.query_rewriter.rewrite_with_context(question, context_string)
        state["rewritten_query"] = rewritten
        duration = time.time() - start_time
        state["processing_time"]["query_rewriting"] = duration
        logger.info(f"[LangGraph] Query rewriting: {duration:.4f}s")
        logger.info(f"[LangGraph] Query: {question} -> {rewritten}")
        return state
    
    def retrieve_context(self, state: ChatState) -> ChatState:
        """Retrieve context documents"""
        start_time = time.time()
        query = state.get("rewritten_query") or state["question"] or ""
        intent = state["intent"]
        confidence = state["confidence"] if state["confidence"] is not None else 0.0
        # Ensure intent is not None and confidence is str if required
        if intent is None:
            raise ValueError("Intent must not be None in retrieve_context")
        # If get_search_collections expects str for confidence, convert
        collections = intent_detector.get_search_collections(intent, str(confidence))
        logger.info(f"[Retrieval] Query: {query}")
        logger.info(f"[Retrieval] Intent: {intent}, Collections: {collections}")
        embedding = get_embedding(query)
        logger.info(f"[Retrieval] Embedding (first 5): {embedding[:5]}... (dim={len(embedding)})")
        all_docs = []
        for collection in collections:
            results = search_qdrant(collection, embedding, limit=15)
            logger.info(f"[Retrieval] Collection: {collection}, Results: {len(results)}")
            docs = [Document(page_content=r.payload.get("text", ""), metadata=r.payload) for r in results]
            all_docs.extend(docs)
        logger.info(f"[Retrieval] Total docs before rerank: {len(all_docs)}")
        if all_docs:
            reranker = get_reranker()
            reranked_docs = reranker.rerank(
                query=query or "",
                documents=[{"content": doc.page_content} for doc in all_docs],
                top_k=15
            )
            logger.info(f"[Retrieval] Docs after rerank: {len(reranked_docs)}")
            for i, doc in enumerate(all_docs[:len(reranked_docs)]):
                doc.metadata["rerank_score"] = reranked_docs[i].get("rerank_score", 0.0)
            # Log chi tiết top 3 tài liệu
            for idx, doc in enumerate(all_docs[:3]):
                meta = doc.metadata
                logger.info(f"[Retrieval] Top doc {idx+1}: law_name={meta.get('law_name')}, article={meta.get('article')}, chapter={meta.get('chapter')}, score={meta.get('rerank_score')}, content={doc.page_content}")
        state["context_docs"] = all_docs[:15]
        duration = time.time() - start_time
        state["processing_time"]["context_retrieval"] = duration
        logger.info(f"[LangGraph] Context retrieval: {duration:.4f}s - {len(all_docs)} docs")
        return state
    
    def generate_answer(self, state: ChatState) -> ChatState:
        """Generate answer với context (chỉ tạo prompt, không gọi LLM ở đây)"""
        start_time = time.time()
        question = state["question"]
        docs = state["context_docs"]
        intent = state["intent"]
        # create_dynamic_prompt expects IntentType
        prompt = self.prompt_manager.create_dynamic_prompt(
            question=question,
            chunks=[doc.metadata for doc in docs],
            intent=intent
        )
        state["prompt"] = prompt  # Store prompt for streaming
        state["answer"] = None
        state["sources"] = []
        duration = time.time() - start_time
        state["processing_time"]["answer_generation"] = duration
        logger.info(f"[LangGraph] Answer prompt generated: {duration:.4f}s")
        return state
    
    def validate_output(self, state: ChatState) -> ChatState:
        """Validate output với guardrails"""
        start_time = time.time()
        
        answer = state["answer"] or ""
        
        # Guardrails check
        output_safety = self.guardrails.validate_output(answer)
        if not output_safety["is_safe"]:
            fallback_msg = self.guardrails.get_fallback_message(output_safety["block_reason"])
            state["answer"] = fallback_msg
            state["error"] = "output_validation_failed"
            logger.warning(f"[LangGraph] Output validation failed: {output_safety['block_reason']}")
        
        # Log timing
        duration = time.time() - start_time
        state["processing_time"]["output_validation"] = duration
        logger.info(f"[LangGraph] Output validation: {duration:.4f}s")
        
        return state
    
    def update_memory(self, state: ChatState) -> ChatState:
        """Update conversation memory"""
        start_time = time.time()
        session_id = state["session_id"]
        messages = state["messages"]
        if state["answer"]:
            messages.append(AIMessage(content=state["answer"]))
        # Convert List[BaseMessage] to List[Dict] for context_manager
        messages_dict = []
        for m in messages:
            if hasattr(m, 'type') and hasattr(m, 'content'):
                role = 'user' if getattr(m, 'type', None) == 'human' else 'assistant'
                messages_dict.append({'role': role, 'content': m.content})
            elif isinstance(m, dict):
                messages_dict.append(m)
        _, processed_turns = self.context_manager.process_conversation_history(messages_dict, state["question"])
        context_summary = None
        if processed_turns:
            context_summary = " | ".join([t.content for t in processed_turns])
        state["messages"] = messages
        state["metadata"]["context_summary"] = context_summary
        state["metadata"]["conversation_turns"] = len(messages) // 2
        duration = time.time() - start_time
        state["processing_time"]["memory_update"] = duration
        logger.info(f"[LangGraph] Memory update: {duration:.4f}s")
        return state

# ============================================================================
# WORKFLOW CONSTRUCTION
# ============================================================================

def create_rag_workflow():
    """Tạo RAG workflow với LangGraph"""
    rag_nodes = RAGNodes()
    workflow = StateGraph(ChatState)
    workflow.add_node("set_intent", rag_nodes.set_intent)
    workflow.add_node("rewrite", rag_nodes.rewrite_query_with_context)
    workflow.add_node("retrieve", rag_nodes.retrieve_context)
    workflow.add_node("generate", rag_nodes.generate_answer)
    workflow.add_node("validate", rag_nodes.validate_output)
    workflow.add_node("update_memory", rag_nodes.update_memory)
    workflow.add_edge(START, "set_intent")
    workflow.add_conditional_edges(
        "set_intent",
        rag_nodes.route_by_intent,
        {
            "law_search": "rewrite",
            "form_search": "rewrite", 
            "procedure_search": "rewrite",
            "general_search": "rewrite"
        }
    )
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", "update_memory")
    workflow.add_edge("update_memory", END)
    app = workflow.compile(checkpointer=MemorySaver())
    return app

# ============================================================================
# LANGCHAIN INTEGRATION
# ============================================================================

class LangChainRAGComponents:
    """LangChain components cho RAG"""
    
    def __init__(self):
        # Initialize existing components
        self.embeddings = None  # Will be initialized with existing embedding service
        self.memory = None  # Will be initialized with existing context manager
        
    def create_conversational_chain(self):
        """Tạo conversational retrieval chain"""
        # This would integrate with existing components
        # For now, return a simple chain structure
        return {
            "type": "conversational_chain",
            "description": "LangChain conversational retrieval chain"
        }
    
    def create_retrieval_chain(self, intent: str):
        """Tạo retrieval chain cho intent cụ thể"""
        return {
            "type": "retrieval_chain",
            "intent": intent,
            "description": f"LangChain retrieval chain for {intent}"
        }

# ============================================================================
# MAIN WORKFLOW INSTANCE
# ============================================================================

# Create workflow instance
rag_workflow = create_rag_workflow()
langchain_components = LangChainRAGComponents()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def convert_messages_to_langchain(messages: List[Dict]) -> List[BaseMessage]:
    """Convert messages từ format hiện tại sang LangChain format"""
    langchain_messages = []
    
    for msg in messages:
        if msg.get('role') == 'user':
            langchain_messages.append(HumanMessage(content=msg.get('content', '')))
        elif msg.get('role') == 'assistant':
            langchain_messages.append(AIMessage(content=msg.get('content', '')))
    
    return langchain_messages

def create_initial_state(question: str, messages: List[Dict], session_id: str) -> ChatState:
    """Tạo initial state cho LangGraph workflow"""
    # Convert messages
    langchain_messages = convert_messages_to_langchain(messages)
    # Add current question
    langchain_messages.append(HumanMessage(content=question))
    return {
        "messages": langchain_messages,
        "question": question,
        "session_id": session_id,
        "intent": None,
        "confidence": None,
        "context_docs": [],
        "rewritten_query": None,
        "sources": [],
        "answer": None,
        "error": None,
        "metadata": {},
        "processing_time": {},
        "prompt": None
    }  # type: ignore

def extract_results_from_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract kết quả từ state"""
    return {
        "answer": state.get("answer", ""),
        "sources": state.get("sources", []),
        "intent": state.get("intent"),
        "confidence": state.get("confidence"),
        "processing_time": state.get("processing_time", {}),
        "error": state.get("error")
    }

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example usage của LangGraph workflow"""
    
    # Sample data
    question = "Tôi muốn hỏi về thủ tục đăng ký thường trú"
    messages = [
        {"role": "user", "content": "Xin chào"},
        {"role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì cho bạn?"}
    ]
    session_id = "test-session-123"
    
    # Create initial state
    initial_state = create_initial_state(question, messages, session_id)
    
    # Run workflow
    config = cast(RunnableConfig, {"configurable": {"thread_id": session_id}})
    result = await rag_workflow.ainvoke(initial_state, config=config)
    
    # Extract results
    results = extract_results_from_state(result)
    print("=== LangGraph RAG Results ===")
    print(f"Answer: {results['answer']}")
    print(f"Intent: {results['intent']}")
    print(f"Confidence: {results['confidence']}")
    print(f"Sources: {len(results['sources'])}")
    print(f"Processing time: {results['processing_time']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage()) 