from agents.state import ChatState
from agents.guardrails.guardrails import Guardrails

guardrails = Guardrails()

async def guardrails_input(state: ChatState) -> ChatState:
    result = guardrails.validate_input(state["question"])
    if not result["is_safe"]:
        state["answer"] = guardrails.get_fallback_message(result["block_reason"])
        state["error"] = "input_validation_failed"
    return state 