# LangSmith Integration Guide

Hướng dẫn tích hợp LangSmith vào Cutru Chatbot để theo dõi và visualize hoạt động của hệ thống.

## 🚀 Tại sao sử dụng LangSmith?

LangSmith giúp bạn:
- **Theo dõi toàn bộ workflow** của LangGraph RAG pipeline
- **Visualize flow** qua các nodes: Intent → Cache → Guardrails → Rewrite → Retrieve → Generate → Validate → Memory
- **Monitor performance** của từng bước và tổng thể
- **Debug issues** khi có lỗi trong quá trình xử lý
- **Track metrics** như response time, success rate, user satisfaction

## 📋 Cài đặt & Cấu hình

### 1. Cài đặt Dependencies

```bash
pip install langsmith==0.2.14
```

### 2. Lấy LangSmith API Key

1. Truy cập [https://smith.langchain.com/](https://smith.langchain.com/)
2. Đăng ký/đăng nhập tài khoản
3. Tạo project mới hoặc sử dụng project có sẵn
4. Lấy API key từ Settings

### 3. Cấu hình Environment Variables

Tạo file `.env` từ `.env.example`:

```bash
cp .env.example .env
```

Cập nhật các giá trị:

```env
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_actual_api_key_here
LANGCHAIN_PROJECT=cutru-chatbot
LANGSMITH_API_URL=https://api.smith.langchain.com
```

### 4. Cấu hình Tags và Metadata

Chỉnh sửa `config/config.yaml`:

```yaml
langsmith:
  project_name: "cutru-chatbot"
  api_url: "https://api.smith.langchain.com"
  tracing_enabled: true
  tags:
    - "production"      # hoặc "development", "staging"
    - "rag-workflow"
    - "vietnamese-legal"
    - "v2.0.0"          # version của app
  metadata:
    application: "cutru-chatbot"
    version: "2.0.0"
    environment: "production"
    team: "legal-tech"
```

## 📊 Các Metrics được Track

### 1. Workflow Metrics
- **Total execution time** cho mỗi conversation
- **Node execution time** cho từng bước
- **Success/failure rate** của workflow
- **Cache hit rate** cho semantic cache

### 2. User Interaction Metrics
- **Session duration** và message count
- **Question length** và complexity
- **Response quality** (qua validation node)
- **Guardrails triggers** khi content bị block

### 3. Performance Metrics
- **LLM response time** cho generation
- **Retrieval accuracy** và relevance scores
- **Memory update frequency**
- **Intent classification accuracy**

## 🎯 Dashboard và Visualization

### 1. Workflow Visualization

LangSmith sẽ hiển thị:
```
Input → Set Intent → Cache Check → Guardrails → Query Rewrite → 
Context Retrieval → Answer Generation → Validation → Memory Update → Output
```

### 2. Key Dashboards

#### A. Performance Dashboard
- Average response time per endpoint
- Success rate trends
- Error rate by node type
- Cache hit rate over time

#### B. User Experience Dashboard  
- Session length distribution
- Most common intents
- Guardrails trigger frequency
- User satisfaction indicators

#### C. System Health Dashboard
- Memory usage patterns
- LLM token consumption
- Retrieval quality scores
- System errors and alerts

### 3. Custom Filters và Views

Tạo custom filters để xem:
- **By Intent**: `tag:procedure`, `tag:law`, `tag:form`, etc.
- **By Performance**: Slow requests (>5s), Failed requests
- **By User**: Specific sessions, Power users
- **By Time**: Peak hours, Daily/weekly trends

## 🔧 Debugging với LangSmith

### 1. Trace Analysis
Khi có issue:
1. Tìm failed trace trong LangSmith
2. Click vào specific node gặp lỗi
3. Xem input/output của node đó
4. Check logs và error messages
5. Trace backward để tìm root cause

### 2. Common Issues

#### Cache Miss Analysis
```python
# Xem tại sao cache miss
# Check semantic similarity scores
# Verify cache key generation
```

#### Guardrails False Positives
```python
# Review blocked content
# Adjust guardrails sensitivity
# Check validation rules
```

#### Poor Retrieval Quality
```python
# Check query rewriting effectiveness
# Review retrieved context relevance
# Adjust retrieval parameters
```

## 📈 Optimization với LangSmith Data

### 1. Performance Optimization
- Identify bottleneck nodes
- Optimize slow LLM calls
- Improve cache strategies
- Reduce retrieval latency

### 2. Quality Improvement
- Analyze low-quality responses
- Improve prompt templates
- Enhance context retrieval
- Fine-tune validation rules

### 3. User Experience Enhancement
- Track user drop-off points
- Identify confusing interactions
- Optimize for common use cases
- Reduce response times

## 🚨 Monitoring và Alerts

### 1. Set up Alerts cho:
- High error rate (>5%)
- Slow response time (>10s)
- Low cache hit rate (<70%)
- Frequent guardrails triggers

### 2. Daily Reports:
- System performance summary
- Top user issues
- Quality metrics
- Recommendations for improvement

## 🔒 Privacy và Security

LangSmith logs chỉ metadata và không lưu:
- Sensitive user information
- Personal identifiable data
- Actual document content (chỉ embeddings)

Để tăng cường privacy:
```python
# Mask sensitive data in traces
config_dict["metadata"]["user_id"] = "***masked***"
config_dict["metadata"]["ip_address"] = "***masked***"
```

## 🎉 Kết quả mong đợi

Sau khi tích hợp LangSmith, bạn sẽ có:

1. **Real-time visibility** vào toàn bộ RAG pipeline
2. **Performance insights** để optimize system
3. **User behavior analytics** để cải thiện UX
4. **Debugging capabilities** để fix issues nhanh chóng
5. **Quality metrics** để đánh giá hiệu quả

Truy cập [LangSmith Dashboard](https://smith.langchain.com/) để xem visualization của workflow!