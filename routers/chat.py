from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import uuid
import time
import json
from models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse, Source
from services.embedding import get_embedding
from services.qdrant_service import search_qdrant
from services.llm_service import call_llm_stream, call_llm_full
from services.supabase_service import save_chat_message, get_chat_history, create_chat_session
from config import supabase
from agents.query_rewriter import QueryRewriter
from agents.guardrails import Guardrails
from agents.intent_detector import intent_detector
from agents.prompt_manager import prompt_manager

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

def search_multiple_collections(query_embedding, intent, confidence):
    """
    Search trong nhiều collections dựa trên intent
    
    Args:
        query_embedding: Vector embedding của câu hỏi
        intent: Intent đã detect
        confidence: Độ tin cậy của detection
        
    Returns:
        List: Kết quả search từ các collections
    """
    collections = intent_detector.get_search_collections(intent, confidence)
    weights = intent_detector.get_search_weights(intent, confidence)
    
    all_results = []
    
    for collection in collections:
        if collection in COLLECTIONS.values():
            results = search_qdrant(collection, query_embedding, limit=10)
            # Áp dụng trọng số cho collection này
            for result in results:
                result.score = result.score * weights.get(collection, 1.0)
            all_results.extend(results)
    
    # Sắp xếp theo score và lấy top results
    all_results.sort(key=lambda x: x.score, reverse=True)
    return all_results[:20]  # Giới hạn 20 kết quả

