## 🛠️ Workflow Chi Tiết Toàn Bộ Hệ Thống (Cập nhật mới nhất)

### 1. Luồng Xử Lý Tổng Thể (LangGraph-based)

```mermaid
graph TD;
  A["User (Frontend - React)"] -->|"Gửi câu hỏi + chat history qua API /chat/stream"| B["Backend (FastAPI, LangGraph)"]
  B --> C0["LangGraph RAG Workflow"]
  C0 --> C1["Context Manager: Xử lý conversation history"]
  C1 --> C2["Semantic Cache (raw query, GTE embedding)"]
  C2 -- "Hit" --> Z["Trả kết quả từ semantic cache"]
  C2 -- "Miss" --> C3["LlamaGuard Input: Kiểm tra an toàn đầu vào"]
  C3 --> C4["Query Rewriter: Làm sạch, paraphrase với context (BARTpho), paraphrase cache"]
  C4 --> C5["Semantic Cache (normalized query, GTE embedding)"]
  C5 -- "Hit" --> Z
  C5 -- "Miss" --> C6["Intent Detector: Phân loại câu hỏi"]
  C6 --> C7["Embedding: Sinh vector (Alibaba GTE)"]
  C7 --> C8["Qdrant: Semantic Search (4 collections, 25 candidates)"]
  C8 --> C9["BGE Reranker: Cross-encoder reranking (top 15)"]
  C9 --> C10["Prompt Manager: Tạo prompt động"]
  C10 --> C11["Context Manager: Tạo optimized prompt với conversation context"]
  C11 --> C12["LLM (DeepSeek): Sinh câu trả lời (streaming)"]
  C12 --> C13["LlamaGuard Output: Kiểm tra an toàn đầu ra"]
  C13 -->|"Trả kết quả từng phần (stream)"| A
  B --> D["Supabase (PostgreSQL): Lưu lịch sử chat, metadata"]
```

**Lưu ý:**
- Tất cả các endpoint chat (`/chat/`, `/chat/stream`, v.v.) hiện tại đều sử dụng LangGraph làm workflow chính.
- Các endpoint cũ đã bị deprecate và trả về lỗi 410 Gone.

### 2. Mô Tả Chi Tiết Từng Bước (LangGraph-based)

1. **Frontend (React 18)**
   - Người dùng nhập câu hỏi, gửi request qua API `/chat/` hoặc `/chat/stream`.
   - Gửi kèm `messages` array chứa lịch sử hội thoại.
   - Hiển thị kết quả trả về, lịch sử chat, trạng thái đang xử lý.

2. **Backend (FastAPI + LangGraph)**
   - Nhận request, sinh session_id nếu chưa có.
   - **LangGraph RAG Workflow:**
     - Tất cả các bước xử lý (context, cache, guardrails, rewriting, search, rerank, prompt, LLM, lưu lịch sử) được thực hiện trong workflow LangGraph.
     - Xử lý context, semantic cache, guardrails, query rewriting, intent detection, embedding, Qdrant search, BGE reranking, prompt, LLM, guardrails output, lưu cache và lịch sử.
   - Trả kết quả về frontend (answer, sources, intent, confidence, timestamp).

3. **Deprecation**
   - Các endpoint cũ trong `/chat` (trước đây không dùng LangGraph) đã bị vô hiệu hóa và trả về mã lỗi 410 Gone.
   - Vui lòng sử dụng endpoint `/chat` mới (LangGraph-powered).

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

