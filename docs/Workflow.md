## 🛠️ Workflow Chi Tiết Toàn Bộ Hệ Thống

### 1. Luồng Xử Lý Tổng Thể (High-level System View)
```mermaid
graph TD

  %% Tầng giao diện người dùng chi tiết
  F1["Browser / Widget"] -->|HTTPS| F2["React App"] -->|REST / SSE| B1["FastAPI + LangGraph"]

  %% Dịch vụ phía sau
  B1 --> DB1["Postgres / Supabase"]
  B1 --> DB2["Qdrant Vector DB"]
  B1 --> DB3["Supabase Storage"]

  %% LangGraph Agent Pipeline
  B1 --> C1["LangGraph Agent Pipeline"]

  subgraph C1 ["LangGraph Agent Pipeline"]
    direction TB
    C1A["Query Understanding & Classification"]
    C1B["Query Optimization & Rewriting"]
    C1C["RAG Execution (Search + LLM + Guard)"]
    C1D["Memory Update + Response"]
    
    C1A --> C1B --> C1C --> C1D
  end

  %% Output
  C1D --> D1["Stream Response to Frontend"] --> F1
```

### 2. Mô tả chi tiết từng bước

**A. Frontend (React 18)**
- Người dùng nhập câu hỏi và gửi request qua API `/chat/stream`.
- Gửi kèm mảng `messages` chứa lịch sử hội thoại.
- **Nhận kết quả trả về dạng streaming:**
  - Các chunk `"type": "chunk"` chứa nội dung trả lời.
  - Chunk `"type": "sources"` chứa metadata nguồn tham khảo (bao gồm cả file mẫu, link tải về...).
- **Hiển thị:**
  - Nội dung trả lời.
  - Nếu có file mẫu trong sources, **hiện nút tải về nổi bật** phía dưới.
  - Khi bấm "Hiện nguồn tham khảo", hiển thị đúng thông tin nguồn (luật hoặc biểu mẫu, có link tải nếu là mẫu).

**B. Backend (FastAPI + LangGraph)**
- Nhận request, sinh `session_id` nếu chưa có, chuẩn hóa lịch sử hội thoại.
- **LangGraph RAG Workflow:**

#### Bước 1-2: Kiểm tra cache ban đầu
1. **set_intent:** Phân loại intent (law, form, term, procedure, template, ambiguous).
2. **semantic_cache_initial:** Kiểm tra cache semantic với câu hỏi gốc.

#### Nhánh A: Cache Hit Ban Đầu (Trùng cache với câu hỏi gốc)
**Khi tìm thấy câu hỏi gốc tương tự trong cache:**
- **Lấy kết quả cache:** Trích xuất answer và sources từ cache
- **Cập nhật metadata:** Ghi log cache hit, thời gian xử lý
- **Stream kết quả:** Gửi cached answer và sources về frontend
- **Bỏ qua tất cả các bước:** Không cần xử lý thêm
- **Lưu lịch sử:** Vẫn lưu vào Supabase để tracking

#### Nhánh B: Cache Miss Ban Đầu (Tiếp tục xử lý)
**Khi không tìm thấy câu hỏi gốc trong cache:**
3. **guardrails_input:** Kiểm duyệt an toàn đầu vào (LlamaGuard Input). Nếu vi phạm, trả về thông báo an toàn.
4. **rewrite:** Làm sạch, paraphrase câu hỏi với context từ lịch sử hội thoại (rule-based + LLM nếu cần).
5. **semantic_cache_rewrite:** Kiểm tra cache semantic với câu hỏi đã được rewrite.

#### Nhánh B1: Cache Hit Sau Rewrite (Trùng cache với câu hỏi đã rewrite)
**Khi tìm thấy câu hỏi đã rewrite tương tự trong cache:**
- **Lấy kết quả cache:** Trích xuất answer và sources từ cache
- **Cập nhật metadata:** Ghi log cache hit với rewritten query
- **Stream kết quả:** Gửi cached answer và sources về frontend
- **Bỏ qua các bước:** Không cần retrieve, generate, validate
- **Lưu lịch sử:** Vẫn lưu vào Supabase để tracking

#### Nhánh B2: Cache Miss Sau Rewrite (Full processing)
**Khi không tìm thấy câu hỏi đã rewrite trong cache:**
6. **retrieve:** Tìm kiếm semantic trong các collection tương ứng (top 25).
7. **generate:** Tạo prompt động phù hợp intent, chèn context và metadata.
8. **validate:** Kiểm duyệt đầu ra (LlamaGuard Output).
9. **update_memory:** Lưu lại câu hỏi, câu trả lời, nguồn, intent, v.v. vào Supabase.
10. **Cache kết quả:** Lưu kết quả mới vào semantic cache cho lần sau.

### 3. Sơ Đồ Luồng Dữ Liệu Chi Tiết (Data Flow, LangGraph-based)

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant B as Backend (FastAPI + LangGraph)
    participant L as LangGraph Workflow
    participant Q as Qdrant (Vector DB)
    participant LLM as AWS Bedrock (LLM)
    participant S as Supabase (PostgreSQL)
    participant C as Cache Service
    
    U->>B: POST /chat/stream (question + messages)
    B->>L: set_intent
    L->>L: semantic_cache_initial (với câu hỏi gốc)
    L->>C: Check semantic cache với original query
    
    alt Cache HIT Ban Đầu (Trùng cache với câu hỏi gốc)
        C-->>L: Cached answer + sources
        L->>L: update_memory (lưu lịch sử)
        L->>S: Lưu chat history với cache flag
        L-->>B: Cached answer + sources
        B-->>U: Stream cached answer chunks + sources
        Note over C: Cache hit với original query - Fastest response
        
    else Cache MISS Ban Đầu (Tiếp tục xử lý)
        L->>L: guardrails_input
        L->>L: rewrite (với context từ lịch sử)
        L->>L: semantic_cache_rewrite (với câu hỏi đã rewrite)
        L->>C: Check semantic cache với rewritten query
        
        alt Cache HIT Sau Rewrite (Trùng cache với câu hỏi đã rewrite)
            C-->>L: Cached answer + sources
            L->>L: update_memory (lưu lịch sử)
            L->>S: Lưu chat history với cache flag
            L-->>B: Cached answer + sources
            B-->>U: Stream cached answer chunks + sources
            Note over C: Cache hit với rewritten query - Fast response
            
        else Cache MISS Sau Rewrite (Full processing)
            L->>L: retrieve
            L->>Q: Semantic search (4 collections)
            Q-->>L: Top 25 candidates
            L->>L: generate
            L->>LLM: Generate answer (streaming)
            LLM-->>L: Answer chunks
            L->>L: validate
            L->>L: update_memory
            L->>S: Lưu lịch sử chat, log
            L->>C: Cache kết quả mới
            L-->>B: Trả answer + sources
            B-->>U: Stream answer chunks + sources
            Note over C: Cache miss - Full processing
        end
    end
```