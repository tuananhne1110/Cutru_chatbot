# Cải tiến Quản lý Context Hội thoại

## Tổng quan
Đã cải thiện hệ thống chatbot để xử lý context hội thoại tốt hơn với các tính năng:
- Quản lý context thông minh
- Tối ưu prompt cho LLM
- Tăng hiệu quả search và query rewriting
- Đồng bộ logic toàn hệ thống

## 1. Quản lý Context Hội thoại

### ContextManager (`agents/context_manager.py`)
- **Giới hạn số lượt đối thoại**: 3-5 turn gần nhất
- **Tóm tắt lịch sử**: Tự động tóm tắt khi cuộc hội thoại quá dài
- **Ưu tiên relevance**: Tính điểm relevance cho từng turn dựa trên câu hỏi hiện tại
- **Cấu trúc rõ ràng**: [System prompt] + [Lịch sử] + [Câu hỏi mới]

### Tính năng chính:
```python
# Xử lý lịch sử hội thoại
context_string, processed_turns = context_manager.process_conversation_history(
    conversation_messages, current_question
)

# Tạo prompt tối ưu
optimized_prompt = context_manager.create_optimized_prompt(
    base_prompt, context_string, current_question
)
```

## 2. Tối ưu Prompt gửi vào LLM

### Cấu trúc Prompt:
```
[System Prompt - VAI TRÒ VÀ TRÁCH NHIỆM]

LỊCH SỬ HỘI THOẠI:
[TÓM TẮT: Người dùng đã hỏi X câu hỏi]
Người dùng: [Câu hỏi gần nhất]
Trợ lý: [Trả lời gần nhất]

CÂU HỎI: [Câu hỏi hiện tại]

THÔNG TIN THAM KHẢO:
[Chunks từ search]

TRẢ LỜI:
```

### Quản lý độ dài:
- Giới hạn 5 turns gần nhất
- Tóm tắt tự động cho cuộc hội thoại dài
- Ưu tiên turns có relevance cao

## 3. Tăng hiệu quả Search và Query Rewriting

### QueryRewriter cải tiến (`agents/query_rewriter.py`):
- **Context-aware rewriting**: Sử dụng context để cải thiện câu hỏi
- **Keyword extraction**: Trích xuất keywords từ context
- **Logging chi tiết**: Log câu gốc và câu đã rewrite để debug

### Tính năng mới:
```python
# Rewrite với context
rewritten_question = query_rewriter.rewrite_with_context(
    original_question, context_string
)

# Log so sánh
query_rewriter._log_rewrite_comparison(original, rewritten, context)
```

## 4. Đồng bộ Logic Toàn Hệ thống

### Process Chat Request (`routers/chat.py`):
- **Unified processing**: Cả `/chat/` và `/stream/` dùng chung logic
- **Context integration**: Tích hợp context vào toàn bộ pipeline
- **Comprehensive logging**: Log toàn bộ chuỗi xử lý

### Pipeline mới:
```
1. Context Processing → 2. Semantic Cache → 3. Guardrails → 
4. Query Rewrite (with context) → 5. Search → 6. Prompt Creation → 
7. LLM Generation → 8. Cache & Save
```

## 5. Logging và Debug

### Logging chi tiết:
- **Context processing**: Số messages → số turns relevant
- **Query rewrite**: So sánh câu gốc và câu đã rewrite
- **Timing**: Thời gian từng bước xử lý
- **Relevance scores**: Điểm relevance của từng turn

### Debug information:
```
=== CONTEXT PROCESSING LOG ===
Original messages: 8
Processed turns: 5
Context length: 245 chars
Current question: Câu hỏi hiện tại

=== QUERY REWRITE COMPARISON ===
Original: Câu hỏi gốc
Rewritten: Câu hỏi đã rewrite
Similarity: 0.85 (12/15 words)
```

## 6. Cấu hình và Tùy chỉnh

### ContextManager settings:
```python
context_manager = ContextManager(
    max_turns=5,      # Số turns tối đa
    max_tokens=2000   # Số tokens tối đa
)
```

### Relevance thresholds:
- **High relevance**: > 0.3 (ưu tiên giữ lại)
- **Low relevance**: < 0.3 (có thể loại bỏ)

## 7. Lợi ích

### Hiệu quả:
- **Tăng độ chính xác**: Context giúp hiểu rõ ý định người dùng
- **Giảm thời gian**: Cache thông minh với context
- **Tối ưu prompt**: LLM nhận được thông tin đầy đủ

### Trải nghiệm người dùng:
- **Hội thoại tự nhiên**: Bot nhớ context cuộc trò chuyện
- **Trả lời nhất quán**: Dựa trên lịch sử hội thoại
- **Hiệu suất cao**: Xử lý nhanh với cache thông minh

## 8. Monitoring và Maintenance

### Metrics cần theo dõi:
- Context processing time
- Relevance score distribution
- Cache hit rate với context
- Prompt length distribution

### Debug tools:
- Log files với chi tiết từng bước
- Context processing visualization
- Query rewrite comparison logs
- Performance timing breakdown

## Kết luận

Hệ thống đã được cải thiện đáng kể trong việc xử lý context hội thoại:
- **Thông minh hơn**: Tự động quản lý và tối ưu context
- **Hiệu quả hơn**: Cache và search được cải thiện
- **Đáng tin cậy hơn**: Logging và monitoring toàn diện
- **Dễ bảo trì**: Code modular và có cấu trúc rõ ràng
``` 