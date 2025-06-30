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

- **Backend**: FastAPI với pipeline RAG tối ưu và Intent Detection
- **Frontend**: React 18 với UI/UX hiện đại
- **Vector Database**: Qdrant cho semantic search với 4 collections
- **Database**: Supabase cho lưu trữ dữ liệu và lịch sử
- **AI Models**: DeepSeek V3 cho LLM, Vietnamese PhoBERT cho embedding
- **Guardrails**: 4 lớp bảo vệ multi-layer defense-in-depth
- **Intent Detection**: Phân loại thông minh câu hỏi theo 4 loại dữ liệu

### 🚀 Tính Năng Chính

- ✅ **4 Loại Dữ Liệu**: Laws, Forms, Terms, Procedures
- ✅ **Intent Detection**: Phân loại thông minh câu hỏi
- ✅ **RAG Pipeline**: Tìm kiếm semantic + sinh câu trả lời
- ✅ **Query Rewriter**: Làm sạch và tối ưu câu hỏi
- ✅ **Guardrails**: 4 lớp bảo vệ an toàn
- ✅ **Streaming Response**: Trả lời real-time
- ✅ **Chat History**: Lưu trữ lịch sử hội thoại
- ✅ **Dynamic Prompts**: Prompt chuyên biệt theo loại dữ liệu
- ✅ **Multi-collection Search**: Tìm kiếm thông minh theo intent
- ✅ **Docker Deployment**: Triển khai dễ dàng

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
                       ┌─────────────────┐
                       │   Qdrant        │
                       │   Vector DB     │
                       │   4 Collections │
                       │   Port: 6333    │
                       └─────────────────┘
```

### 🔄 Luồng Dữ Liệu

```
User Query → 🛡️ Guardrails → 🧠 Intent Detection → 🔄 Query Rewrite → 
🔍 Multi-Collection Search → 📝 Dynamic Prompt → 🤖 LLM → 🛡️ Output Validation → 📤 Response
```

## 📁 Cấu Trúc Thư Mục

```
phapluat/
├── 📁 agents/                    # AI Agents & Intelligence
│   ├── intent_detector.py       # Phân loại intent thông minh
│   ├── prompt_templates.py      # Prompt templates chuyên biệt
│   ├── prompt_manager.py        # Quản lý prompt động
│   ├── guardrails.py            # 4 lớp bảo vệ an toàn
│   └── query_rewriter.py        # Làm sạch & tối ưu câu hỏi
├── 📁 chunking/                  # Xử lý văn bản pháp luật
│   ├── law_chunking.py          # Chunking luật thành đoạn nhỏ
│   ├── form_chunker.py          # Chunking form guidance
│   ├── term_chunks.py           # Chunking thuật ngữ
│   └── output_json/             # JSON chunks đã xử lý
│       ├── all_laws.json        # ~1,200+ law chunks
│       ├── form_chunks.json     # ~400+ form chunks
│       ├── term_chunks.json     # ~470+ term chunks
│       └── procedure_chunks.json # ~5,400+ procedure chunks
├── 📁 data/                      # Database & Data Management
│   ├── create_tables.sql        # SQL schema cho 4 bảng
│   ├── insert_all_data.py       # Import dữ liệu vào Supabase
│   └── README_Insert_Data.md    # Hướng dẫn import
├── 📁 frontend/                  # React Frontend
│   ├── src/                     # React components
│   ├── public/                  # Static files
│   ├── package.json             # Dependencies
│   └── Dockerfile.frontend      # Frontend container
├── 📁 models/                    # Pydantic Schemas
│   └── schemas.py               # API request/response models
├── 📁 routers/                   # FastAPI Routes
│   ├── chat.py                  # Chat endpoints với intent detection
│   └── health.py                # Health check
├── 📁 services/                  # Business Logic
│   ├── llm_service.py           # LLM integration (DeepSeek)
│   ├── embedding.py             # Embedding service (PhoBERT)
│   ├── qdrant_service.py        # Vector search
│   └── supabase_service.py      # Database operations
├── 📁 utils/                     # Utility functions
├── 📄 main.py                    # FastAPI app entry point
├── 📄 config.py                  # Configuration & clients
├── 📄 form_embed_qdrant.py      # Tạo embeddings cho 4 loại dữ liệu
├── 📄 add_new_chunks.py         # Thêm chunks mới vào Qdrant
├── 📄 requirements.txt           # Python dependencies
├── 📄 docker-compose.yml         # Multi-container setup
├── 📄 Dockerfile.backend         # Backend container
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
IntentType.UNKNOWN    # Không xác định
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

