from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.langgraph_chat import router as langgraph_chat_router
from src.routers import health
from src.routers.reader_cccd import router as reader_router
from src.routers.ct01 import router as ct01_router
from src.routers.voice_to_text import router as voice_to_text_router

app= FastAPI(title="test Middleware")

# chú ý khi triển khai thực tế thì không nên chọn tất cả "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(langgraph_chat_router)
app.include_router(health.router)
app.include_router(reader_router)
app.include_router(ct01_router)
app.include_router(voice_to_text_router)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
