import time
import asyncio
import logging
from agents.state import ChatState
from agents.prompt.prompt_manager import prompt_manager
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

async def generate_answer(state: ChatState) -> ChatState:
    start_time = time.time()
    question = state["question"]
    docs = state["context_docs"]
    intent = state["intent"]
    if not docs:
        logger.warning(f"[LangGraph] No docs found for question: {question}")
        state["answer"] = "Xin lỗi, không tìm thấy thông tin liên quan đến câu hỏi của bạn."
        return state
    loop = asyncio.get_running_loop()
    prompt = prompt_manager.create_dynamic_prompt(
        question,
        [{"content": doc.page_content, "page_content": doc.page_content, **doc.metadata} for doc in docs]
    )
    state["prompt"] = prompt
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
    sources = []
    for doc in docs[:3]:
        file_url = doc.metadata.get("file_url", "")
        url = doc.metadata.get("url", "")
        code = doc.metadata.get("code", "")
        title = doc.metadata.get("name", doc.metadata.get("form_name", doc.metadata.get("procedure_name", "N/A")))
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