import os
import pandas as pd

from rag.workflow import create_rag_workflow, create_default_rag_state, RAGWorkflowNodes
from config.settings import Settings


def infer_csv(input_csv: str, output_csv: str | None = None):
    """
    Đọc CSV với cột 'question' (và 'answer' nếu có), chạy RAG cho mỗi question,
    lưu phản hồi chatbot vào cột 'inference' và ghi ra file mới.
    """
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"Không tìm thấy file: {input_csv}")

    # Đọc dữ liệu
    df = pd.read_csv(input_csv, encoding="utf-8")

    print(df.info())
    if "question" not in df.columns:
        raise ValueError("File CSV phải có cột 'question'.")

    # Chuẩn bị RAG workflow (khởi tạo 1 lần để dùng lại)
    settings = Settings()
    rag_nodes = RAGWorkflowNodes(settings=settings)
    rag_workflow = create_rag_workflow(rag_nodes=rag_nodes)

    # Tạo cột inference rỗng
    df["inference"] = ""

    for idx, row in df.iterrows():
        question = str(row["question"]).strip()
        if not question:
            df.at[idx, "inference"] = ""
            continue
        print(f"### câu hỏi thứ {idx + 1} : {question}")
        # Tạo state cho từng câu hỏi (không dùng lịch sử hội thoại xuyên hàng)
        state = create_default_rag_state(
            user_query=question.lower(),
            conversation_history=[]
        )

        try:
            result = rag_workflow.invoke(state)
            answer = result.get("final_response", "Không có câu trả lời phù hợp.")
        except Exception as e:
            # Không để pipeline gãy giữa chừng
            answer = f"[Lỗi khi suy luận: {e}]"

        df.at[idx, "inference"] = answer
        print(f"[{idx+1}/{len(df)}] ✓")  # log tiến độ tối giản
        
    # Xác định đường dẫn xuất
    if output_csv is None:
        base, ext = os.path.splitext(input_csv)
        output_csv = f"{base}_with_inference{ext or '.csv'}"

    # Lưu kết quả
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"Đã lưu kết quả vào: {output_csv}")