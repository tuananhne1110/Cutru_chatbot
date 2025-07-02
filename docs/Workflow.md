## 🛠️ Workflow Chi Tiết Toàn Bộ Hệ Thống (Cập nhật mới)

### 1. Luồng Xử Lý Tổng Thể

```mermaid
graph TD;
  A["User (Frontend - React)"] -->|"Gửi câu hỏi qua API /chat/"| B["Backend (FastAPI)"]
  B --> C0["Semantic Cache (raw query, GTE embedding)"]
  C0 -- "Hit" --> Z["Trả kết quả từ semantic cache"]
  C0 -- "Miss" --> C1["LlamaGuard Input: Kiểm tra an toàn đầu vào"]
  C1 --> C2["Query Rewriter: Làm sạch, paraphrase (BARTpho), paraphrase cache"]
  C2 --> C3["Semantic Cache (normalized query, GTE embedding)"]
  C3 -- "Hit" --> Z
  C3 -- "Miss" --> C4["Intent Detector: Phân loại câu hỏi"]
  C4 --> C5["Embedding: Sinh vector (Alibaba GTE)"]
  C5 --> C6["Qdrant: Semantic Search (4 collections, 25 candidates)"]
  C6 --> C7["BGE Reranker: Cross-encoder reranking (top 15)"]
  C7 --> C8["Prompt Manager: Tạo prompt động"]
  C8 --> C9["LLM (DeepSeek): Sinh câu trả lời"]
  C9 --> C10["LlamaGuard Output: Kiểm tra an toàn đầu ra"]
  C10 -->|"Trả kết quả"| A
  B --> D["Supabase (PostgreSQL): Lưu lịch sử chat, metadata"]
```

### 2. Mô Tả Chi Tiết Từng Bước (Cập nhật)

1. **Frontend (React 18)**
   - Người dùng nhập câu hỏi, gửi request qua API `/chat/` hoặc `/chat/stream`.
   - Hiển thị kết quả trả về, lịch sử chat, trạng thái đang xử lý.

2. **Backend (FastAPI)**
   - Nhận request, sinh session_id nếu chưa có.
   - **Semantic Cache (raw query):**
     - Tính embedding bằng Alibaba-NLP/gte-multilingual-base.
     - Nếu similarity với cache >= threshold, trả về kết quả luôn.
   - Nếu không hit cache:
     - Gọi LlamaGuard Input Policy kiểm tra an toàn đầu vào.
     - Gọi Query Rewriter để làm sạch, paraphrase (ưu tiên rule-based, paraphrase bằng BARTpho nếu cần), cache paraphrase.
     - **Semantic Cache (normalized query):**
       - Tính embedding normalized query, check cache.
       - Nếu hit, trả về kết quả luôn.
   - Nếu không hit cache:
     - Intent Detector xác định loại câu hỏi (law, form, term, procedure, ambiguous).
     - Sinh embedding cho câu hỏi bằng Alibaba GTE.
     - Truy vấn Qdrant (vector DB) theo intent, lấy 25 chunk liên quan từ 1 hoặc nhiều collection.
     - Áp dụng BGE Reranker để cải thiện ranking quality, chọn top 15 kết quả.
     - Gọi Prompt Manager để tạo prompt động, format context phù hợp intent.
     - Gọi LLM (DeepSeek V3) sinh câu trả lời dựa trên prompt và context.
     - Kiểm tra an toàn đầu ra bằng LlamaGuard Output Policy.
     - Lưu lịch sử chat, metadata vào Supabase (PostgreSQL).
     - Lưu kết quả vào semantic cache (cả raw và normalized query).
     - Trả kết quả về frontend (answer, sources, intent, confidence, timestamp).

3. **Qdrant (Vector DB)**
   - Lưu trữ embedding của 4 loại dữ liệu (laws, forms, terms, procedures).
   - Hỗ trợ truy vấn semantic search theo vector embedding.
   - Trả về 25 chunk dữ liệu liên quan nhất cho backend.

4. **BGE Reranker**
   - Sử dụng cross-encoder model "BAAI/bge-reranker-v2-m3".
   - Cải thiện ranking quality từ 70-80% lên 85-95%.
   - Chọn top 15 kết quả sau reranking.
   - Performance: 0.5-2.0s cho batch processing.

5. **Supabase (PostgreSQL)**
   - Lưu trữ dữ liệu gốc (laws, forms, terms, procedures).
   - Lưu lịch sử hội thoại, metadata, log intent detection, performance.
   - Hỗ trợ truy vấn lịch sử chat, thống kê, monitoring.

6. **Các Agent & Service**
   - **LlamaGuard**: 2 lớp bảo vệ an toàn input/output.
   - **Intent Detector**: Phân loại intent, routing collection.
   - **Query Rewriter**: Làm sạch, paraphrase (ưu tiên rule-based, paraphrase bằng BARTpho nếu cần), cache paraphrase.
   - **BGE Reranker**: Cross-encoder reranking để cải thiện chất lượng.
   - **Prompt Manager**: Sinh prompt động, format context.
   - **LLM Service**: Gọi model DeepSeek V3 sinh câu trả lời.
   - **Embedding Service**: Sinh embedding bằng Alibaba GTE.
   - **Qdrant Service**: Truy vấn vector DB, trả về chunk liên quan.
   - **Supabase Service**: Lưu/log dữ liệu, truy vấn lịch sử.
   - **Semantic Cache Service**: Lưu và truy vấn cache semantic (raw + normalized).
   - **Paraphrase Cache Service**: Lưu và truy vấn cache paraphrase.

### 3. Sơ Đồ Luồng Dữ Liệu (Data Flow, Cập nhật)

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant B as Backend (FastAPI)
    participant C as Semantic Cache
    participant P as Paraphrase Cache
    participant Q as Qdrant (Vector DB)
    participant R as BGE Reranker
    participant S as Supabase (PostgreSQL)
    participant L as LLM (DeepSeek)
    U->>B: POST /chat/ (question)
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
            B->>B: Query Rewriter (rule-based/BARTpho)
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
            B->>L: Gọi LLM sinh câu trả lời
            L-->>B: Answer
            B->>B: LlamaGuard Output Check
            B->>S: Lưu lịch sử chat, log
            B->>C: Save semantic cache (raw + normalized)
            B-->>U: Trả kết quả
        end
    end
```
