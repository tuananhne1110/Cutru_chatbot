# agents/nodes/generate_node_graph.py
import time
import asyncio
import logging
from agents.state import ChatState
from agents.prompt.prompt_manager import prompt_manager
from langchain_core.messages import AIMessage
from langfuse.decorators import observe, langfuse_context
from services.graph_rag_service import GraphRAGService

logger = logging.getLogger(__name__)

@observe(as_type="generation")
async def generate_answer_with_graph(state: ChatState) -> ChatState:
    """Generate answer using both graph and vector contexts"""
    start_time = time.time()
    
    # Check for guardrails error
    if state.get("error") == "input_validation_failed":
        logger.info(f"[Generate] Skipping generation due to guardrails error")
        state["processing_time"]["answer_generation"] = time.time() - start_time
        return state
    
    question = state["question"]
    vector_docs = state["context_docs"]
    graph_context = state.get("graph_context", "")
    intent = state["intent"]
    history = state.get("messages", [])
    
    # Format vector context
    vector_context = ""
    if vector_docs:
        formatted_docs = []
        for doc in vector_docs:
            doc_dict = {
                "content": doc.page_content,
                "page_content": doc.page_content,
                **doc.metadata
            }
            formatted_docs.append(doc_dict)
        vector_context = prompt_manager.prompt_templates.format_context_by_category(formatted_docs)
    
    # Combine contexts
    combined_context = ""
    if graph_context and vector_context:
        combined_context = f"""THÔNG TIN TỪ KNOWLEDGE GRAPH:
{graph_context}

THÔNG TIN CHI TIẾT:
{vector_context}"""
    elif graph_context:
        combined_context = f"""THÔNG TIN TỪ KNOWLEDGE GRAPH:
{graph_context}"""
    elif vector_context:
        combined_context = vector_context
    else:
        # No context available - handle as before
        if intent == IntentType.GENERAL:
            try:
                from services.llm_service import call_llm_stream
                loop = asyncio.get_running_loop()
                answer_chunks = []
                for chunk in await loop.run_in_executor(None, lambda: list(call_llm_stream(question, "llama", max_tokens=500, temperature=0.3))):
                    answer_chunks.append(chunk)
                answer = "".join(answer_chunks)
                state["answer"] = answer
                state["answer_chunks"] = answer_chunks
                return state
            except Exception as e:
                logger.error(f"[Generate] Error generating general response: {e}")
                state["answer"] = "Xin chào! Tôi là trợ lý AI, rất vui được gặp bạn. Bạn có thể hỏi tôi về các vấn đề liên quan đến thủ tục hành chính, luật pháp, biểu mẫu hoặc các câu hỏi khác."
        else:
            state["answer"] = "Xin lỗi, không tìm thấy thông tin liên quan đến câu hỏi của bạn trong cơ sở dữ liệu pháp luật hiện có. Vui lòng thử câu hỏi khác hoặc liên hệ với cơ quan chức năng có thẩm quyền để được hỗ trợ."
        
        return state
    
    # Create enhanced prompt with combined context
    enhanced_prompt_template = """Bạn là chuyên gia pháp lý về pháp luật hành chính và cư trú tại Việt Nam.

NGUYÊN TẮC TRẢ LỜI:
- Sử dụng thông tin từ knowledge graph để hiểu mối quan hệ giữa các văn bản pháp luật
- Kết hợp thông tin chi tiết từ các điều luật cụ thể
- Trả lời NGẮN GỌN, TẬP TRUNG vào câu hỏi cụ thể
- Ưu tiên thông tin QUAN TRỌNG NHẤT và TRỰC TIẾP NHẤT với câu hỏi
- Cấu trúc: TRỰC TIẾP trả lời câu hỏi → Nêu căn cứ pháp lý chính → Kết luận ngắn gọn

{context}

CÂU HỎI: {question}

TRẢ LỜI (tận dụng cả thông tin knowledge graph và chi tiết pháp luật):"""
    
    prompt = enhanced_prompt_template.format(
        context=combined_context,
        question=question
    )
    
    state["prompt"] = prompt
    
    # Log metadata
    logger.info(f"[Generate] Using combined context: Graph={bool(graph_context)}, Vector={bool(vector_context)}")
    
    langfuse_context.update_current_observation(
        input=prompt,
        model="llama",
        metadata={
            "session_id": state["session_id"],
            "intent": str(intent),
            "prompt_version": "graph_rag_v1",
            "graph_context_length": len(graph_context) if graph_context else 0,
            "vector_context_length": len(vector_context) if vector_context else 0,
            "history": str(history[:5]),
        }
    )
    
    # Generate answer
    try:
        from services.llm_service import call_llm_stream
        loop = asyncio.get_running_loop()
        answer_chunks = []
        for chunk in await loop.run_in_executor(None, lambda: list(call_llm_stream(prompt, "llama", max_tokens=800, temperature=0.2))):
            answer_chunks.append(chunk)
        answer = "".join(answer_chunks)
        
        # Post-processing
        if len(answer) > 1500:
            cut_position = answer.rfind('.', 0, 1500)
            if cut_position == -1:
                cut_position = answer.rfind('\n', 0, 1500)
            if cut_position == -1:
                cut_position = 1500
            answer = answer[:cut_position + 1].strip()
            logger.info(f"[Generate] Truncated long answer from {len(''.join(answer_chunks))} to {len(answer)} characters")
        
        state["answer"] = answer
        state["answer_chunks"] = answer_chunks
        
        # Log usage
        langfuse_context.update_current_observation(
            usage_details={"input": 0, "output": 0},
            cost_details={"input": 0.0, "output": 0.0, "total": 0.0}
        )
        
    except Exception as e:
        logger.error(f"[Generate] Error in graph-enhanced generation: {e}")
        state["error"] = "generation_exception"
        state["answer"] = f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"
    
    duration = time.time() - start_time
    state["processing_time"]["answer_generation"] = duration
    logger.info(f"[Generate] Graph-enhanced generation: {duration:.4f}s")
    
    return state