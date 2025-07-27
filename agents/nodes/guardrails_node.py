from agents.state import ChatState
from agents.guardrails.guardrails import Guardrails
import time
import traceback
import logging

guardrails = Guardrails()
logger = logging.getLogger(__name__)

async def guardrails_input(state: ChatState) -> ChatState:
    start_time = time.time()
    question = state["question"]
    
    logger.info(f"[Guardrails] Validating input: {question[:50]}...")
    
    result = guardrails.validate_input(question)
    
    try:
        if not result["is_safe"]:
            logger.warning(f"[Guardrails] Input blocked: {result['block_reason']}")
            # Set answer và error để dừng workflow
            state["answer"] = guardrails.get_fallback_message(result["block_reason"])
            state["error"] = "input_validation_failed"
            state["processing_time"]["guardrails_input"] = time.time() - start_time
            logger.info(f"[Guardrails] Workflow stopped due to unsafe input")
            return state
        else:
            logger.info(f"[Guardrails] Input passed validation")
    except Exception as e:
        logger.error(f"[Guardrails] Exception in input validation: {e}")
        tb = traceback.format_exc()
        state["error"] = "input_validation_exception"
    
    duration = time.time() - start_time
    state["processing_time"]["guardrails_input"] = duration
    logger.info(f"[Guardrails] Input validation: {duration:.4f}s")
    
    return state 