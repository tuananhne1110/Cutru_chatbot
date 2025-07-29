from agents.state import ChatState
from agents.guardrails.guardrails import Guardrails
import time
import traceback
import os
from dotenv import load_dotenv
load_dotenv()

guardrails = Guardrails(
    guardrail_id= os.getenv("GUARDRAIL_ID"),
    guardrail_version= os.getenv("GUARDRAIL_VERSION"),
    region_name="us-east-1"
)

async def guardrails_input(state: ChatState) -> ChatState:
    start_time = time.time()
    result = guardrails.validate_input(state["question"])
    try:
        if not result["is_safe"]:
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")
            # print("_Lỗi rồi_")

            state["answer"] = guardrails.get_fallback_message(result["block_reason"])
            state["error"] = "input_validation_failed"
        else:
            pass
    except Exception as e:
        tb = traceback.format_exc()
        state["error"] = "input_validation_exception"
    return state 
