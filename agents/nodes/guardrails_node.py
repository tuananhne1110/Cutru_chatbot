from agents.state import ChatState
from agents.guardrails.guardrails import Guardrails
import time
import traceback

guardrails = Guardrails()

async def guardrails_input(state: ChatState) -> ChatState:
    start_time = time.time()
    result = guardrails.validate_input(state["question"])
    try:
        if not result["is_safe"]:
            state["answer"] = guardrails.get_fallback_message(result["block_reason"])
            state["error"] = "input_validation_failed"
        else:
            pass
    except Exception as e:
        tb = traceback.format_exc()
        state["error"] = "input_validation_exception"
    return state 