import asyncio
from agents.state import ChatState
from embeddings import get_embedding
from services.cache_service import get_semantic_cached_result

async def semantic_cache(state: ChatState) -> ChatState:
    query = state["question"]
    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(None, get_embedding, query)
    cached = await loop.run_in_executor(None, get_semantic_cached_result, embedding)
    if cached:
        state["answer"] = cached.get("answer", "")
        state["sources"] = cached.get("sources", [])
        state["error"] = None
    return state 