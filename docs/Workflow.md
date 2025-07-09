## 🛠️ Workflow Chi Tiết Toàn Bộ Hệ Thống (Cập nhật mới nhất)

### 1. Luồng Xử Lý Tổng Thể (LangGraph-based)
```mermaid
graph TD;
  A["User (Frontend - React)"] -->|"Send question + chat history via API /chat/stream"| B["Backend (FastAPI, LangGraph)"]
  B --> C0["LangGraph RAG Workflow"]
  C0 --> C1["set_intent: Phân loại intent"]
  C1 --> C2["semantic_cache: Kiểm tra cache semantic"]
  C2 --> C3["guardrails_input: Kiểm duyệt an toàn đầu vào (LlamaGuard)"]
  C3 --> C4["rewrite: Làm sạch, paraphrase câu hỏi (BARTpho)"]
  C4 --> C5["retrieve: Semantic Search (Qdrant, 4 collections, 25 candidates)"]
  C5 --> C6["generate: Tạo prompt động"]
  C6 --> C7["validate: Kiểm duyệt đầu ra (LlamaGuard Output)"]
  C7 --> C8["update_memory: Cập nhật lịch sử hội thoại"]
  C8 --> D["Supabase (PostgreSQL): Store chat history, metadata"]
  C7 -->|"Stream answer chunks"| A
```

### 2. Mô tả chi tiết từng bước

**A. Frontend (React 18)**
- Người dùng nhập câu hỏi và gửi request qua API `/chat/` hoặc `/chat/stream`.
- Gửi kèm mảng `messages` chứa lịch sử hội thoại.
- Nhận câu trả lời trả về dạng streaming (từng đoạn text), lịch sử chat và trạng thái xử lý.

**B. Backend (FastAPI + LangGraph)**
- Nhận request, sinh `session_id` nếu chưa có, chuẩn hóa lịch sử hội thoại.
- **LangGraph RAG Workflow:**
  1. **set_intent:** Phân loại intent (law, form, term, procedure, ambiguous).
  2. **semantic_cache:** Kiểm tra cache semantic (embedding) với câu hỏi gốc. Nếu trùng, trả kết quả luôn.
  3. **guardrails_input:** Kiểm duyệt an toàn đầu vào (LlamaGuard Input). Nếu vi phạm, trả về thông báo an toàn.
  4. **rewrite:** Làm sạch, paraphrase câu hỏi với context (rule-based + LLM nếu cần).
  5. **retrieve:** Tìm kiếm semantic trong các collection tương ứng (top 25).
  6. **generate:** Tạo prompt động phù hợp intent, chèn context và metadata.
  7. **validate:** Kiểm duyệt đầu ra (LlamaGuard Output).
  8. **update_memory:** Lưu lại câu hỏi, câu trả lời, nguồn, intent, v.v. vào Supabase.
- **Trả kết quả:**
  - Stream từng đoạn text về frontend, giúp UI hiển thị liên tục theo thời gian thực.

### 3. Sơ Đồ Luồng Dữ Liệu (Data Flow, LangGraph-based)

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant B as Backend (FastAPI + LangGraph)
    participant L as LangGraph Workflow
    participant S as Supabase (PostgreSQL)
    U->>B: POST /chat/ (question + messages)
    B->>L: set_intent
    L->>L: semantic_cache
    alt Cache hit
        L-->>B: Cached answer
        B-->>U: Trả kết quả
    else Cache miss
        L->>L: guardrails_input
        alt Input blocked
            L-->>B: Fallback message
            B-->>U: Trả kết quả
        else Input safe
            L->>L: rewrite
            L->>L: retrieve
            L->>L: generate
            L->>L: validate
            L->>L: update_memory
            L->>S: Lưu lịch sử chat, log
            L-->>B: Trả kết quả
            B-->>U: Stream answer chunks
        end
    end
```

### 4. Tóm tắt các bước chính

1. **set_intent:** Phân loại intent câu hỏi
2. **semantic_cache:** Trả kết quả nếu đã có trong cache semantic
3. **guardrails_input:** Kiểm duyệt an toàn đầu vào
4. **rewrite:** Làm sạch, paraphrase câu hỏi
5. **retrieve:** Semantic search + rerank
6. **generate:** Tạo prompt động
7. **validate:** Kiểm duyệt đầu ra
8. **update_memory:** Lưu lịch sử, metadata

### 5. Lưu ý
- Nếu **semantic cache hit**: trả kết quả luôn, bỏ qua các bước sau.
- Nếu **input bị block**: trả fallback message, bỏ qua các bước sau.
- Các bước còn lại thực hiện như pipeline cũ.

---