**4 Lớp Bảo Vệ:**
1. **Rule-based filters** - Từ khóa cấm, PII patterns
2. **OpenAI Moderation API** - Content safety check
3. **LLM-based policy check** - Semantic validation
4. **Logging + Fallback** - Audit trail và message an toàn

### 4. 🔄 **Query Rewriter** (`agents/query_rewriter.py`)
- Cải thiện câu hỏi để tăng độ chính xác search
- Xử lý ngôn ngữ tự nhiên tiếng Việt
- Rule-based cleaning + LLM paraphrase

### 5. 📋 **Prompt Manager** (`agents/prompt_manager.py`)
- Dynamic prompt generation theo intent
- Context formatting chuyên biệt
- Multi-category handling

## ⚡ Pipeline Xử Lý

### 🔄 Chat Pipeline Chi Tiết

```
1. User Query
   ↓
2. Guardrails Input Check
   ├── Lớp 1: Rule-based filter
   ├── Lớp 2: OpenAI Moderation (nếu cần)
   └── Lớp 3: Policy check
   ↓
3. Intent Detection
   ├── Keywords analysis
   ├── Confidence scoring
   └── Collection routing
   ↓
4. Query Rewriter
   ├── Rule-based cleaning
   └── LLM paraphrase (nếu cần)
   ↓
5. Embedding Generation
   └── Vietnamese PhoBERT
   ↓
6. Multi-Collection Search
   ├── Intent-based routing
   ├── Weighted search
   └── Result ranking
   ↓
7. Dynamic Prompt Creation
   ├── Intent-based prompt selection
   ├── Context formatting
   └── Metadata enrichment
   ↓
8. LLM Generation
   ├── DeepSeek V3
   └── Specialized response
   ↓
9. Guardrails Output Check
   ├── Content safety
   └── Policy compliance
   ↓
10. Response
    └── Answer + Sources + Metadata
```

### 📊 Performance Metrics

| Bước | Thời gian trung bình | Ghi chú |
|------|---------------------|---------|
| Guardrails Input | 0.1-7.0s | Phụ thuộc OpenAI API |
| Intent Detection | 0.001s | Rule-based, rất nhanh |
| Query Rewrite | 0.001-0.5s | Rule-based nhanh, LLM chậm |
| Embedding | 0.8s | Vietnamese PhoBERT |
| Multi-collection Search | 0.03s | 4 collections |
| Dynamic Prompt | 0.002s | Template selection |
| LLM Generation | 1.2s | DeepSeek V3 |
| Guardrails Output | 0.1-7.0s | Phụ thuộc OpenAI API |
| **Tổng** | **2.1-15.5s** | **Trung bình ~5s** |

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
git clone <repository-url>
cd phapluat
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
npm start
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
docker-compose up -d
```

#### 3. Services
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Qdrant**: http://localhost:6333
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
  "session_id": "optional-session-id"
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

### 🔒 4 Lớp Bảo Vệ

#### **Lớp 1: Rule-based Filter**
- **Từ khóa nhạy cảm**: Tục tĩu, bạo lực, chính trị, ma túy
- **PII Patterns**: CMND, số điện thoại, email, passport
- **Spam Patterns**: Nhiều dấu chấm than, chữ hoa liên tiếp
- **Performance**: < 1ms

#### **Lớp 2: OpenAI Moderation**
- **Model**: `text-moderation-latest`
- **Categories**: harassment, hate, self_harm, sexual, violence
- **Threshold**: 0.7+ → BLOCKED, 0.3-0.7 → WARNING
- **Cost**: ~$0.0001 per request

#### **Lớp 3: Policy Guardrails**
- **Input Check**: Kiểm tra relevance pháp luật
- **Output Check**: Kiểm tra compliance policy
- **Rules**: Chỉ pháp luật hành chính-cư trú, không tư vấn cá nhân

#### **Lớp 4: Logging & Fallback**
- **Log**: Toàn bộ input/output với metadata
- **Fallback**: Message chuẩn khi bị block
- **Audit**: Trail để kiểm tra sau này

### 🚫 Xử Lý Khi Không An Toàn

```json
{
  "error": "Query không an toàn",
  "reason": "Nội dung độc hại (OpenAI): ['violence']",
  "safety_level": "blocked",
  "fallback_message": "Xin lỗi, tôi không thể hỗ trợ câu hỏi này..."
}
```

## 📊 Monitoring & Logging

### 📝 Log Format

#### **Intent Detection Log**
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "query": "thủ tục đăng ký tạm trú",
  "intent": "procedure",
  "confidence": "high",
  "law_matches": 0,
  "form_matches": 0,
  "term_matches": 0,
  "procedure_matches": 3,
  "detected_keywords": ["thủ tục", "đăng ký", "tạm trú"]
}
```

