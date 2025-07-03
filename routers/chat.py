from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import uuid
import time
import json
import logging
from models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse, Source
from services.embedding import get_embedding
from services.qdrant_service import search_qdrant
from services.llm_service import call_llm_stream, call_llm_full
from services.supabase_service import save_chat_message, get_chat_history, create_chat_session
from services.reranker_service import get_reranker
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_config import supabase
from agents.query_rewriter import QueryRewriter
from agents.guardrails import Guardrails
from agents.intent_detector import intent_detector
from agents.prompt_manager import prompt_manager
from agents.context_manager import context_manager
from services.cache_service import get_cached_result, set_cached_result, get_cached_paraphrase, set_cached_paraphrase, get_semantic_cached_result, set_semantic_cached_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Collections cho từng loại nội dung
COLLECTIONS = {
    "law": "legal_chunks",
    "form": "form_chunks",
    "term": "term_chunks",
    "procedure": "procedure_chunks"
}

query_rewriter = QueryRewriter()
guardrails = Guardrails()

def search_multiple_collections(query_embedding, intent, confidence, original_query=""):
    """
    Search trong nhiều collections dựa trên intent với BGE reranking
    
    Args:
        query_embedding: Vector embedding của câu hỏi
        intent: Intent đã detect
        confidence: Độ tin cậy của detection
        original_query: Câu hỏi gốc để sử dụng cho reranking
        
    Returns:
        List: Kết quả search từ các collections đã được rerank
    """
    collections = intent_detector.get_search_collections(intent, confidence)
    weights = intent_detector.get_search_weights(intent, confidence)
    
    all_results = []
    
    for collection in collections:
        if collection in COLLECTIONS.values():
            results = search_qdrant(collection, query_embedding, limit=15)  # Tăng limit để có nhiều candidates cho reranking
            # Áp dụng trọng số cho collection này
            for result in results:
                result.score = result.score * weights.get(collection, 1.0)
            all_results.extend(results)
    
    # Sắp xếp theo score và lấy top results ban đầu
    all_results.sort(key=lambda x: x.score, reverse=True)
    initial_results = all_results[:25]  # Lấy nhiều hơn để rerank
    
    # Áp dụng BGE reranking nếu có query gốc
    if original_query and initial_results:
        try:
            # Chuẩn bị documents cho reranking
            documents = []
            for result in initial_results:
                doc = result.payload.copy()
                if 'text' in doc:
                    doc['content'] = doc['text']
                documents.append(doc)
            
            # Rerank với BGE
            reranker = get_reranker()
            reranked_docs = reranker.rerank(
                query=original_query,
                documents=documents,
                top_k=15,  
                batch_size=16
            )
            
            # Chuyển đổi lại thành format kết quả
            reranked_results = []
            for doc in reranked_docs:
                # Tìm result gốc tương ứng
                for result in initial_results:
                    if result.payload.get('text') == doc.get('content') or result.payload.get('content') == doc.get('content'):
                        # Cập nhật score với rerank score
                        result.score = doc.get('rerank_score', result.score)
                        reranked_results.append(result)
                        break
            
            logger.info(f"[Reranking] Applied BGE reranking to {len(reranked_docs)} documents")
            return reranked_results
            
        except Exception as e:
            logger.error(f"[Reranking] Error during reranking: {e}, using original results")
            return initial_results[:15]
    
    return initial_results[:15]  # Giới hạn 15 kết quả

