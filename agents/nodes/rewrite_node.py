import time
import asyncio
import logging
from agents.utils.query_rewriter import query_rewriter
from agents.utils.context_manager import context_manager
from agents.utils.llm_client_wrapper import llm_client_wrapper
from agents.state import ChatState
from langfuse.decorators import observe

logger = logging.getLogger(__name__)

@observe()
async def rewrite_query_with_context(state: ChatState) -> ChatState:
    start_time = time.time()

    # Kiểm tra nếu đã có error từ guardrails
    if state.get("error") == "input_validation_failed":
        logger.info(f"[Rewrite] Skipping rewrite due to guardrails error")
        state["processing_time"]["query_rewriting"] = time.time() - start_time
        return state

    question = state["question"]
    messages = state["messages"]
    intent = state.get("intent")
    
    logger.info(f"[Rewrite] Starting query rewrite for: {question[:50]}... (intent={intent})")
    
    try:
        # Sử dụng Query Rewriter mới với LLM-based approach
        llm_client = llm_client_wrapper
        # Rewrite câu hỏi sử dụng LLM, truyền intent vào
        rewritten_question = await query_rewriter.rewrite_query_with_context(
            current_question=question,
            messages=messages,
            llm_client=llm_client,
            intent=intent
        )
        # Nếu rewrite thành công và khác với câu hỏi gốc
        if rewritten_question and rewritten_question != question:
            # Cập nhật state với câu hỏi đã rewrite
            state["original_question"] = question
            state["question"] = rewritten_question
            state["query_rewritten"] = True
        else:
            logger.info(f"[Rewrite] Query kept unchanged (already clear)")
            state["query_rewritten"] = False
        # Tạo context string cho các bước tiếp theo
        context_string, relevant_turns = context_manager.process_conversation_history(
            messages, question
        )
        state["context_string"] = context_string
        state["relevant_turns"] = relevant_turns
        logger.info(f"[Rewrite] Context created: {len(context_string)} characters")
    except Exception as e:
        logger.error(f"[Rewrite] Error in query rewrite: {e}")
        # Fallback: giữ nguyên câu hỏi gốc
        state["query_rewritten"] = False
        # Vẫn tạo context
        try:
            context_string, relevant_turns = context_manager.process_conversation_history(
                messages, question
            )
            state["context_string"] = context_string
            state["relevant_turns"] = relevant_turns
        except Exception as context_error:
            logger.error(f"[Rewrite] Error creating context: {context_error}")
            state["context_string"] = ""
            state["relevant_turns"] = []

    duration = time.time() - start_time
    state["processing_time"]["query_rewriting"] = duration
    logger.info(f"[Rewrite] Query rewriting completed in {duration:.4f}s")

    return state 