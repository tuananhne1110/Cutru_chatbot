import time
import logging
import traceback
from agents.state import ChatState
from agents.guardrails.guardrails import Guardrails

guardrails = Guardrails()
logger = logging.getLogger(__name__)

async def validate_output(state: ChatState) -> ChatState:
    start_time = time.time()
    answer = state["answer"] or ""
    output_safety = guardrails.validate_output(answer)
    try:
        if not output_safety["is_safe"]:
            fallback_msg = guardrails.get_fallback_message(output_safety["block_reason"])
            state["answer"] = fallback_msg
            state["error"] = "output_validation_failed"
            logger.warning(f"[LangGraph] Output validation failed: {output_safety['block_reason']}")
        else:
            pass
    except Exception as e:
        tb = traceback.format_exc()
        state["error"] = "output_validation_exception"
    duration = time.time() - start_time
    state["processing_time"]["output_validation"] = duration
    logger.info(f"[LangGraph] Output validation: {duration:.4f}s")
    return state 