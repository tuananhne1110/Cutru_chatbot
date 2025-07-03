## 🛠️ Workflow Chi Tiết Toàn Bộ Hệ Thống (Cập nhật mới nhất)

### 1. Luồng Xử Lý Tổng Thể

```mermaid
graph TD;
  A["User (Frontend - React)"] -->|"Gửi câu hỏi + chat history qua API /chat/"| B["Backend (FastAPI)"]
  B --> C0["Context Manager: Xử lý conversation history"]
  C0 --> C1["Semantic Cache (raw query, GTE embedding)"]
  C1 -- "Hit" --> Z["Trả kết quả từ semantic cache"]
  C1 -- "Miss" --> C2["LlamaGuard Input: Kiểm tra an toàn đầu vào"]
  C2 --> C3["Query Rewriter: Làm sạch, paraphrase với context (BARTpho), paraphrase cache"]
  C3 --> C4["Semantic Cache (normalized query, GTE embedding)"]
  C4 -- "Hit" --> Z
  C4 -- "Miss" --> C5["Intent Detector: Phân loại câu hỏi"]
  C5 --> C6["Embedding: Sinh vector (Alibaba GTE)"]
  C6 --> C7["Qdrant: Semantic Search (4 collections, 25 candidates)"]
  C7 --> C8["BGE Reranker: Cross-encoder reranking (top 15)"]
  C8 --> C9["Prompt Manager: Tạo prompt động"]
  C9 --> C10["Context Manager: Tạo optimized prompt với conversation context"]
  C10 --> C11["LLM (DeepSeek): Sinh câu trả lời"]
  C11 --> C12["LlamaGuard Output: Kiểm tra an toàn đầu ra"]
  C12 -->|"Trả kết quả"| A
  B --> D["Supabase (PostgreSQL): Lưu lịch sử chat, metadata"]
```

### 2. Mô Tả Chi Tiết Từng Bước (Cập nhật mới nhất)

1. **Frontend (React 18)**
   - Người dùng nhập câu hỏi, gửi request qua API `/chat/` hoặc `/chat/stream`.
   - Gửi kèm `messages` array chứa lịch sử hội thoại.
   - Hiển thị kết quả trả về, lịch sử chat, trạng thái đang xử lý.

2. **Backend (FastAPI) - Unified Processing**
   - Nhận request, sinh session_id nếu chưa có.
   - **Context Manager:**
     - Xử lý conversation history từ `request.messages`.
     - Giới hạn số lượng turns (mặc định 10 turns).
     - Tóm tắt lịch sử dài thành context string.
     - Ưu tiên các turns liên quan đến câu hỏi hiện tại.
     - Tạo optimized prompt kết hợp context.
   - **Semantic Cache (raw query):**
     - Tính embedding bằng Alibaba-NLP/gte-multilingual-base.
     - Nếu similarity với cache >= threshold, trả về kết quả luôn.
   - Nếu không hit cache:
     - Gọi LlamaGuard Input Policy kiểm tra an toàn đầu vào.
     - **Query Rewriter với Context:**
       - Làm sạch câu hỏi (rule-based).
       - Kết hợp với conversation context để tạo enhanced query.
       - Paraphrase bằng BARTpho nếu cần thiết.
       - Cache paraphrase để tái sử dụng.
     - **Semantic Cache (normalized query):**
       - Tính embedding normalized query, check cache.
       - Nếu hit, trả về kết quả luôn.
   - Nếu không hit cache:
     - Intent Detector xác định loại câu hỏi (law, form, term, procedure, ambiguous).
     - Sinh embedding cho câu hỏi bằng Alibaba GTE.
   - Truy vấn Qdrant (vector DB) theo intent, lấy 25 chunk liên quan từ 1 hoặc nhiều collection.
   - Áp dụng BGE Reranker để cải thiện ranking quality, chọn top 15 kết quả.
   - Gọi Prompt Manager để tạo prompt động, format context phù hợp intent.
   - **Context Manager: Tạo optimized prompt:**
     - Kết hợp base prompt với conversation context.
     - Đảm bảo context không quá dài.
     - Tối ưu hóa prompt cho LLM.
   - Gọi LLM (DeepSeek V3) sinh câu trả lời dựa trên optimized prompt.
     - Kiểm tra an toàn đầu ra bằng LlamaGuard Output Policy.
   - Lưu lịch sử chat, metadata vào Supabase (PostgreSQL).
     - Lưu kết quả vào semantic cache (cả raw và normalized query).
   - Trả kết quả về frontend (answer, sources, intent, confidence, timestamp).

3. **Context Manager**
   - **process_conversation_history()**: Xử lý lịch sử hội thoại.
     - Giới hạn số lượng turns (configurable).
     - Tóm tắt lịch sử dài thành context string.
     - Ưu tiên các turns liên quan đến câu hỏi hiện tại.
   - **create_optimized_prompt()**: Tạo prompt tối ưu.
     - Kết hợp base prompt với conversation context.
     - Đảm bảo độ dài phù hợp cho LLM.
     - Tối ưu hóa format và cấu trúc.

4. **Query Rewriter**
   - **rewrite_with_context()**: Rewrite với conversation context.
     - Kết hợp câu hỏi với context keywords.
     - Rule-based cleaning (loại bỏ emoji, HTML, cụm từ không cần thiết).
     - Paraphrase bằng BARTpho nếu cần thiết.
     - Cache paraphrase để tái sử dụng.
   - **Enhanced logging**: Log chi tiết quá trình rewrite để debug.

5. **Qdrant (Vector DB)**
   - Lưu trữ embedding của 4 loại dữ liệu (laws, forms, terms, procedures).
   - Hỗ trợ truy vấn semantic search theo vector embedding.
   - Trả về 25 chunk dữ liệu liên quan nhất cho backend.

6. **BGE Reranker**
   - Sử dụng cross-encoder model "BAAI/bge-reranker-v2-m3".
   - Cải thiện ranking quality từ 70-80% lên 85-95%.
   - Chọn top 15 kết quả sau reranking.
   - Performance: 0.5-2.0s cho batch processing.

7. **Supabase (PostgreSQL)**
   - Lưu trữ dữ liệu gốc (laws, forms, terms, procedures).
   - Lưu lịch sử hội thoại, metadata, log intent detection, performance.
   - Hỗ trợ truy vấn lịch sử chat, thống kê, monitoring.

8. **Các Agent & Service**
   - **Context Manager**: Quản lý conversation context, tối ưu hóa prompt.
   - **LlamaGuard**: 2 lớp bảo vệ an toàn input/output.
   - **Intent Detector**: Phân loại intent, routing collection.
   - **Query Rewriter**: Làm sạch, paraphrase với context, cache paraphrase.
   - **BGE Reranker**: Cross-encoder reranking để cải thiện chất lượng.
   - **Prompt Manager**: Sinh prompt động, format context.
   - **LLM Service**: Gọi model DeepSeek V3 sinh câu trả lời.
   - **Embedding Service**: Sinh embedding bằng Alibaba GTE.
   - **Qdrant Service**: Truy vấn vector DB, trả về chunk liên quan.
   - **Supabase Service**: Lưu/log dữ liệu, truy vấn lịch sử.
   - **Semantic Cache Service**: Lưu và truy vấn cache semantic (raw + normalized).
   - **Paraphrase Cache Service**: Lưu và truy vấn cache paraphrase.

### 3. Sơ Đồ Luồng Dữ Liệu (Data Flow, Cập nhật mới nhất)

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant B as Backend (FastAPI)
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

