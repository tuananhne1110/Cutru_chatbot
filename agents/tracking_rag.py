import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uuid
import asyncio
from langsmith import trace
from workflow import create_rag_workflow
from utils.message_conversion import create_initial_state

# Khởi tạo workflow
rag_workflow = create_rag_workflow()
thread_id = str(uuid.uuid4())  # Tạo ID duy nhất cho phiên chat

# Xuất ảnh PNG
png_bytes = rag_workflow.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(png_bytes)
print("✅ Workflow graph saved as workflow.png")

# Nếu muốn xuất thêm code Mermaid
mermaid_code = rag_workflow.get_graph().draw_mermaid()
with open("workflow.mmd", "w", encoding="utf-8") as f:
    f.write(mermaid_code)
print("✅ Mermaid code saved as workflow.mmd")


async def main():
    question = "Xin chào, tôi muốn biết thủ tục đăng ký tạm trú"
    messages = []  # Lần đầu chưa có message trước đó
    session_id = thread_id  # Có thể dùng thread_id làm session_id luôn

    # Tạo state ban đầu bằng hàm khởi tạo của bạn
    initial_state = create_initial_state(
        question=question,
        messages=messages,
        session_id=session_id
    )

    with trace("RAG Workflow Test Run"):
        result = await rag_workflow.ainvoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id": thread_id
                }
            }
        )

    print("\n=== Workflow Output ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