def build_conversational_prompt(messages):
    prompt = ""
    for msg in messages or []:
        if msg.get('role') == 'user':
            prompt += f"User: {msg['content']}\n"
        elif msg.get('role') == 'assistant':
            prompt += f"Assistant: {msg['content']}\n"
    prompt += "Assistant:"
    return prompt

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        total_start = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        if not request.session_id:
            create_chat_session(session_id)
        
        # Guardrails check - Input validation
        t0 = time.time()
        input_safety = guardrails.validate_input(request.question, getattr(request, 'messages', None))
        t1 = time.time()
        print(f"[Timing] Guardrails Input: {t1-t0:.4f}s")
        
        if not input_safety["is_safe"]:
            block_reason = input_safety.get("block_reason")
            # Ensure block_reason is always a string and never a bool
            if isinstance(block_reason, bool) or block_reason is None:
                block_reason_str = ""
            else:
                block_reason_str = str(block_reason)
            fallback_msg = guardrails.get_fallback_message(block_reason_str)
            safety_level = input_safety.get("safety_level")
            # Only use .value if it's an Enum, else fallback to string
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
        
        # Intent detection
        t0 = time.time()
        intent, intent_metadata = intent_detector.detect_intent(request.question)
        t1 = time.time()
        print(f"[Timing] Intent Detection: {t1-t0:.4f}s")
        print(f"[Intent] Detected: {intent.value}, Confidence: {intent_metadata.get('confidence', 'unknown')}")
        
        # Query rewriting trước khi embedding
        t0 = time.time()
        rewritten_question = query_rewriter.rewrite(request.question)
        t1 = time.time()
        print(f"[Timing] Query rewrite: {t1-t0:.4f}s")
        
        # Embedding
        t0 = time.time()
        query_embedding = get_embedding(rewritten_question)
        t1 = time.time()
        print(f"[Timing] Embedding: {t1-t0:.4f}s")
        
        # Multi-collection search
        t0 = time.time()
        results = search_multiple_collections(query_embedding, intent, intent_metadata.get('confidence', 'low'))
        t1 = time.time()
        print(f"[Timing] Multi-collection search: {t1-t0:.4f}s")
        
        # Debug: In ra cấu trúc dữ liệu từ Qdrant
        if results:
            print(f"[Debug] Qdrant result sample payload keys: {list(results[0].payload.keys())}")
        
        # Chuẩn bị chunks cho prompt manager
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
        
        # Tạo prompt động dựa trên intent và chunks
        t0 = time.time()
        prompt = prompt_manager.create_dynamic_prompt(
            question=rewritten_question,
            chunks=chunks,
            intent=intent
        )
        t1 = time.time()
        print(f"[Timing] Dynamic prompt creation: {t1-t0:.4f}s")
        
        # Gọi LLM
        t0 = time.time()
        answer = call_llm_full(prompt)
        t1 = time.time()
        print(f"[Timing] LLM: {t1-t0:.4f}s")
        
        # Guardrails check - Output validation
        t0 = time.time()
        output_safety = guardrails.validate_output(answer)
        t1 = time.time()
        print(f"[Timing] Guardrails Output: {t1-t0:.4f}s")
        
        if not output_safety["is_safe"]:
            fallback_msg = guardrails.get_fallback_message(output_safety["block_reason"])
            # Thay thế answer bằng fallback message
            answer = fallback_msg
        
        # Chuẩn bị sources
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
        
        try:
            save_chat_message(
                session_id=session_id,
                question=request.question,
                answer=answer,
                sources=[src.dict() for src in sources]
            )
        except Exception as e:
            print(f"Không thể lưu chat history: {e}")
        
        total_end = time.time()
        print(f"[Timing] Tổng thời gian xử lý: {total_end-total_start:.4f}s")
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        print(f"Exception in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    total_start = time.time()
    session_id = request.session_id or str(uuid.uuid4())
    if not request.session_id:
        create_chat_session(session_id)
    
    # Guardrails check - Input validation
    t0 = time.time()
    input_safety = guardrails.validate_input(request.question, getattr(request, 'messages', None))
    t1 = time.time()
    print(f"[Timing] Guardrails Input: {t1-t0:.4f}s")

    # Nếu cần làm rõ, trả về gợi ý mềm
    if input_safety.get("need_clarification"):
        clarification = input_safety.get("clarification_message") or "Bạn vui lòng nói rõ hơn để tôi có thể trả lời chính xác."
        return StreamingResponse((str(clarification) for clarification in [clarification]), media_type="text/plain")

    if not input_safety["is_safe"]:
        block_reason = input_safety.get("block_reason")
        # Ensure block_reason is always a string and never a bool
        if isinstance(block_reason, bool) or block_reason is None:
            block_reason_str = ""
        else:
            block_reason_str = str(block_reason)
        fallback_msg = guardrails.get_fallback_message(block_reason_str)
        safety_level = input_safety.get("safety_level")
        # Only use .value if it's an Enum, else fallback to string
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
    
    # --- Build conversational prompt từ toàn bộ messages ---
    if getattr(request, 'messages', None):
        conversational_prompt = build_conversational_prompt(request.messages)
    else:
        conversational_prompt = request.question
    # Intent detection
    t0 = time.time()
    intent, intent_metadata = intent_detector.detect_intent(request.question)
    t1 = time.time()
    print(f"[Timing] Intent Detection: {t1-t0:.4f}s")
    print(f"[Intent] Detected: {intent.value}, Confidence: {intent_metadata.get('confidence', 'unknown')}")
    
    # Query rewriting trước khi embedding
    t0 = time.time()
    rewritten_prompt = query_rewriter.rewrite(conversational_prompt)
    t1 = time.time()
    print(f"[Timing] Query rewrite: {t1-t0:.4f}s")
    
    # Embedding
    t0 = time.time()
    query_embedding = get_embedding(rewritten_prompt)
    t1 = time.time()
    print(f"[Timing] Embedding: {t1-t0:.4f}s")
    
    # Multi-collection search
    t0 = time.time()
    results = search_multiple_collections(query_embedding, intent, intent_metadata.get('confidence', 'low'))
    t1 = time.time()
    print(f"[Timing] Multi-collection search: {t1-t0:.4f}s")
    
    # Debug: In ra cấu trúc dữ liệu từ Qdrant
    if results:
        print(f"[Debug] Qdrant result sample payload keys: {list(results[0].payload.keys())}")
    
    # Chuẩn bị chunks cho prompt manager
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
    
    # Tạo prompt động dựa trên intent và chunks
    t0 = time.time()
    prompt = prompt_manager.create_dynamic_prompt(
        question=rewritten_prompt,
        chunks=chunks,
        intent=intent
    )
    t1 = time.time()
    print(f"[Timing] Dynamic prompt creation: {t1-t0:.4f}s")
    
    # Chuẩn bị sources
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
    
    # Tạo generator function để vừa stream vừa lưu lịch sử
    def stream_with_history():
        full_answer = ""
        try:
            for chunk in call_llm_stream(prompt):
                if chunk:
                    full_answer += chunk
                yield chunk
        except Exception as e:
            print(f"Error in stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Lưu lịch sử sau khi stream hoàn thành
            try:
                save_chat_message(
                    session_id=session_id,
                    question=request.question,
                    answer=full_answer,
                    sources=[src.dict() for src in sources]
                )
            except Exception as e:
                print(f"Không thể lưu chat history: {e}")
    
    # Gọi LLM stream (không đo thời gian vì là stream)
    resp = StreamingResponse(stream_with_history(), media_type="text/plain")
    total_end = time.time()
    print(f"[Timing] Tổng thời gian xử lý (trước khi stream): {total_end-total_start:.4f}s")
    return resp

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