#### **Performance Log**
```
[Timing] Guardrails Input: 0.1234s
[Timing] Intent Detection: 0.0012s
[Timing] Query rewrite: 0.0123s
[Timing] Embedding: 0.8234s
[Timing] Multi-collection search: 0.1567s
[Timing] Dynamic prompt creation: 0.0023s
[Timing] LLM: 1.2345s
[Timing] Guardrails Output: 0.0987s
[Timing] Tổng thời gian xử lý: 2.4527s
```

### 📈 Metrics to Monitor

- **Response Time**: Trung bình, 95th percentile
- **Intent Accuracy**: Độ chính xác phân loại intent
- **Collection Usage**: Tỷ lệ sử dụng từng collection
- **Error Rate**: API errors, LLM failures
- **Guardrails**: Block rate, warning rate
- **Cost**: OpenAI API usage, embedding calls
- **Quality**: User feedback, answer relevance

## 🔧 Troubleshooting

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

#### **3. OpenAI API Error**
```bash
# Nguyên nhân: API key không đúng hoặc hết quota
# Giải pháp: Kiểm tra CHUTES_API_KEY trong .env
```

#### **4. Supabase Connection Error**
```bash
# Nguyên nhân: URL hoặc key không đúng
# Giải pháp: Kiểm tra SUPABASE_URL và SUPABASE_KEY
```

### 🔍 Debug Commands

#### **Kiểm tra Services**
```bash
# Backend health
curl http://localhost:8000/health

# Qdrant collections
python -c "from config import qdrant_client; print([c.name for c in qdrant_client.get_collections().collections])"

# Supabase tables
python -c "from config import supabase; print(supabase.table('laws').select('*').limit(1).execute())"
```

#### **Test Intent Detection**
```bash
# Test intent detector
python -c "from agents.intent_detector import intent_detector; intent, meta = intent_detector.detect_intent('thủ tục đăng ký tạm trú'); print(f'Intent: {intent.value}, Confidence: {meta[\"confidence\"]}')"
```

### 📋 Checklist Deployment

- [ ] Environment variables configured
- [ ] Database tables created (4 tables)
- [ ] Data imported to Supabase (4 types)
- [ ] Embeddings uploaded to Qdrant (4 collections)
- [ ] API keys valid
- [ ] Services running
- [ ] Health checks passing
- [ ] Intent detection working
- [ ] Frontend accessible
- [ ] Chat functionality working

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

## 🤝 Contributing

### 📝 Development Workflow

1. **Fork** repository
2. **Create** feature branch
3. **Make** changes
4. **Test** thoroughly
5. **Submit** pull request

### 🧪 Testing

```bash
# Run backend tests
python -m pytest tests/

# Run frontend tests
cd frontend && npm test

# Integration tests
python tests/integration_test.py
```

### 📚 Code Standards

- **Python**: PEP 8, type hints
- **JavaScript**: ESLint, Prettier
- **API**: OpenAPI 3.0 spec
- **Documentation**: Inline comments, docstrings

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)
- **Email**: support@legal-assistant.com

---

**Made with ❤️ for the Vietnamese legal community** 