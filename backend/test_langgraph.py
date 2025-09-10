

# ------------------------------------------------------------- #
# Test lịch sử 
# ------------------------------------------------------------- #

# from langgraph_rag.nodes import *
# from langgraph_rag.utils.config_utils import BaseConfig

# if __name__ == "__main__":
#     question = "xin chào tôi tên là văn tôi sinh năm 1999"

#     initial_state = create_default_rag_state(
#         question=question.lower(),
#         conversation_history=[]
#     )
#     global_config = BaseConfig()
#     rag_workflow_node =  RAGWorkflowNodes(global_config=global_config)
#     rag_workflow_node.input_validation_node(initial_state)
#     rag_workflow_node.query_analysis_node(initial_state)
#     rag_workflow_node.document_retrieval_node(initial_state)
#     rag_workflow_node.answer_generation_node(initial_state)
#     rag_workflow_node.output_validation_node(initial_state)
#     print(initial_state['final_response'])

#     question = "Chỗ nào không được phép đăng ký tạm trú"
#     initial_state['question'] = question.lower()
#     rag_workflow_node.input_validation_node(initial_state)
#     rag_workflow_node.query_analysis_node(initial_state)
#     rag_workflow_node.document_retrieval_node(initial_state)
#     rag_workflow_node.answer_generation_node(initial_state)
#     rag_workflow_node.output_validation_node(initial_state)
#     print(initial_state['final_response'])

# ------------------------------------------------------------- #
# Test trả lời trên cli liên tục
# ------------------------------------------------------------- #


# # # run_cli_chat.py
# from typing import List
# from src.langgraph_rag.utils.llm_utils import TextChatMessage
# from src.langgraph_rag.utils.config_utils import BaseConfig
# from src.langgraph_rag.nodes import RAGWorkflowNodes, create_default_rag_state
# EXIT_CMDS = {"exit", "quit", ":q", "/q"}
# RESET_CMDS = {"/reset", "/clear"}

# def run_cli_chat():
#     print("=== CLI RAG Chat (gõ 'exit' để thoát, '/reset' để xoá lịch sử) ===")
#     global_config = BaseConfig()
#     rag_workflow_node = RAGWorkflowNodes(global_config=global_config)

#     conversation_history: List[TextChatMessage] = []
#      # Khởi tạo state cho lượt hiện tại, truyền lịch sử đang có
#     state = create_default_rag_state(
#         question="",              # hoặc user_input.lower() nếu bạn muốn
#         conversation_history=conversation_history
#     )
#     while True:
#         try:
#             user_input = input("Bạn: ").strip()
#             state['question'] = user_input
#         except (EOFError, KeyboardInterrupt):
#             print("\nTạm biệt!")
#             break

#         if not user_input:
#             continue
#         low = user_input.lower()
#         if low in EXIT_CMDS:
#             print("Tạm biệt!")
#             break
#         if low in RESET_CMDS:
#             conversation_history.clear()
#             print("(✓) Đã xoá lịch sử hội thoại.")
#             continue


#         # Chạy pipeline các node
#         try:
#             rag_workflow_node.input_validation_node(state)
#             rag_workflow_node.query_analysis_node(state)
#             rag_workflow_node.document_retrieval_node(state)
#             rag_workflow_node.answer_generation_node(state)
#             rag_workflow_node.output_validation_node(state)
#         except Exception as e:
#             print(f"[Lỗi] Pipeline gặp sự cố: {e}")
#             continue

#         # Lấy câu trả lời cuối cùng
#         answer = state.get("final_response") or "(Không có câu trả lời phù hợp.)"
#         print(f"Trợ lý:\n{answer}\n")

#         # LƯU LỊCH SỬ: thêm user + assistant vào conversation_history cho lượt sau
#         conversation_history.append({"role": "user", "content": user_input})
#         conversation_history.append({"role": "assistant", "content": answer})


# if __name__ == "__main__":
#     run_cli_chat()

# ------------------------------------------------------------- #
# Test câu trả lời
# ------------------------------------------------------------- #


from src.langgraph_rag.workflows import create_rag_workflow
from src.langgraph_rag.utils.config_utils import BaseConfig
from src.langgraph_rag.nodes import RAGWorkflowNodes, create_default_rag_state


# global_config = BaseConfig()
# nodes = RAGWorkflowNodes(global_config=global_config)
# app = create_rag_workflow(nodes)

# state = create_default_rag_state(question="làm thế nào để gia hạn tạm trú nhỉ?", conversation_history=[])
# result = app.invoke(state)
# print(result["final_response"])
# print(result['conversation_history'])
# # "thủ tục 'cấp thẻ tạm trú cho người nước ngoài tại cục quản lý xuất nhập cảnh, bộ công an' gồm những giấy tờ gì ?"
#

import time
from langfuse import get_client
LANGFUSE = get_client()

global_config = BaseConfig()
nodes = RAGWorkflowNodes(global_config=global_config)
app = create_rag_workflow(nodes)

state = create_default_rag_state(
    question="Hồ sơ gia hạn tạm trú gồm những giấy tờ gì ?",
    conversation_history=[]
)

with LANGFUSE.start_as_current_span(name="workflow.invoke") as sp:
    sp.update(input={"question": state["question"][:200]})
    t0 = time.perf_counter()
    result = app.invoke(state)
    dt = time.perf_counter() - t0
    sp.update(output={
        "answer_preview": (result.get("final_response") or "")[:200],
        "latency_seconds": round(dt, 3),
    })

print(result["final_response"])
print(result["total_token"])

print(f"⏱️ Latency: {dt:.3f} s (đã log vào Langfuse)")