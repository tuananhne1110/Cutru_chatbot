from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
import logging
import time
from langchain_core.runnables import RunnableConfig
from typing import cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
# import os
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import existing components
# from agents.intent_detector import intent_detector, IntentType
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
    all_intents: List[tuple]  # Lưu tất cả intents
    context_docs: List[Document]
    rewritten_query: Optional[str]
    sources: List[Dict[str, Any]]
    answer: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    processing_time: Dict[str, float]
    prompt: Optional[str]  # Add prompt for streaming
    answer_chunks: Optional[List[str]]  # Add for streaming real chunks

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
        self._executor = ThreadPoolExecutor()
        
    async def set_intent(self, state: ChatState) -> ChatState:
        """Bước 1: Phân tích intent từ câu hỏi"""
        question = state["question"]
        intents = self.intent_detector.detect_intent(question)
        # Lưu tất cả intents để xử lý sau
        state["all_intents"] = intents
        # Lấy intent đầu tiên làm primary intent
        primary_intent = intents[0][0] if intents else IntentType.GENERAL
        state["intent"] = primary_intent
        logger.info(f"[LangGraph] All intents detected: {intents}")
        logger.info(f"[LangGraph] Primary intent: {primary_intent}")
        return state

    
    async def rewrite_query_with_context(self, state: ChatState) -> ChatState:
        """Rewrite query với conversation context"""
        start_time = time.time()
        question = state["question"]
        messages = state["messages"]
        messages_dict = []
        for m in messages:
            if hasattr(m, 'type') and hasattr(m, 'content'):
                role = 'user' if getattr(m, 'type', None) == 'human' else 'assistant'
                messages_dict.append({'role': role, 'content': m.content})
            elif isinstance(m, dict):
                messages_dict.append(m)
        loop = asyncio.get_running_loop()
        context_string, _ = await loop.run_in_executor(self._executor, self.context_manager.process_conversation_history, messages_dict, question)
        rewritten = await loop.run_in_executor(self._executor, self.query_rewriter.rewrite_with_context, question, context_string)
        state["rewritten_query"] = rewritten
        duration = time.time() - start_time
        state["processing_time"]["query_rewriting"] = duration
        logger.info(f"[LangGraph] Query rewriting: {duration:.4f}s")
        logger.info(f"[LangGraph] Query: {question} -> {rewritten}")
        return state
    
    async def retrieve_context(self, state: ChatState) -> ChatState:
        """Bước 2: Truy vấn Qdrant 1 lần với limit cao"""
        start_time = time.time()
        query = state.get("rewritten_query") or state["question"] or ""
        all_intents = state.get("all_intents", [])
        primary_intent = state["intent"]
        
        if primary_intent is None:
            raise ValueError("Intent must not be None in retrieve_context")
        
        # Lấy collections dựa trên tất cả intents
        all_collections = set()
        for intent_tuple in all_intents:
            intent, _ = intent_tuple
            collections = intent_detector.get_search_collections([(intent, query)])
            all_collections.update(collections)
        
        collections = list(all_collections)
        logger.info(f"[LangGraph] Collections to search (from all intents): {collections}")
        
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(self._executor, get_embedding, query)
        all_docs = []
        
        # Bước 2: Gọi Qdrant 1 lần với limit cao (50)
        for collection in collections:
            if collection == "general_chunks":
                continue
                
            # Tăng limit lên 50 để lấy đủ dữ liệu
            results, filter_condition = await loop.run_in_executor(self._executor, search_qdrant, collection, embedding, query, 50)
            results_list = results if isinstance(results, list) else [results]
            logger.info(f"[LangGraph] Collection {collection}: found {len(results_list)} results")
            
            # Chuyển đổi kết quả thành Document objects
            docs = []
            for r in results_list:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    docs.append(Document(page_content=content, metadata=r.payload))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    docs.append(Document(page_content=content, metadata=r))
            
            all_docs.extend(docs)
        
        # Rerank để lấy top chunks
        if all_docs:
            reranker = get_reranker()
            reranked_docs = await loop.run_in_executor(self._executor, reranker.rerank, query or "", [{"content": doc.page_content} for doc in all_docs], 50)
            for i, doc in enumerate(all_docs[:len(reranked_docs)]):
                doc.metadata["rerank_score"] = reranked_docs[i].get("rerank_score", 0.0)
        
        # Bước 3: Xử lý kết quả tại RAM - Gom nhóm theo parent_id cho LAW intent
        if primary_intent == IntentType.LAW:
            logger.info("[LangGraph] LAW intent detected - starting parent_id grouping...")
            
            # Log trước khi gom nhóm
            logger.info(f"[LangGraph] Before grouping: {len(all_docs)} docs")
            for i, doc in enumerate(all_docs[:5]):
                logger.info(f"  Doc {i+1}: id={doc.metadata.get('id')}, parent_id={doc.metadata.get('parent_id')}, type={doc.metadata.get('type')}")
            
            # Gom nhóm theo parent_id
            group_map = self._group_law_chunks_by_parent(all_docs)
            logger.info(f"[LangGraph] Grouping completed: {len(group_map)} groups")
            
            # Log chi tiết từng nhóm
            logger.info("[LangGraph] GROUP DETAILS:")
            for parent_id, group in group_map.items():
                logger.info(f"  Group {parent_id}: {len(group)} docs")
                for doc in group:
                    logger.info(f"    - {doc.metadata.get('type')} {doc.metadata.get('clause', '')} {doc.metadata.get('point', '')}: {doc.page_content[:50]}...")
            
            # Merge và format
            merged_docs = self._merge_and_format_law_chunks(group_map)
            logger.info(f"[LangGraph] After merging: {len(merged_docs)} merged docs")
            
            # Log merged docs
            logger.info("[LangGraph] MERGED DOCS:")
            for i, doc in enumerate(merged_docs):
                logger.info(f"  Merged Doc {i+1}:")
                logger.info(f"    Title: {doc.metadata.get('law_name', '')} - {doc.metadata.get('article', '')}")
                logger.info(f"    Content: {doc.page_content[:200]}...")
                logger.info("-" * 40)
            
            state["context_docs"] = merged_docs[:8]
        else:
            # Các intent khác: giữ nguyên
            state["context_docs"] = all_docs[:8]
        
        # Log debug chi tiết
        logger.info(f"[LangGraph] DEBUG: Total docs retrieved: {len(all_docs)}")
        logger.info(f"[LangGraph] DEBUG: Context docs set: {len(state['context_docs'])}")
        
        # Log chi tiết từng context doc
        logger.info("="*80)
        logger.info("[LangGraph] CONTEXT_DOCS DETAILS:")
        for i, doc in enumerate(state["context_docs"]):
            logger.info(f"Doc {i+1}:")
            logger.info(f"  Content: {doc.page_content}")
            logger.info(f"  Metadata: {doc.metadata}")
            logger.info("-"*40)
        logger.info("="*80)
        
        duration = time.time() - start_time
        state["processing_time"]["context_retrieval"] = duration
        logger.info(f"[LangGraph] Retrieval completed: {len(state['context_docs'])} docs in {duration:.4f}s")
        return state
    
    async def _enhance_law_chunks_with_parents(self, all_docs: List[Document], collection: str) -> List[Document]:
        """Tìm thêm các chunk có parent_id trùng với id của chunk đã tìm được"""
        enhanced_docs = all_docs.copy()
        
        # Lấy tất cả id từ docs đã tìm được
        retrieved_ids = set()
        for doc in all_docs:
            doc_id = doc.metadata.get("id")
            if doc_id:
                retrieved_ids.add(doc_id)
        
        # Tìm thêm các chunk có parent_id trùng với retrieved_ids
        # Tạm thời bỏ qua logic này để tránh gọi Qdrant quá nhiều
        # TODO: Implement logic tìm parent chunks hiệu quả hơn
        
        logger.info(f"[LangGraph] Enhanced docs: {len(all_docs)} -> {len(enhanced_docs)} (parent chunks enhancement disabled)")
        return enhanced_docs
    
    def _group_law_chunks_by_parent(self, all_docs: List[Document]) -> Dict[str, List[Document]]:
        """Bước 3: Nhóm chunks theo parent_id - chỉ cho LAW intent"""
        logger.info("[LangGraph] Starting _group_law_chunks_by_parent...")
        
        # Tạo map từ id → chunk để tra nhanh
        id_to_doc = {}
        for doc in all_docs:
            doc_id = doc.metadata.get("id")
            if doc_id:
                id_to_doc[doc_id] = doc
        
        logger.info(f"[LangGraph] Created id_to_doc map with {len(id_to_doc)} entries")
        
        # Nhóm theo parent_id
        group_map = {}
        for doc in all_docs:
            meta = doc.metadata
            doc_id = meta.get("id")
            parent_id = meta.get("parent_id")
            doc_type = meta.get("type", "")
            
            logger.info(f"[LangGraph] Processing doc: id={doc_id}, parent_id={parent_id}, type={doc_type}")
            
            if doc_type == "điều":
                # Nếu là điều, tạo nhóm mới
                if doc_id:
                    if doc_id not in group_map:
                        group_map[doc_id] = []
                    group_map[doc_id].append(doc)
                    logger.info(f"[LangGraph] Created new group for điều: {doc_id}")
            elif parent_id:
                # Nếu là khoản/điểm, gán vào nhóm parent
                if parent_id not in group_map:
                    group_map[parent_id] = []
                group_map[parent_id].append(doc)
                logger.info(f"[LangGraph] Added to parent group: {parent_id}")
        
        # Đảm bảo mỗi nhóm có cả điều cha (nếu có)
        for parent_id, group in group_map.items():
            if parent_id in id_to_doc and id_to_doc[parent_id] not in group:
                group.insert(0, id_to_doc[parent_id])
                logger.info(f"[LangGraph] Added parent điều to group: {parent_id}")
        
        logger.info(f"[LangGraph] Final group_map has {len(group_map)} groups")
        return group_map
    
    def _merge_and_format_law_chunks(self, group_map: Dict[str, List[Document]]) -> List[Document]:
        """Bước 4: Sắp xếp, gộp và tạo ngữ cảnh - chỉ cho LAW intent"""
        logger.info("[LangGraph] Starting _merge_and_format_law_chunks...")
        merged_docs = []
        
        for parent_id, group in group_map.items():
            if not group:
                continue
                
            logger.info(f"[LangGraph] Processing group {parent_id} with {len(group)} docs")
            
            # Sắp xếp khoản, điểm theo thứ tự
            def sort_key(doc):
                meta = doc.metadata
                clause = meta.get("clause", "")
                point = meta.get("point", "")
                # Ưu tiên điều trước, sau đó đến khoản, điểm
                if meta.get("type") == "điều":
                    return (0, 0, 0)
                try:
                    clause_num = int(clause) if clause.isdigit() else 99
                except:
                    clause_num = 99
                try:
                    point_num = ord(point.lower()) - ord('a') if point and point.isalpha() else 99
                except:
                    point_num = 99
                return (1, clause_num, point_num)
            
            group_sorted = sorted(group, key=sort_key)
            logger.info(f"[LangGraph] Sorted group {parent_id}: {[doc.metadata.get('type', '') + ' ' + doc.metadata.get('clause', '') + ' ' + doc.metadata.get('point', '') for doc in group_sorted]}")
            
            # Format lại context: Điều + các khoản/điểm
            meta = group_sorted[0].metadata
            law_name = meta.get("law_name", "")
            chapter = meta.get("chapter", "")
            article = meta.get("article", "")
            
            title = f"{law_name}"
            if chapter:
                title += f" - {chapter}"
            if article:
                title += f" - Điều {article}"
            
            logger.info(f"[LangGraph] Creating merged doc with title: {title}")
            
            content_lines = []
            for doc in group_sorted:
                m = doc.metadata
                t = m.get("type", "")
                clause = m.get("clause", "")
                point = m.get("point", "")
                
                if t == "điều":
                    content_lines.append(doc.page_content.strip())
                    logger.info(f"[LangGraph] Added điều content: {doc.page_content[:50]}...")
                elif t == "khoản":
                    content_lines.append(f"- Khoản {clause}: {doc.page_content.strip()}")
                    logger.info(f"[LangGraph] Added khoản {clause}: {doc.page_content[:50]}...")
                elif t == "điểm":
                    content_lines.append(f"  + Điểm {point}: {doc.page_content.strip()}")
                    logger.info(f"[LangGraph] Added điểm {point}: {doc.page_content[:50]}...")
                else:
                    content_lines.append(doc.page_content.strip())
                    logger.info(f"[LangGraph] Added other type {t}: {doc.page_content[:50]}...")
            
            merged_text = "\n".join(content_lines)
            merged_docs.append(Document(page_content=f"{title}\n{merged_text}", metadata=meta))
            logger.info(f"[LangGraph] Created merged doc with {len(content_lines)} content lines")
        
        logger.info(f"[LangGraph] Total merged docs created: {len(merged_docs)}")
        return merged_docs
    
    async def generate_answer(self, state: ChatState) -> ChatState:
        """Generate answer với context (sử dụng streaming thực sự nếu có)"""
        start_time = time.time()
        question = state["question"]
        docs = state["context_docs"]
        intent = state["intent"]
        
        # Log debug
        logger.info(f"[LangGraph] Generate answer started")
        logger.info(f"[LangGraph] DEBUG: Question: {question}")
        logger.info(f"[LangGraph] DEBUG: Number of docs: {len(docs)}")
        logger.info(f"[LangGraph] DEBUG: Intent: {intent}")
        
        if not docs:
            logger.warning(f"[LangGraph] No docs found for question: {question}")
            state["answer"] = "Xin lỗi, không tìm thấy thông tin liên quan đến câu hỏi của bạn."
            return state
        
        # Tạo prompt
        loop = asyncio.get_running_loop()
        logger.info(f"[LangGraph] Sắp tạo prompt với prompt_manager...")
        logger.info(f"[LangGraph] DEBUG: Sắp tạo prompt với question: {question}, số docs: {len(docs)}, intent: {intent}")
        for i, doc in enumerate(docs[:3]):
            logger.info(f"[LangGraph] DEBUG: Doc {i}: {doc.metadata}")
        # SỬA: truyền cả content vào context
        prompt = self.prompt_manager.create_dynamic_prompt(
            question,
            [{"content": doc.page_content, "page_content": doc.page_content, **doc.metadata} for doc in docs]
        )
        # logger.info("="*80)
        # logger.info("[LangGraph] PROMPT DETAILS:")
        # logger.info(f"Question: {question}")
        # logger.info(f"Number of docs: {len(docs)}")
        # logger.info(f"Prompt length: {len(prompt)}")
        # logger.info(f"Prompt content:")
        # logger.info(prompt)
        # logger.info("="*80)
        state["prompt"] = prompt  # Store prompt for streaming

        # Call LLM to generate answer
        try:
            from services.llm_service import call_llm_stream
            answer_chunks = []
            for chunk in await loop.run_in_executor(None, lambda: list(call_llm_stream(prompt, "llama"))):
                answer_chunks.append(chunk)
            answer = "".join(answer_chunks)
            logger.info(f"[LangGraph] Đã gọi xong call_llm_stream, answer[:100]: {str(answer)[:100]}")
            state["answer"] = answer
            state["answer_chunks"] = answer_chunks 
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            state["answer"] = "Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn."
            state["error"] = "llm_error"
        
        # Tạo sources từ docs
        sources = []
        for doc in docs[:3]:  # Top 3 sources
            file_url = doc.metadata.get("file_url", "")
            url = doc.metadata.get("url", "")
            code = doc.metadata.get("code", "")
            title = doc.metadata.get("name", doc.metadata.get("form_name", doc.metadata.get("procedure_name", "N/A")))
            if file_url:
                source = {
                    "title": title,
                    "code": code,
                    "file_url": file_url,
                    "url": url,
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata
                }
                sources.append(source)
            else:
                # fallback: vẫn thêm các nguồn khác nếu không có file_url
                source = {
                    "title": title,
                    "code": code,
                    "file_url": file_url,
                    "url": url,
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata
                }
                sources.append(source)
        state["sources"] = sources
        
        duration = time.time() - start_time
        state["processing_time"]["answer_generation"] = duration
        logger.info(f"[LangGraph] Answer generation: {duration:.4f}s")
        return state
    
    async def validate_output(self, state: ChatState) -> ChatState:
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
    
    async def update_memory(self, state: ChatState) -> ChatState:
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
        loop = asyncio.get_running_loop()
        _, processed_turns = await loop.run_in_executor(self._executor, self.context_manager.process_conversation_history, messages_dict, state["question"])
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

    async def semantic_cache(self, state: ChatState) -> ChatState:
        """Kiểm tra semantic cache (nếu có)"""
        from services.embedding import get_embedding
        from services.cache_service import get_semantic_cached_result
        query = state["question"]
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(self._executor, get_embedding, query)
        cached = await loop.run_in_executor(self._executor, get_semantic_cached_result, embedding)
        if cached:
            state["answer"] = cached.get("answer", "")
            state["sources"] = cached.get("sources", [])
            state["error"] = None
            # Nếu hit cache, có thể set flag để dừng sớm nếu muốn
        return state

    async def guardrails_input(self, state: ChatState) -> ChatState:
        """Kiểm tra an toàn đầu vào (LlamaGuard Input)"""
        from agents.guardrails import Guardrails
        guardrails = Guardrails()
        result = guardrails.validate_input(state["question"])
        if not result["is_safe"]:
            state["answer"] = guardrails.get_fallback_message(result["block_reason"])
            state["error"] = "input_validation_failed"
        return state

