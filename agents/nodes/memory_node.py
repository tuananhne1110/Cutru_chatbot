import time
import asyncio
import logging
from agents.state import ChatState
from langchain_core.messages import AIMessage
from agents.utils.context_manager import context_manager

logger = logging.getLogger(__name__)

async def update_memory(state: ChatState) -> ChatState:
    start_time = time.time()
    session_id = state["session_id"]
    messages = state["messages"]
    if state["answer"]:
        messages.append(AIMessage(content=state["answer"]))
    messages_dict = []
    for m in messages:
        if hasattr(m, 'type') and hasattr(m, 'content'):
            role = 'user' if getattr(m, 'type', None) == 'human' else 'assistant'
            messages_dict.append({'role': role, 'content': m.content})
        elif isinstance(m, dict):
            messages_dict.append(m)
    loop = asyncio.get_running_loop()
    _, processed_turns = await loop.run_in_executor(None, context_manager.process_conversation_history, messages_dict, state["question"])
    context_summary = None
    if processed_turns:
        context_summary = " | ".join([t.content for t in processed_turns])
    state["messages"] = messages
    state["metadata"]["context_summary"] = context_summary
    state["metadata"]["conversation_turns"] = len(messages) // 2
    duration = time.time() - start_time
    state["processing_time"]["memory_update"] = duration
    logger.info(f"[LangGraph] Memory update: {duration:.4f}s")
    return state 