import logging
logging.basicConfig(level=logging.INFO)
# Giảm log spam cho các module phụ
logging.getLogger("agents.context_manager").setLevel(logging.WARNING)
logging.getLogger("prompt.prompt_manager").setLevel(logging.WARNING)
logging.getLogger("prompt.prompt_templates").setLevel(logging.WARNING)
logging.getLogger("services.qdrant_service").setLevel(logging.WARNING)
logging.getLogger("services.reranker_service").setLevel(logging.WARNING)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health
from routers.langgraph_chat import router as langgraph_chat_router

app = FastAPI(title="Legal Assistant API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use LangGraph as the main chat endpoint
app.include_router(langgraph_chat_router)
app.include_router(health.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 