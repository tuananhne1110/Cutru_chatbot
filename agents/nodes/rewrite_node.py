import time
import asyncio
from agents.utils.query_rewriter import QueryRewriter
from agents.utils.context_manager import context_manager
from agents.state import ChatState

query_rewriter = QueryRewriter()

async def rewrite_query_with_context(state: ChatState) -> ChatState:
    start_time = time.time()
    question = state["question"]
    messages = state["messages"]
    messages_dict = []
    for m in messages:
        if hasattr(m, 'type') and hasattr(m, 'content'):
            role = 'user' if getattr(m, 'type', None) == 'human' else 'assistant'
            messages_dict.append({'role': role, 'content': m.content})
        elif isinstance(m, dict):
            messages_dict.append(m)
    loop = asyncio.get_running_loop()
    context_string, _ = await loop.run_in_executor(None, context_manager.process_conversation_history, messages_dict, question)
    rewritten = await loop.run_in_executor(None, query_rewriter.rewrite_with_context, question, context_string)
    state["rewritten_query"] = rewritten
    duration = time.time() - start_time
    state["processing_time"]["query_rewriting"] = duration
    return state 