def process_chat_request(request: ChatRequest, is_streaming: bool = False):
    """
    Xử lý chung cho cả streaming và non-streaming chat
    
    Args:
        request: ChatRequest object
        is_streaming: True nếu là streaming request
        
    Returns:
        Dict: Kết quả xử lý
    """
    total_start = time.time()
    session_id = request.session_id or str(uuid.uuid4())
    if not request.session_id:
        create_chat_session(session_id)
    
    # Log bắt đầu xử lý
    logger.info(f"=== CHAT REQUEST PROCESSING ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Question: {request.question}")
    logger.info(f"Has messages: {bool(getattr(request, 'messages', None))}")
    logger.info(f"Is streaming: {is_streaming}")
    
    # (1) Xử lý context hội thoại
    t0 = time.time()
    conversation_messages = getattr(request, 'messages', None) or []
    context_string, processed_turns = context_manager.process_conversation_history(
        conversation_messages, request.question
    )
    t1 = time.time()
    logger.info(f"[Timing] Context processing: {t1-t0:.4f}s")
    
    # Log context processing
    context_manager.log_context_processing(
        conversation_messages or [], processed_turns, context_string, request.question
    )
    
    # (2) Semantic cache với raw query
    t0 = time.time()
    raw_embedding = get_embedding(request.question)
    t1 = time.time()
    logger.info(f"[Timing] Raw Embedding: {t1-t0:.4f}s")
    raw_sem_cache = get_semantic_cached_result(raw_embedding)
    if raw_sem_cache:
        answer = raw_sem_cache['answer']
        sources = [Source(**src) for src in raw_sem_cache['sources']]
        logger.info("[Semantic Cache] Trả về từ semantic cache raw query")
        return {
            'answer': answer,
            'sources': sources,
            'session_id': session_id,
            'from_cache': True
        }
    
    # (3) Guardrails check - Input validation
    t0 = time.time()
    input_safety = guardrails.validate_input(request.question, conversation_messages)
    t1 = time.time()
    logger.info(f"[Timing] Guardrails Input: {t1-t0:.4f}s")
    
    if not input_safety["is_safe"]:
        block_reason = input_safety.get("block_reason")
        if isinstance(block_reason, bool) or block_reason is None:
            block_reason_str = ""
        else:
            block_reason_str = str(block_reason)
        fallback_msg = guardrails.get_fallback_message(block_reason_str)
        safety_level = input_safety.get("safety_level")
        if hasattr(safety_level, 'value') and not isinstance(safety_level, bool):
            safety_level_value = str(getattr(safety_level, 'value', ''))
        elif isinstance(safety_level, str):
            safety_level_value = safety_level
        else:
            safety_level_value = ""
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Query không an toàn",
                "reason": block_reason_str,
                "safety_level": safety_level_value,
                "fallback_message": fallback_msg
            }
        )
    
    # (4) Query rewriting với context
    t0 = time.time()
    cached_paraphrase = get_cached_paraphrase(request.question)
    if cached_paraphrase:
        rewritten_question = cached_paraphrase
        logger.info("[Paraphrase Cache] Trả về từ paraphrase cache")
    else:
        # Sử dụng context cho query rewriting
        rewritten_question = query_rewriter.rewrite_with_context(
            request.question, context_string
        )
        set_cached_paraphrase(request.question, rewritten_question)
    t1 = time.time()
    logger.info(f"[Timing] Query rewrite with context: {t1-t0:.4f}s")
    
    # (5) Semantic cache với normalized query
    t0 = time.time()
    norm_embedding = get_embedding(rewritten_question)
    t1 = time.time()
    logger.info(f"[Timing] Norm Embedding: {t1-t0:.4f}s")
    norm_sem_cache = get_semantic_cached_result(norm_embedding)
    if norm_sem_cache:
        answer = norm_sem_cache['answer']
        sources = [Source(**src) for src in norm_sem_cache['sources']]
        logger.info("[Semantic Cache] Trả về từ semantic cache normalized query")
        return {
            'answer': answer,
            'sources': sources,
            'session_id': session_id,
            'from_cache': True
        }
    
    # (6) Intent detection
    t0 = time.time()
    intent, intent_metadata = intent_detector.detect_intent(request.question)
    t1 = time.time()
    logger.info(f"[Timing] Intent Detection: {t1-t0:.4f}s")
    logger.info(f"[Intent] Detected: {intent.value}, Confidence: {intent_metadata.get('confidence', 'unknown')}")
    
    # (7) Multi-collection search với BGE reranking
    t0 = time.time()
    results = search_multiple_collections(
        norm_embedding, 
        intent, 
        intent_metadata.get('confidence', 'low'),
        original_query=rewritten_question
    )
    t1 = time.time()
    logger.info(f"[Timing] Multi-collection search with reranking: {t1-t0:.4f}s")
    
    # Debug: In ra cấu trúc dữ liệu từ Qdrant
    if results:
        logger.info(f"[Debug] Qdrant result sample payload keys: {list(results[0].payload.keys())}")
    
    # (8) Chuẩn bị chunks cho prompt manager
    chunks = []
    sources_data = []
    
    for result in results:
        chunk_data = result.payload.copy()
        # Đảm bảo có trường 'content' hoặc 'text'
        if 'text' in chunk_data:
            chunk_data['content'] = chunk_data['text']
        elif 'content' not in chunk_data:
            continue
            
        chunks.append(chunk_data)
        
        # Chuẩn bị sources data
        source_data = {k: v for k, v in chunk_data.items() if k not in ['text', 'content']}
        sources_data.append(source_data)
    
    # (9) Tạo prompt tối ưu với context
    t0 = time.time()
    base_prompt = prompt_manager.create_dynamic_prompt(
        question=rewritten_question,
        chunks=chunks,
        intent=intent
    )
    
    # Tạo prompt tối ưu với context
    optimized_prompt = context_manager.create_optimized_prompt(
        base_prompt, context_string, rewritten_question
    )
    t1 = time.time()
    logger.info(f"[Timing] Optimized prompt creation: {t1-t0:.4f}s")
    
    # (10) Chuẩn bị sources
    sources = []
    for src in sources_data:
        # Đảm bảo các trường bắt buộc có giá trị mặc định
        safe_src = {
            "law_name": src.get("law_name", src.get("form_name", "Nguồn")),
            "article": src.get("article"),
            "chapter": src.get("chapter"),
            "clause": src.get("clause"),
            "point": src.get("point")
        }
        sources.append(Source(**safe_src))
    
    # (11) Gọi LLM
    t0 = time.time()
    if is_streaming:
        # Trả về generator cho streaming
        return {
            'prompt': optimized_prompt,
            'sources': sources,
            'session_id': session_id,
            'raw_embedding': raw_embedding,
            'norm_embedding': norm_embedding,
            'rewritten_question': rewritten_question,
            'is_streaming': True
        }
    else:
        answer = call_llm_full(optimized_prompt)
        t1 = time.time()
        logger.info(f"[Timing] LLM: {t1-t0:.4f}s")
        
        # (12) Guardrails check - Output validation
        t0 = time.time()
        output_safety = guardrails.validate_output(answer)
        t1 = time.time()
        logger.info(f"[Timing] Guardrails Output: {t1-t0:.4f}s")
        if not output_safety["is_safe"]:
            fallback_msg = guardrails.get_fallback_message(output_safety["block_reason"])
            answer = fallback_msg
        
        # (13) Lưu semantic cache cho cả raw và normalized query
        set_semantic_cached_result(raw_embedding, request.question, answer, [src.dict() for src in sources])
        set_semantic_cached_result(norm_embedding, rewritten_question, answer, [src.dict() for src in sources])
        
        # (14) Lưu chat history
        try:
            save_chat_message(
                session_id=session_id,
                question=request.question,
                answer=answer,
                sources=[src.dict() for src in sources]
            )
        except Exception as e:
            logger.error(f"Không thể lưu chat history: {e}")
        
        total_end = time.time()
        logger.info(f"[Timing] Tổng thời gian xử lý: {total_end-total_start:.4f}s")
        
        return {
            'answer': answer,
            'sources': sources,
            'session_id': session_id,
            'from_cache': False
        }

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = process_chat_request(request)
        return ChatResponse(
            answer=result['answer'],
            sources=result['sources'],
            session_id=result['session_id'],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        print(f"Exception in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        result = process_chat_request(request, is_streaming=True)
        
        # Nếu có cache, trả về ngay
        if result.get('from_cache'):
            def stream_cached():
                yield result['answer']
            return StreamingResponse(stream_cached(), media_type="text/plain")
        
        # Tạo generator function để vừa stream vừa lưu lịch sử
        def stream_with_history():
            full_answer = ""
            try:
                for chunk in call_llm_stream(result['prompt']):
                    if chunk:
                        full_answer += chunk
                    yield chunk
            except Exception as e:
                logger.error(f"Error in stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                try:
                    save_chat_message(
                        session_id=result['session_id'],
                        question=request.question,
                        answer=full_answer,
                        sources=[src.dict() for src in result['sources']]
                    )
                    # Lưu semantic cache cho cả raw và normalized query
                    set_semantic_cached_result(result['raw_embedding'], request.question, full_answer, [src.dict() for src in result['sources']])
                    set_semantic_cached_result(result['norm_embedding'], result['rewritten_question'], full_answer, [src.dict() for src in result['sources']])
                except Exception as e:
                    logger.error(f"Không thể lưu chat history: {e}")
        
        return StreamingResponse(stream_with_history(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Exception in /stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_history(session_id: str, limit: int = 50):
    try:
        messages = get_chat_history(session_id, limit)
        return ChatHistoryResponse(
            messages=messages,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session")
async def create_session():
    try:
        session_id = str(uuid.uuid4())
        result = create_chat_session(session_id)
        return {"session_id": session_id, "created": result is not None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{session_id}")
async def delete_history(session_id: str):
    try:
        # Xóa tất cả messages của session
        result = supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
        return {"deleted": True, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 