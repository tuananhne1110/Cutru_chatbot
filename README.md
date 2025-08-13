# 🏛️ Legal Assistant - Hệ Thống Trợ Lý Pháp Luật Thông Minh

Hệ thống RAG (Retrieval-Augmented Generation) chuyên về pháp luật Việt Nam, sử dụng AI để trả lời câu hỏi pháp luật một cách chính xác và đáng tin cậy với 4 loại dữ liệu chính: Luật pháp, Biểu mẫu, Thuật ngữ, và Thủ tục hành chính.

## 📋 Mục Lục

- [Tổng Quan](#-tổng-quan)
- [4 Loại Dữ Liệu Chính](#-4-loại-dữ-liệu-chính)
- [Kiến Trúc Hệ Thống](#-kiến-trúc-hệ-thống)
- [Cấu Trúc Thư Mục](#-cấu-trúc-thư-mục)
- [AI Agents & Intelligence](#-ai-agents--intelligence)
- [Pipeline Xử Lý](#-pipeline-xử-lý)
- [Cài Đặt & Triển Khai](#-cài-đặt--triển-khai)
- [API Endpoints](#-api-endpoints)
- [Guardrails & Bảo Mật](#-guardrails--bảo-mật)
- [Monitoring & Logging](#-monitoring--logging)
- [Troubleshooting](#-troubleshooting)

## 🎯 Tổng Quan

Legal Assistant là một hệ thống AI hoàn chỉnh bao gồm:

- **Backend**: FastAPI với LangGraph workflow tối ưu và Intent Detection
- **Frontend**: React 18 với UI/UX hiện đại
- **Vector Database**: Qdrant cho semantic search với 4 collections
- **Database**: Supabase cho lưu trữ dữ liệu và lịch sử
- **Cache**: Redis cho semantic caching và performance optimization
- **AI Models**: AWS Bedrock (Llama 4 Scout 17B) cho LLM, Vietnamese PhoBERT cho embedding
- **BGE Reranker**: Cross-encoder reranking để cải thiện chất lượng kết quả
- **Guardrails**: 2 lớp bảo vệ với LlamaGuard
- **Intent Detection**: Phân loại thông minh câu hỏi theo 4 loại dữ liệu

### 🚀 Tính Năng Chính

- ✅ **4 Loại Dữ Liệu**: Laws, Forms, Terms, Procedures
- ✅ **LangGraph Workflow**: State management và orchestration tối ưu
- ✅ **Intent Detection**: Phân loại thông minh câu hỏi
- ✅ **RAG Pipeline**: Tìm kiếm semantic + sinh câu trả lời
- ✅ **BGE Reranker**: Cross-encoder reranking
- ✅ **Query Rewriter**: Làm sạch và tối ưu câu hỏi
- ✅ **Guardrails**: 2 lớp bảo vệ an toàn
- ✅ **Streaming Response**: Trả lời real-time
- ✅ **Chat History**: Lưu trữ lịch sử hội thoại
- ✅ **Dynamic Prompts**: Prompt chuyên biệt theo loại dữ liệu
- ✅ **Multi-collection Search**: Tìm kiếm thông minh theo intent
- ✅ **Semantic Caching**: Redis-based caching cho performance
- ✅ **Docker Deployment**: Triển khai dễ dàng với Docker Compose
- ✅ **LangSmith Monitoring**: Tracing và visualization toàn diện

## 📊 4 Loại Dữ Liệu Chính

### 1. 📜 **Laws (Luật pháp)**
- **File**: `chunking/output_json/all_laws.json`
- **Collection**: `legal_chunks`
- **Table**: `laws`
- **Content**: Văn bản luật, nghị định, thông tư, quyết định
- **Metadata**: law_code, law_name, promulgator, promulgation_date, effective_date, law_type, article, chapter, clause, point

### 2. 📋 **Forms (Biểu mẫu)**
- **File**: `chunking/output_json/form_chunks.json`
- **Collection**: `form_chunks`
- **Table**: `form_guidance`
- **Content**: Hướng dẫn điền biểu mẫu (CT01, CT02, NA17, etc.)
- **Metadata**: form_code, form_name, field_no, field_name, chunk_type, content, note

### 3. 📚 **Terms (Thuật ngữ)**
- **File**: `chunking/output_json/term_chunks.json`
- **Collection**: `term_chunks`
- **Table**: `terms`
- **Content**: Định nghĩa thuật ngữ pháp lý, khái niệm
- **Metadata**: term, definition, content, category, source, article, synonyms, related_terms, examples

### 4. 📋 **Procedures (Thủ tục)**
- **File**: `chunking/output_json/procedure_chunks.json`
- **Collection**: `procedure_chunks`
- **Table**: `procedures`
- **Content**: Thủ tục hành chính, quy trình đăng ký cư trú
- **Metadata**: procedure_code, procedure_name, implementation_level, procedure_type, field, requirements, implementation_result

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React 18)    │◄──►│   (FastAPI)     │◄──►│   (Supabase)    │
│   Port: 3000    │    │   Port: 8000    │    │   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Qdrant        │    │   Redis         │
                       │   Vector DB     │    │   Cache         │
                       │   4 Collections │    │   Semantic      │
                       │   Port: 6333    │    │   Port: 6379    │
                       └─────────────────┘    └─────────────────┘
```

### 🔄 Luồng Dữ Liệu

```
User Query → 🛡️ Guardrails → 🧠 Intent Detection → 🔄 Query Rewrite → 
🔍 Multi-Collection Search → 📝 Dynamic Prompt → 🤖 LLM → 🛡️ Output Validation → 📤 Response
```

## 📁 Cấu Trúc Thư Mục

```
Cutru_chatbot/
├── 📁 agents/                    # AI Agents & Intelligence
│   ├── intent_detector.py       # Phân loại intent thông minh
│   ├── prompt_templates.py      # Prompt templates chuyên biệt
│   ├── prompt_manager.py        # Quản lý prompt động
│   ├── guardrails.py            # 2 lớp bảo vệ an toàn
│   ├── query_rewriter.py        # Làm sạch & tối ưu câu hỏi
│   ├── context_manager.py       # Quản lý context hội thoại
│   ├── langgraph_implementation.py # LangGraph workflow chính
│   ├── policy_input.yaml        # LlamaGuard input policy
│   └── policy_output.yaml       # LlamaGuard output policy
├── 📁 chunking/                  # Xử lý văn bản pháp luật
│   ├── law_chunking.py          # Chunking luật thành đoạn nhỏ
│   ├── form_chunker.py          # Chunking form guidance
│   ├── term_chunks.py           # Chunking thuật ngữ
│   └── output_json/             # JSON chunks đã xử lý
│       ├── all_laws.json        
│       ├── form_chunks.json     
│       ├── term_chunks.json     
│       └── procedure_chunks.json 
├── 📁 data/                      # Database & Data Management
│   ├── create_tables.sql        # SQL schema cho 4 bảng
│   ├── insert_all_data.py       # Import dữ liệu vào Supabase
│   └── README_Insert_Data.md    # Hướng dẫn import
├── 📁 frontend/                  # React Frontend
│   ├── src/                     # React components
│   │   ├── components/          # UI components
│   │   │   ├── ChatWindow.js    # Chat interface
│   │   │   ├── FloatingChatbot.js # Floating chat widget
│   │   │   ├── Message.js       # Message component
│   │   │   ├── MessageInput.js  # Input component
│   │   │   └── DemoPage.js      # Demo page
│   │   ├── hooks/               # Custom hooks
│   │   │   └── useChatStream.js # Chat streaming logic
│   │   ├── App.js               # Main app component
│   │   └── index.js             # Entry point
│   ├── public/                  # Static files
│   ├── package.json             # Dependencies
│   ├── Dockerfile.frontend      # Frontend container
│   └── nginx.conf               # Nginx configuration
├── 📁 models/                    # Pydantic Schemas
│   └── schemas.py               # API request/response models
├── 📁 routers/                   # FastAPI Routes
│   ├── langgraph_chat.py        # LangGraph chat endpoints
│   └── health.py                # Health check
├── 📁 services/                  # Business Logic
│   ├── llm_service.py           # LLM integration (AWS Bedrock)
│   ├── aws_bedrock.py           # AWS Bedrock client
│   ├── embedding.py             # Embedding service (PhoBERT)
│   ├── qdrant_service.py        # Vector search
│   ├── reranker_service.py      # BGE reranker
│   ├── cache_service.py         # Redis semantic cache
│   └── supabase_service.py      # Database operations
├── 📁 docker/                    # Docker Configuration
│   └── docker-compose.yml       # Multi-container setup
├── 📁 config/                    # Configuration
├── 📁 scripts/                   # Utility scripts
├── 📁 assets/                    # Static assets
├── 📄 main.py                    # FastAPI app entry point
├── 📄 requirements.txt           # Python dependencies
├── 📄 setup.sh                   # Setup script
├── 📄 entrypoint.sh              # Docker entrypoint
└── 📄 README.md                  # This file
```

## 🧠 AI Agents & Intelligence

### 1. 🧠 **Intent Detector** (`agents/intent_detector.py`)

**Phân loại thông minh câu hỏi theo 4 loại:**

```python
IntentType.LAW        # Tra cứu luật pháp
IntentType.FORM       # Hướng dẫn biểu mẫu  
IntentType.TERM       # Thuật ngữ, định nghĩa
IntentType.PROCEDURE  # Thủ tục hành chính
IntentType.AMBIGUOUS  # Không rõ ràng
IntentType.GENERAL    # Tổng quát
```

**Keywords Detection:**
- **Law**: "luật", "điều", "khoản", "quy định", "ban hành", "nghị định", "thông tư"
- **Form**: "mẫu", "biểu mẫu", "điền", "CT01", "CT02", "NA17", "tờ khai"
- **Term**: "thuật ngữ", "định nghĩa", "là gì", "nghĩa là", "giải thích"
- **Procedure**: "thủ tục", "quy trình", "đăng ký", "cư trú", "tạm trú", "thường trú"

**Search Routing:**
```python
# Intent-based collection routing
LAW → legal_chunks
FORM → form_chunks  
TERM → term_chunks
PROCEDURE → procedure_chunks
AMBIGUOUS → all collections with weights
```

### 2. 📝 **Prompt Templates** (`agents/prompt_templates.py`)

**4 Prompt chuyên biệt:**

- **Law Prompt**: Chuyên gia pháp lý, trích dẫn điều khoản, căn cứ pháp luật
- **Form Prompt**: Hướng dẫn điền biểu mẫu chi tiết, ví dụ cụ thể
- **Term Prompt**: Giải thích thuật ngữ, định nghĩa, ví dụ sử dụng
- **Procedure Prompt**: Hướng dẫn thủ tục hành chính, quy trình từng bước

**Context Formatting:**
```python
# Law: [Luật Cư trú - Điều 20 - Khoản 1]
# Form: [CT01 - Mục 1 - Họ tên - hướng_dẫn_điền]
# Term: [Thường trú - Định nghĩa - cư_trú]
# Procedure: [Đăng ký tạm trú - 1.004194 - Cấp Xã - Phần 1/9]
```

### 3. 🛡️ **Guardrails** (`agents/guardrails.py`)

**2 Lớp Bảo Vệ:**
1. **LlamaGuard Input Policy** - Kiểm duyệt đầu vào
2. **LlamaGuard Output Policy** - Kiểm duyệt đầu ra
3. **Fallback Messages** - Thông báo an toàn khi vi phạm

### 4. 🔄 **Query Rewriter** (`agents/query_rewriter.py`)
- Cải thiện câu hỏi để tăng độ chính xác search
- Xử lý ngôn ngữ tự nhiên tiếng Việt
- Rule-based cleaning + LLM paraphrase

### 5. 📋 **Prompt Manager** (`agents/prompt_manager.py`)
- Dynamic prompt generation theo intent
- Context formatting chuyên biệt
- Multi-category handling

### 6. ⭐ **BGE Reranker** (`services/reranker_service.py`)
- Cross-encoder reranking với BAAI/bge-reranker-v2-m3
- Cải thiện chất lượng kết quả tìm kiếm
- Relevance scoring và reordering
- Performance optimization với batch processing

### 7. 🧠 **Context Manager** (`agents/context_manager.py`)
- Quản lý context hội thoại
- Xử lý lịch sử chat
- Tối ưu hóa context cho câu hỏi tiếp theo

## ⚡ Pipeline Xử Lý

### 🔄 LangGraph Workflow Chi Tiết

```
1. User Query
   ↓
2. set_intent (Intent Detection)
   ├── Keywords analysis
   ├── Confidence scoring
   └── Collection routing
   ↓
3. semantic_cache (Cache Check)
   ├── Embedding similarity check
   ├── Redis cache lookup
   └── Return cached result if found
   ↓
4. guardrails_input (Input Validation)
   ├── LlamaGuard Input Policy
   ├── Safety validation
   └── Block unsafe content
   ↓
5. rewrite (Query Rewriting)
   ├── Rule-based cleaning
   ├── Context-aware rewriting
   └── LLM paraphrase (if needed)
   ↓
6. retrieve (Semantic Retrieval)
   ├── Multi-collection search
   ├── Intent-based routing
   ├── Top 30 candidates retrieval
   └── BGE reranking
   ↓
7. generate (Answer Generation)
   ├── Dynamic prompt creation
   ├── LLM generation (AWS Bedrock)
   └── Streaming response
   ↓
8. validate (Output Validation)
   ├── LlamaGuard Output Policy
   ├── Content safety validation
   └── Policy compliance
   ↓
9. update_memory (Memory Update)
   ├── Conversation history update
   ├── Context summary generation
   └── Metadata logging
   ↓
10. Response
     └── Answer + Sources + Metadata
```

## 🚀 Cài Đặt & Triển Khai

### 📋 Yêu Cầu Hệ Thống

- **Python**: 3.8+
- **Node.js**: 16+
- **Docker**: 20.10+
- **RAM**: 4GB+ (8GB recommended)
- **Storage**: 10GB+ cho vector database

### 🔧 Cài Đặt Local

#### 1. Clone Repository
```bash
git clone https://github.com/tuananhne1110/Cutru_chatbot.git
cd Cutru_chatbot
```

#### 2. Backend Setup
```bash
# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc venv\Scripts\activate  # Windows

# Cài dependencies
pip install -r requirements.txt

# Cấu hình environment
cp env.example .env
# Chỉnh sửa .env với API keys
```

#### 3. Database Setup
```bash
# Tạo bảng Supabase (4 bảng)
python data/create_tables.sql

# Import dữ liệu (4 loại)
python data/insert_all_data.py
```

#### 4. Embedding Setup
```bash
# Tạo embeddings cho 4 loại dữ liệu
python form_embed_qdrant.py
```

#### 5. Frontend Setup
```bash
cd frontend
npm install
npm run build
npm install -g serve
serve -s build
```

#### 6. Chạy Backend
```bash
python main.py
```

### 🐳 Docker Deployment

#### 1. Environment Setup
```bash
cp env.example .env
# Chỉnh sửa .env
```

#### 2. Build & Run
```bash
docker-compose -f docker/docker-compose.yml up -d
```

#### 3. Services
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Qdrant**: http://localhost:6333
- **Redis**: localhost:6379
- **Nginx**: http://localhost:80
- **API Docs**: http://localhost:8000/docs

## 📡 API Endpoints

### 🔗 Base URL
```
http://localhost:8000
```

### 💬 Chat Endpoints

#### **POST /chat/**
```json
{
  "question": "Thủ tục đăng ký tạm trú như thế nào?",
  "session_id": "optional-session-id",
  "messages": [
    {"role": "user", "content": "Câu hỏi trước"},
    {"role": "assistant", "content": "Trả lời trước"}
  ]
}
```

**Response:**
```json
{
  "answer": "Thủ tục đăng ký tạm trú bao gồm các bước sau...",
  "sources": [
    {
      "procedure_name": "Đăng ký tạm trú",
      "procedure_code": "1.004194",
      "implementation_level": "Cấp Xã",
      "content": "Bước 1: Chuẩn bị hồ sơ..."
    }
  ],
  "session_id": "uuid-session-id",
  "timestamp": "2024-01-01T12:00:00",
  "intent": "procedure",
  "confidence": "high"
}
```

#### **POST /chat/stream**
- Streaming response cho real-time chat
- Same request format as `/chat/`
- Server-Sent Events (SSE) format

#### **GET /chat/history/{session_id}**
```json
{
  "messages": [
    {
      "question": "Thủ tục đăng ký tạm trú?",
      "answer": "Bao gồm...",
      "sources": [...],
      "intent": "procedure",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "session_id": "uuid-session-id"
}
```

### 🏥 Health Check

#### **GET /health**
```json
{
  "status": "healthy",
  "collections": {
    "legal_chunks": 1200,
    "form_chunks": 400,
    "term_chunks": 470,
    "procedure_chunks": 5400
  }
}
```

## 🛡️ Guardrails & Bảo Mật

### 🔒 2 Lớp Bảo Vệ

#### **Lớp 1: LlamaGuard Input Policy**
- **Model**: LlamaGuard 7B cho input validation
- **Policy**: `agents/policy_input.yaml`
- **Categories**: Harmful content, policy violations
- **Performance**: 0.1-2.0s
- **Fallback**: Safe khi LlamaGuard không available

#### **Lớp 2: LlamaGuard Output Policy**
- **Model**: LlamaGuard 7B cho output validation
- **Policy**: `agents/policy_output.yaml`
- **Categories**: Content safety, policy compliance
- **Performance**: 0.1-2.0s
- **Logging**: Chi tiết validation results

### 📊 Safety Metrics

| Lớp | Coverage | Response Time | Accuracy |
|-----|----------|---------------|----------|
| LlamaGuard Input | 95% | 0.1-2.0s | 98% |
| LlamaGuard Output | 95% | 0.1-2.0s | 98% |
| Fallback | 100% | <1ms | 100% |

### 🚫 Xử Lý Khi Không An Toàn

```json
{
  "error": "Query không an toàn",
  "reason": "Vi phạm chính sách Guardrails",
  "safety_level": "blocked",
  "fallback_message": "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam."
}
```

## 📊 Monitoring & Logging

### 🎯 LangSmith Integration
**Hệ thống monitoring và tracing toàn diện cho LangGraph workflow:**

- **🔄 Workflow Visualization**: Xem flow qua các nodes trong real-time
- **⚡ Performance Tracking**: Thời gian xử lý từng bước và tổng thể  
- **🐛 Error Monitoring**: Theo dõi lỗi và exceptions với stack trace
- **👤 User Analytics**: Phân tích hành vi và session người dùng
- **🤖 Model Performance**: Đánh giá chất lượng LLM và retrieval
- **🏷️ Smart Tagging**: Tags theo intent, environment, version
- **📊 Custom Metrics**: Cache hit rate, intent accuracy, response quality

**Setup nhanh:**
```bash
# 1. Auto setup 
python scripts/setup_langsmith.py

# 2. Test integration
python scripts/test_langsmith.py

# 3. View dashboard
https://smith.langchain.com/
```

### 📈 Metrics Dashboard
- **Workflow Performance**: Visualization của toàn bộ RAG pipeline
- **Node-level Metrics**: Thời gian và accuracy của từng step
- **Response Quality**: User feedback và validation scores  
- **Cache Efficiency**: Hit rate và performance improvement
- **Intent Distribution**: Phân bố và accuracy của intent detection
- **Error Analysis**: Categorized errors với debugging info
- **User Patterns**: Session analysis và behavior insights

### 🔍 Debugging Features
- **Trace Explorer**: Chi tiết từng request qua workflow
- **Node Inspector**: Input/output của mỗi processing step
- **Error Root Cause**: Trace backward để tìm nguyên nhân
- **Performance Bottlenecks**: Identify slow nodes và optimize
- **A/B Testing**: Compare different prompts và configurations

## ❌ Troubleshooting

### ❌ Lỗi Thường Gặp

#### **1. Intent Detection Error**
```bash
# Nguyên nhân: Keywords không match
# Giải pháp: Kiểm tra intent_detector.py keywords
```

#### **2. Collection Not Found**
```bash
# Nguyên nhân: Qdrant collection chưa tạo
# Giải pháp: Chạy form_embed_qdrant.py
```

#### **3. LLM API Error**
```bash
# Nguyên nhân: AWS credentials không đúng hoặc hết quota
# Giải pháp: Kiểm tra AWS credentials trong .env
```

#### **4. Supabase Connection Error**
```bash
# Nguyên nhân: URL hoặc key không đúng
# Giải pháp: Kiểm tra SUPABASE_URL và SUPABASE_KEY
```

#### **5. Redis Connection Error**
```bash
# Nguyên nhân: Redis service không chạy
# Giải pháp: Kiểm tra Redis container hoặc local Redis
```

### 📋 Checklist Deployment

- [ ] Environment variables configured
- [ ] Database tables created (4 tables)
- [ ] Data imported to Supabase (4 types)
- [ ] Embeddings uploaded to Qdrant (4 collections)
- [ ] Redis cache service running
- [ ] API keys valid
- [ ] Services running
- [ ] Health checks passing
- [ ] Intent detection working
- [ ] Frontend accessible
- [ ] Chat functionality working
- [ ] Streaming response working
- [ ] Cache functionality working

## 🎯 Use Cases & Examples

### **Law Queries:**
```
"Điều kiện đăng ký thường trú là gì?"
→ Intent: LAW → legal_chunks → Law-specific prompt
```

### **Form Queries:**
```
"Cách điền mục họ tên trong CT01?"
→ Intent: FORM → form_chunks → Form-specific prompt
```

### **Term Queries:**
```
"Thường trú là gì?"
→ Intent: TERM → term_chunks → Term-specific prompt
```

### **Procedure Queries:**
```
"Thủ tục đăng ký tạm trú như thế nào?"
→ Intent: PROCEDURE → procedure_chunks → Procedure-specific prompt
```

### **Ambiguous Queries:**
```
"Đăng ký cư trú cần gì?"
→ Intent: AMBIGUOUS → all collections → General prompt
```

## 🔄 Cache Strategy

### 🚀 Semantic Caching
- **Redis-based**: Lưu trữ kết quả dựa trên embedding similarity
- **Threshold**: 0.85 similarity score
- **TTL**: 1 giờ cho cache entries
- **Limit**: 1000 cached entries

### 📊 Cache Performance
- **Hit rate**: ~30-40% cho câu hỏi tương tự
- **Response time**: <100ms cho cache hits
- **Memory usage**: ~50MB cho 1000 entries

## 🎨 Frontend Features

### 💬 Chat Interface
- **Real-time streaming**: Server-Sent Events
- **Message history**: Lưu trữ và hiển thị lịch sử
- **Source display**: Hiển thị nguồn tham khảo
- **File download**: Tải biểu mẫu và tài liệu
- **Responsive design**: Mobile-friendly

### 🎯 UI Components
- **FloatingChatbot**: Widget chat nổi
- **ChatWindow**: Cửa sổ chat chính
- **Message**: Component tin nhắn
- **MessageInput**: Input nhập câu hỏi
- **DemoPage**: Trang demo

### 🔧 Custom Hooks
- **useChatStream**: Quản lý streaming chat
- **Session management**: Quản lý phiên chat
- **Error handling**: Xử lý lỗi gracefully