# ============================================================================
# WORKFLOW CONSTRUCTION
# ============================================================================

def create_rag_workflow():
    """Tạo RAG workflow với LangGraph"""
    rag_nodes = RAGNodes()
    workflow = StateGraph(ChatState)
    workflow.add_node("set_intent", rag_nodes.set_intent)
    workflow.add_node("semantic_cache", rag_nodes.semantic_cache)  # NEW
    workflow.add_node("guardrails_input", rag_nodes.guardrails_input)  # NEW
    workflow.add_node("rewrite", rag_nodes.rewrite_query_with_context)
    workflow.add_node("retrieve", rag_nodes.retrieve_context)
    workflow.add_node("generate", rag_nodes.generate_answer)
    workflow.add_node("validate", rag_nodes.validate_output)
    workflow.add_node("update_memory", rag_nodes.update_memory)
    workflow.add_edge(START, "set_intent")
    workflow.add_edge("set_intent", "semantic_cache")
    workflow.add_edge("semantic_cache", "guardrails_input")
    workflow.add_edge("guardrails_input", "rewrite")
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
        "all_intents": [],
        "context_docs": [],
        "rewritten_query": None,
        "sources": [],
        "answer": None,
        "error": None,
        "metadata": {},
        "processing_time": {},
        "prompt": None,
        "answer_chunks": None
    }  # type: ignore

def extract_results_from_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract kết quả từ state và in log thời gian xử lý từng bước"""
    result = {
        "answer": state.get("answer", ""),
        "sources": state.get("sources", []),
        "intent": state.get("intent"),
        "processing_time": state.get("processing_time", {}),
        "error": state.get("error")
    }
    # In log thời gian xử lý từng bước
    print("=== Thời gian xử lý từng bước ===")
    for step, t in result["processing_time"].items():
        print(f"{step}: {t:.4f} giây")
    return result