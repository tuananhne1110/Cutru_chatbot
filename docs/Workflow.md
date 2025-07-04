## 🛠️ Workflow Chi Tiết Toàn Bộ Hệ Thống (Cập nhật mới nhất)

### 1. Luồng Xử Lý Tổng Thể (LangGraph-based)
```mermaid
graph TD;
  A["User (Frontend - React)"] -->|"Send question + chat history via API /chat/stream"| B["Backend (FastAPI, LangGraph)"]
  B --> C0["LangGraph RAG Workflow"]
  C0 --> C1["Context Manager: Process conversation history"]
  C1 --> C2["Semantic Cache (raw query, GTE embedding)"]
  C2 -- "Hit" --> Z["Return answer from semantic cache"]
  C2 -- "Miss" --> C3["LlamaGuard Input: Input safety check"]
  C3 --> C4["Query Rewriter: Clean, paraphrase with context (BARTpho), paraphrase cache"]
  C4 --> C5["Semantic Cache (normalized query, GTE embedding)"]
  C5 -- "Hit" --> Z
  C5 -- "Miss" --> C6["Intent Detector: Classify question intent"]
  C6 --> C7["Embedding: Generate vector (Alibaba GTE)"]
  C7 --> C8["Qdrant: Semantic Search (4 collections, 25 candidates)"]
  C8 --> C9["BGE Reranker: Cross-encoder reranking (top 15)"]
  C9 --> C10["Prompt Manager: Build dynamic prompt"]
  C10 --> C11["Context Manager: Build optimized prompt with conversation context"]
  C11 --> C12["LLM (DeepSeek): Generate answer (streaming)"]
  C12 --> C13["LlamaGuard Output: Output safety check"]
  C13 -->|"Stream answer chunks"| A
  B --> D["Supabase (PostgreSQL): Store chat history, metadata"]
```

### 2. Mô Tả Chi Tiết Từng Bước (LangGraph-based)

A. **Frontend (React 18)**
   - Người dùng nhập câu hỏi, gửi request qua API `/chat/` hoặc `/chat/stream`.
   - Gửi kèm `messages` array chứa lịch sử hội thoại.
   - Nhận kết quả trả về dạng streaming (từng đoạn text), lịch sử chat, trạng thái đang xử lý.

B. **Backend (FastAPI + LangGraph)**
  1. Nhận request
    Sinh session_id nếu chưa có.
    Chuẩn hóa lịch sử hội thoại.
  
  2. LangGraph RAG Workflow
    - Context Manager: Xử lý, tóm tắt, chọn các lượt hội thoại liên quan nhất (giới hạn 3-5 turn, tóm tắt nếu quá dài).
    - Semantic Cache: Kiểm tra cache semantic (embedding) với câu hỏi gốc. Nếu có, trả kết quả luôn.
    - Guardrails Input: Kiểm tra an toàn đầu vào (LlamaGuard).
    - Query Rewriter: Làm sạch, paraphrase câu hỏi với context (rule-based + LLM nếu cần).
    - Semantic Cache (normalized): Kiểm tra cache với câu hỏi đã rewrite.
    - Intent Detector: Phân loại intent (law, form, term, procedure, ambiguous).
    - Embedding: Sinh vector embedding cho câu hỏi (PhoBERT/GTE).
    - Qdrant Search: Tìm kiếm semantic trong các collection tương ứng (top 25).
    - BGE Reranker: Rerank các kết quả bằng cross-encoder, chọn top 15.
    - Prompt Manager: Tạo prompt động phù hợp intent, chèn context, metadata.
    - LLM (DeepSeek): Sinh câu trả lời dựa trên prompt (streaming từng đoạn).
    - Guardrails Output: Kiểm tra an toàn đầu ra (LlamaGuard).
    - Lưu lịch sử: Lưu lại câu hỏi, câu trả lời, nguồn, intent, v.v. vào Supabase.
  
  3. Trả kết quả
    - Trả về frontend từng đoạn text (streaming), giúp UI hiển thị liên tục.

### 3. Sơ Đồ Luồng Dữ Liệu (Data Flow, LangGraph-based)

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant B as Backend (FastAPI + LangGraph)
    participant CM as Context Manager
    participant C as Semantic Cache
    participant P as Paraphrase Cache
    participant Q as Qdrant (Vector DB)
    participant R as BGE Reranker
    participant S as Supabase (PostgreSQL)
    participant L as LLM (DeepSeek)
    U->>B: POST /chat/ (question + messages)
    B->>CM: Process conversation history
    CM-->>B: Context string + processed turns
    B->>C: Check semantic cache (raw query)
    alt Cache hit
        C-->>B: Cached answer
        B-->>U: Trả kết quả
    else Cache miss
    B->>B: LlamaGuard Input Check
        B->>P: Check paraphrase cache
        alt Paraphrase cache hit
            P-->>B: Paraphrased query
        else Paraphrase cache miss
            B->>B: Query Rewriter with context (rule-based/BARTpho)
            B->>P: Save paraphrase
        end
        B->>C: Check semantic cache (normalized query)
        alt Cache hit
            C-->>B: Cached answer
            B-->>U: Trả kết quả
        else Cache miss
    B->>B: Intent Detection
    B->>Q: Semantic Search (intent-based, 25 candidates)
    Q-->>B: Top-25 Chunks
    B->>R: BGE Reranking (cross-encoder)
    R-->>B: Top-15 Reranked Chunks
    B->>B: Prompt Manager (context)
    B->>CM: Create optimized prompt with conversation context
    CM-->>B: Optimized prompt
    B->>L: Gọi LLM sinh câu trả lời
    L-->>B: Answer
    B->>B: LlamaGuard Output Check
    B->>S: Lưu lịch sử chat, log
            B->>C: Save semantic cache (raw + normalized)
            B-->>U: Trả kết quả
        end
    end
```

