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
  C7 -->|"Stream answer chunks + sources"| A
```

### 2. Mô tả chi tiết từng bước

**A. Frontend (React 18)**
- Người dùng nhập câu hỏi và gửi request qua API `/chat/stream`.
- Gửi kèm mảng `messages` chứa lịch sử hội thoại.
- **Nhận kết quả trả về dạng streaming:**
  - Các chunk `"type": "chunk"` chứa nội dung trả lời.
  - Chunk `"type": "sources"` chứa metadata nguồn tham khảo (bao gồm cả file mẫu, link tải về...).
- **Hiển thị:**
  - Nội dung trả lời (không còn link dài ngoằng).
  - Nếu có file mẫu trong sources, **hiện nút tải về nổi bật** phía dưới.
  - Khi bấm "Hiện nguồn tham khảo", hiển thị đúng thông tin nguồn (luật hoặc biểu mẫu, có link tải nếu là mẫu).

**B. Backend (FastAPI + LangGraph)**
- Nhận request, sinh `session_id` nếu chưa có, chuẩn hóa lịch sử hội thoại.
- **LangGraph RAG Workflow:**
  1. **set_intent:** Phân loại intent (law, form, term, procedure, template, ambiguous).
  2. **semantic_cache:** Kiểm tra cache semantic (embedding) với câu hỏi gốc. Nếu trùng, trả kết quả luôn.
  3. **guardrails_input:** Kiểm duyệt an toàn đầu vào (LlamaGuard Input). Nếu vi phạm, trả về thông báo an toàn.
  4. **rewrite:** Làm sạch, paraphrase câu hỏi với context (rule-based + LLM nếu cần).
  5. **retrieve:** Tìm kiếm semantic trong các collection tương ứng (top 25).
  6. **generate:** Tạo prompt động phù hợp intent, chèn context và metadata (bao gồm cả file_url, code, title... nếu là template).
  7. **validate:** Kiểm duyệt đầu ra (LlamaGuard Output).
  8. **update_memory:** Lưu lại câu hỏi, câu trả lời, nguồn, intent, v.v. vào Supabase.
- **Trả kết quả:**
  - **Stream từng chunk nội dung trả lời** về frontend.
  - **Sau khi stream xong, gửi chunk `"type": "sources"`** chứa metadata nguồn tham khảo (bao gồm cả file mẫu, link tải về...).

### 3. Sơ Đồ Luồng Dữ Liệu (Data Flow, LangGraph-based)

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant B as Backend (FastAPI + LangGraph)
    participant L as LangGraph Workflow
    participant S as Supabase (PostgreSQL)
    U->>B: POST /chat/stream (question + messages)
    B->>L: set_intent
    L->>L: semantic_cache
    alt Cache hit
        L-->>B: Cached answer + sources
        B-->>U: Stream answer chunks + sources
    else Cache miss
        L->>L: guardrails_input
        alt Input blocked
            L-->>B: Fallback message
            B-->>U: Stream answer chunks
        else Input safe
            L->>L: rewrite
            L->>L: retrieve
            L->>L: generate
            L->>L: validate
            L->>L: update_memory
            L->>S: Lưu lịch sử chat, log
            L-->>B: Trả answer + sources
            B-->>U: Stream answer chunks + sources
        end
    end
```

### 4. Tóm tắt các điểm mới nổi bật

- **Backend luôn trả về sources (bao gồm file_url, code, title...) trong chunk riêng biệt.**
- **Frontend tự động nhận sources và render nút tải về mẫu, hiển thị nguồn tham khảo đúng loại (luật, biểu mẫu...).**
- **Không còn link dài ngoằng trong nội dung trả lời.**
- **UX tốt hơn, người dùng dễ dàng tải file mẫu và xem nguồn tham khảo.**

### 5. Chi tiết xử lý sources

- **Backend:**
  - Khi truy vấn liên quan đến biểu mẫu, backend lấy metadata (file_url, code, title, ...) từ Qdrant hoặc nguồn dữ liệu.
  - Sau khi stream xong nội dung trả lời, backend gửi chunk `{"type": "sources", "sources": [...]}` cho frontend.
- **Frontend:**
  - Khi nhận chunk `type: sources`, frontend gán vào message bot cuối cùng.
  - Component Message.js sẽ tự động hiển thị nút tải về nếu có file_url, và hiển thị nguồn tham khảo đúng loại (luật, biểu mẫu, ...).


