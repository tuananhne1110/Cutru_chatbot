import time
import asyncio
import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from agents.utils.intent_detector import intent_detector, IntentType
from agents.state import ChatState
from services.embedding import get_embedding
from services.qdrant_service import search_qdrant
from services.reranker_service import get_reranker
from langfuse.decorators import observe

logger = logging.getLogger(__name__)

@observe()
async def retrieve_context(state: ChatState) -> ChatState:
    start_time = time.time()
    
    # Kiểm tra nếu đã có error từ guardrails
    if state.get("error") == "input_validation_failed":
        logger.info(f"[Retrieve] Skipping retrieval due to guardrails error")
        state["processing_time"]["context_retrieval"] = time.time() - start_time
        return state
    
    query = state.get("rewritten_query") or state["question"] or ""
    # Nếu query quá ngắn hoặc là follow-up, nối với câu hỏi trước
    if len(query.split()) < 6 and len(state["messages"]) > 1:
        # Tìm câu hỏi gần nhất của user trước đó
        prev_user_msg = None
        for m in reversed(state["messages"][:-1]):
            if hasattr(m, 'type') and getattr(m, 'type', None) == 'human':
                prev_user_msg = m.content
                break
            elif isinstance(m, dict) and m.get('role') == 'user':
                prev_user_msg = m.get('content', '')
                break
        if prev_user_msg:
            query = prev_user_msg.strip() + ' ' + query.strip()
            logger.info(f"[Retrieve] Follow-up detected, merged query: {query}")
    all_intents = state.get("all_intents", [])
    primary_intent = state["intent"]
    # KHÔNG tạo trace mới ở đây nữa, chỉ tạo trace root ở node generate_answer
    if primary_intent is None:
        logger.error("[Retrieve] Intent is None. State: %s", state)
        raise ValueError("Intent must not be None in retrieve_context")
    
    # Ưu tiên primary intent, chỉ thêm các intent phụ nếu thực sự liên quan mạnh
    primary_collections = set()
    secondary_collections = set()
    
    # Thêm collection cho primary intent
    if primary_intent == IntentType.LAW:
        primary_collections.add("legal_chunks")
    elif primary_intent == IntentType.FORM:
        primary_collections.add("form_chunks")
    elif primary_intent == IntentType.TERM:
        primary_collections.add("legal_chunks")  # Chuyển term search sang legal_chunks
    elif primary_intent == IntentType.PROCEDURE:
        primary_collections.add("procedure_chunks")
    elif primary_intent == IntentType.GENERAL:
        primary_collections.add("general_chunks")
    
    # Thêm tất cả collections liên quan từ all_intents
    for intent, query in all_intents:
        if intent == IntentType.LAW:
            secondary_collections.add("legal_chunks")
        elif intent == IntentType.FORM:
            secondary_collections.add("form_chunks")
        elif intent == IntentType.TERM:
            secondary_collections.add("legal_chunks")  # Chuyển term search sang legal_chunks
        elif intent == IntentType.PROCEDURE:
            secondary_collections.add("procedure_chunks")
        elif intent == IntentType.GENERAL:
            secondary_collections.add("general_chunks")
    
    # Loại bỏ duplicates
    secondary_collections = secondary_collections - primary_collections
    
    # Kết hợp tất cả collections liên quan
    collections = list(primary_collections | secondary_collections)
    logger.info(f"[Retrieve] Collections to search (from all intents): {collections}")
    if not collections:
        logger.warning("[Retrieve] No collections found for intents")
        state["context_docs"] = []
        state["processing_time"]["context_retrieval"] = time.time() - start_time
        return state
    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(None, get_embedding, query)
    logger.info(f"[Retrieve] Getting embedding for query: {query}")
    all_docs = []
    for collection in collections:
        try:
            # Điều chỉnh search limit dựa trên số collections
            if len(collections) == 1:
                search_limit = 15  # Nếu chỉ 1 collection thì lấy nhiều hơn
            elif len(collections) == 2:
                search_limit = 8   # Nếu 2 collections thì lấy ít hơn mỗi collection
            else:
                search_limit = 6   # Nếu nhiều collections thì lấy ít nhất
            search_result = await loop.run_in_executor(None, search_qdrant, collection, embedding, query, search_limit)
            
            # search_qdrant now returns results directly (similar to vector retriever)
            results = search_result
            
            logger.info(f"[Retrieve] Found {len(results)} docs in {collection}")
            
            for r in results:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    # Thêm vector score vào metadata để tracking
                    metadata = dict(r.payload)
                    metadata["vector_score"] = getattr(r, 'score', 0.0)
                    all_docs.append(Document(page_content=content, metadata=metadata))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    metadata = dict(r)
                    metadata["vector_score"] = r.get('score', 0.0)
                    all_docs.append(Document(page_content=content, metadata=metadata))
        except Exception as e:
            logger.error(f"[Retrieve] Error searching collection {collection}: {e}")
            logger.warning(f"[Retrieve] Skipping collection: {collection}")
            continue
    logger.info(f"[Retrieve] Total docs before rerank: {len(all_docs)}")
    
    if all_docs:
        # Giới hạn số docs để rerank (tối đa 20 docs)
        docs_to_rerank = min(len(all_docs), 20)
        reranker = get_reranker()
        reranked_docs = await loop.run_in_executor(None, reranker.rerank, query or "", [{"content": doc.page_content} for doc in all_docs[:docs_to_rerank]], docs_to_rerank)
        
        # Áp dụng rerank scores và lọc theo threshold
        for i, doc in enumerate(all_docs[:len(reranked_docs)]):
            rerank_score = reranked_docs[i].get("rerank_score", 0.0)
            doc.metadata["rerank_score"] = rerank_score
        
        # Lọc chỉ lấy docs có rerank_score >= 0.3 và sắp xếp theo rerank_score
        filtered_docs = [doc for doc in all_docs if doc.metadata.get("rerank_score", 0.0) >= 0.3]
        filtered_docs.sort(key=lambda x: x.metadata.get("rerank_score", 0.0), reverse=True)
        
        logger.info(f"[Retrieve] After rerank filtering (score >= 0.3): {len(filtered_docs)} docs")
        
        # Giảm số lượng kết quả cuối cùng xuống 10-15 docs thay vì 30
        final_limit = 12
        state["context_docs"] = filtered_docs[:final_limit]
    else:
        state["context_docs"] = []
    logger.info(f"[Retrieve] Retrieval completed: {len(state['context_docs'])} docs")
    duration = time.time() - start_time
    state["processing_time"]["context_retrieval"] = duration
    logger.info(f"[Retrieve] Retrieval time: {duration:.4f}s")
    return state
