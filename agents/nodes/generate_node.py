import time
import asyncio
import logging
import traceback
from agents.state import ChatState
from agents.prompt.prompt_manager import prompt_manager
from langchain_core.messages import AIMessage
from langfuse.decorators import observe, langfuse_context
import boto3
import yaml

logger = logging.getLogger(__name__)
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

def load_llm_config(yaml_path="config/config.yaml"):
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get("llm", {})
    except Exception:
        return {}
llm_cfg = load_llm_config()
prompt_version = llm_cfg.get("prompt_version", "v1")
model_name = llm_cfg.get("default_model_name", "us.meta.llama4-scout-17b-instruct-v1:0")

@observe(as_type="generation")
async def generate_answer(state: ChatState) -> ChatState:
    start_time = time.time()
    
    # Kiểm tra nếu đã có error từ guardrails
    if state.get("error") == "input_validation_failed":
        logger.info(f"[Generate] Skipping generation due to guardrails error")
        state["processing_time"]["answer_generation"] = time.time() - start_time
        return state
    
    question = state["question"]
    docs = state["context_docs"]
    intent = state["intent"]
    history = state.get("messages", [])

    if docs:
        logger.info(f"[Generate] First doc: {docs[0] if docs else 'None'}")
    if not docs:
        logger.warning(f"[LangGraph] No docs found for question: {question}")
        state["answer"] = "Xin lỗi, không tìm thấy thông tin liên quan đến câu hỏi của bạn trong cơ sở dữ liệu pháp luật hiện có. Vui lòng thử câu hỏi khác hoặc liên hệ với cơ quan chức năng có thẩm quyền để được hỗ trợ."
        logger.info(f"[Langfuse] Logging input/model/metadata: input={question}, model={model_name}")
        langfuse_context.update_current_observation(
            input=question,
            model=model_name,
            metadata={
                "session_id": state["session_id"],
                "intent": str(intent),
                "prompt_version": prompt_version,
                "system_prompt": "",
                "history": str(history[:5]),
            }
        )

        langfuse_context.update_current_observation(
            usage_details={"input": 0, "output": 0},
            cost_details={"input": 0.0, "output": 0.0, "total": 0.0}
        )

        return state
    loop = asyncio.get_running_loop()
    # Format docs để phù hợp với prompt_manager
    formatted_docs = []
    for doc in docs:
        doc_dict = {
            "content": doc.page_content,
            "page_content": doc.page_content,
            **doc.metadata
        }
        formatted_docs.append(doc_dict)
    
    prompt = prompt_manager.create_dynamic_prompt(
        question,
        formatted_docs
    )
    system_prompt = prompt_manager.prompt_templates.base_template
    state["prompt"] = prompt
    logger.info(f"[Langfuse] Logging input/model/metadata: input={prompt}, model={model_name}")
    
    langfuse_context.update_current_observation(
        input=prompt,
        model=model_name,
        metadata={
            "session_id": state["session_id"],
            "intent": str(intent),
            "prompt_version": prompt_version,
            "system_prompt": system_prompt,
            "history": str(history[:5]),
        }
    )
    token_input = 0
    token_output = 0
    try:
        from services.llm_service import call_llm_stream
        answer_chunks = []
        raw_llm_response = []
        for chunk in await loop.run_in_executor(None, lambda: list(call_llm_stream(prompt, model_name))):
            answer_chunks.append(chunk)
            raw_llm_response.append(chunk)
        answer = "".join(answer_chunks)
        state["answer"] = answer
        state["answer_chunks"] = answer_chunks 
        # Log usage details
        logger.info(f"[Langfuse] Logging usage_details={token_input}/{token_output}, cost_details=0")
        langfuse_context.update_current_observation(
            usage_details={"input": token_input, "output": token_output},
            cost_details={"input": 0.0, "output": 0.0, "total": 0.0}
        )
    except Exception as e:
        logger.error(f"[LangGraph] Error in generate_answer: {e}")
        tb = traceback.format_exc()
        state["error"] = "generation_exception"
        state["answer"] = f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"
    duration = time.time() - start_time
    state["processing_time"]["answer_generation"] = duration
    logger.info(f"[LangGraph] Answer generation: {duration:.4f}s")
    return state 