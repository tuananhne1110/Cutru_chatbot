# Hệ Thống Chatbot Trợ Lý Pháp Lý Cư Trú - Phân Tích Chi Tiết

## 1. TỔNG QUAN HỆ THỐNG

Đây là một hệ thống chatbot AI chuyên biệt hỗ trợ tư vấn pháp lý về lĩnh vực cư trú tại Việt Nam. Hệ thống sử dụng kiến trúc RAG (Retrieval-Augmented Generation) với LangGraph để xử lý các câu hỏi phức tạp một cách có cấu trúc.

### Công nghệ chính:
- **FastAPI**: Web framework để xây dựng API
- **LangGraph**: Orchestration cho workflow AI phức tạp
- **AWS Bedrock**: Dịch vụ LLM (Claude và Llama)
- **Qdrant**: Vector database cho việc tìm kiếm tài liệu
- **BGE Reranker**: Cải thiện chất lượng kết quả tìm kiếm
- **LangSmith**: Monitoring và tracing

---

## 2. KIẾN TRÚC TỔNG THỂ

### 2.1 Cấu trúc thư mục chính

```
├── main.py                    # Entry point của ứng dụng
├── config/                    # Cấu hình hệ thống
├── agents/                    # Logic xử lý AI workflow
│   ├── workflow.py           # Định nghĩa LangGraph workflow
│   ├── state.py              # State management
│   ├── nodes/                # Các node xử lý trong workflow
│   ├── utils/                # Utilities hỗ trợ
│   └── prompt/               # Quản lý prompt templates
├── services/                  # Các dịch vụ core
├── routers/                  # API endpoints
├── models/                   # Data schemas
└── data/                     # Dữ liệu và scripts xử lý
```

### 2.2 Luồng xử lý chính

```
User Question → Intent Detection → Query Rewriting → Document Retrieval 
→ Reranking → Answer Generation → Validation → Response
```

---

## 3. PHÂN TÍCH CHI TIẾT TỪNG THÀNH PHẦN

### 3.1 Entry Point - `main.py`

**Chức năng**: Khởi tạo ứng dụng FastAPI và cấu hình các middleware cần thiết.

**Cách hoạt động**:
- Tạo FastAPI app với title "Legal Assistant API"
- Cấu hình CORS middleware cho phép tất cả origins
- Đăng ký các router: `/chat` (LangGraph) và `/health`
- Thiết lập logging levels để giảm spam logs
- Chạy server trên port 8000

---

### 3.2 Configuration System - `config/`

#### 3.2.1 `config.yaml`
**Chức năng**: File cấu hình trung tâm chứa tất cả parameters của hệ thống.

**Các cấu hình chính**:
- **LLM Models**: Claude và Llama với các parameters như max_tokens, temperature
- **Cache**: Cấu hình semantic cache với threshold và limits
- **Intent Detection**: System prompts và keyword mappings cho phân loại câu hỏi
- **Embedding**: Model name cho sentence transformers
- **Prompt Templates**: Base template cho generation

#### 3.2.2 `app_config.py`
**Chức năng**: Load và khởi tạo các client/services cần thiết.

**Cách hoạt động**:
1. Load environment variables từ `.env`
2. Khởi tạo embedding model (Alibaba-NLP/gte-multilingual-base)
3. Tạo Qdrant client (local host:6333)
4. Khởi tạo Supabase client (nếu có credentials)
5. Cấu hình LangSmith tracing (nếu enabled)

---

### 3.3 LangGraph Workflow - `agents/workflow.py`

**Chức năng**: Định nghĩa và orchestrate toàn bộ quy trình xử lý câu hỏi.

**Workflow Flow**:
```
START → set_intent → semantic_cache → guardrails_input 
→ rewrite → retrieve → generate → validate → update_memory → END
```

**Các Node chính**:
- `set_intent`: Phân loại intent của câu hỏi
- `semantic_cache`: Kiểm tra cache để tăng tốc
- `guardrails_input`: Kiểm soát an toàn input
- `rewrite`: Viết lại câu hỏi cho rõ ràng hơn
- `retrieve`: Tìm kiếm tài liệu liên quan
- `generate`: Sinh câu trả lời
- `validate`: Kiểm tra chất lượng output
- `update_memory`: Cập nhật conversation memory

**State Management**: Sử dụng `ChatState` TypedDict để truyền dữ liệu giữa các nodes.

---

### 3.4 State Management - `agents/state.py`

**Chức năng**: Định nghĩa cấu trúc dữ liệu được truyền qua toàn bộ workflow.

**Các trường chính**:
- `messages`: Lịch sử conversation
- `question`: Câu hỏi hiện tại
- `intent`: Intent được phát hiện
- `context_docs`: Tài liệu tìm được
- `rewritten_query`: Câu hỏi đã được viết lại
- `answer`: Câu trả lời sinh ra
- `processing_time`: Thời gian xử lý từng bước

---

### 3.5 Intent Detection System - `agents/utils/intent_detector.py`

**Chức năng**: Phân loại câu hỏi của người dùng vào các nhóm intent khác nhau.

**6 Intent Types**:
1. **LAW**: Tra cứu luật pháp (văn bản pháp lý, điều luật)
2. **PROCEDURE**: Thủ tục hành chính (quy trình, hồ sơ)
3. **FORM**: Hướng dẫn điền biểu mẫu
4. **TERM**: Thuật ngữ và định nghĩa
5. **TEMPLATE**: Biểu mẫu gốc (templates)
6. **GENERAL**: Giao tiếp chung

**Cách hoạt động**:
1. Sử dụng AWS Bedrock Llama model với tool calling
2. Định nghĩa các tool specs cho từng intent
3. LLM phân tích câu hỏi và gọi tool phù hợp
4. Trả về list các (intent, query) pairs
5. Tự động bổ sung LAW + FORM nếu phát hiện PROCEDURE

**Xử lý đặc biệt**:
- Loại bỏ intent trùng lặp
- Hỗ trợ multi-intent cho câu hỏi phức tạp
- Fallback về GENERAL nếu không phân loại được

---

### 3.6 Query Rewriting - `agents/utils/query_rewriter.py`

**Chức năng**: Viết lại câu hỏi để rõ ràng và đầy đủ hơn, đặc biệt với follow-up questions.

**3 Rewrite Strategies**:
1. **SUB_QUERY**: Chia nhỏ câu hỏi phức tạp (cho PROCEDURE)
2. **MULTI_QUERY**: Tạo nhiều biến thể (cho FORM, TEMPLATE, GENERAL)
3. **STANDARD**: Diễn giải rõ ràng hơn (cho LAW, TERM)

**Cách hoạt động**:
1. Lấy context từ conversation history
2. Chọn strategy dựa trên intent
3. Tạo prompt phù hợp với strategy
4. Gọi LLM để rewrite
5. Clean và trả về query đã được cải thiện

**Intent-Strategy Mapping**:
- LAW → STANDARD (giữ nguyên độ chính xác pháp lý)
- PROCEDURE → SUB_QUERY (chia nhỏ các bước)
- FORM/TEMPLATE → MULTI_QUERY (nhiều cách gọi tên)

---

### 3.7 Document Retrieval - `agents/nodes/retrieve_node.py`

**Chức năng**: Tìm kiếm và thu thập tài liệu liên quan từ vector database.

**Quy trình retrieval**:
1. **Collection Mapping**: Chuyển intent thành collection names
   - LAW → legal_chunks
   - PROCEDURE → procedure_chunks  
   - FORM → form_chunks
   - TERM → term_chunks
   - TEMPLATE → template_chunks

2. **Embedding & Search**: 
   - Tạo embedding cho query
   - Tìm kiếm trong các collections tương ứng
   - Lấy 30 docs từ mỗi collection

3. **Reranking**: Sử dụng BGE reranker để cải thiện thứ tự

4. **Law-specific Processing**:
   - Phát hiện cấu trúc pháp lý (điều-khoản-điểm)
   - Mở rộng tìm kiếm theo parent_id
   - Merge thành cây cấu trúc hoàn chỉnh
   - Group theo Điều → Khoản → Điểm

**Xử lý đặc biệt cho Legal chunks**:
- Tự động lấy parent/child documents
- Merge theo cấu trúc pháp lý đúng
- Đảm bảo context đầy đủ cho điều luật

---

### 3.8 Vector Database Service - `services/qdrant_service.py`

**Chức năng**: Quản lý tương tác với Qdrant vector database và tự động filtering.

**Auto-filtering System**:
- Sử dụng LLM để sinh filter conditions từ natural language
- Riêng biệt cho từng collection type (PROCEDURE, LEGAL, FORM, TERM)
- Filter theo metadata fields cụ thể

**Filtering Logic**:
1. Phân tích query bằng LLM
2. Sinh structured filter (must/must_not/should)
3. Thực hiện filtered search
4. Fallback to vector search nếu filter không có kết quả

**Ví dụ filter fields**:
- **PROCEDURE**: procedure_code, category, implementation_level
- **LEGAL**: law_name, article, chapter, clause, point
- **FORM**: form_code, form_name, field_name
- **TERM**: term, category

**Parent-ID Expansion**:
- `search_qdrant_by_parent_id`: Tìm children của document
- `search_qdrant_by_id`: Tìm document cụ thể
- Hỗ trợ xây dựng cây cấu trúc pháp lý

---

### 3.9 Reranking Service - `services/reranker_service.py`

**Chức năng**: Cải thiện chất lượng search results bằng cross-encoder model.

**BGE Reranker (BAAI/bge-reranker-v2-m3)**:
- Cross-encoder architecture for better relevance scoring
- Đánh giá pairwise giữa query và documents
- Sắp xếp lại theo relevance score

**Quy trình reranking**:
1. Chuẩn bị (query, document) pairs
2. Tính cross-encoder scores
3. Sắp xếp theo scores giảm dần
4. Trả về top-k results
5. Thống kê improvement metrics

**Metadata Extraction**: Tự động trích xuất thông tin quan trọng từ metadata để reranking khi không có content.

---

### 3.10 LLM Service - `services/llm_service.py`

**Chức năng**: Interface thống nhất để gọi các LLM models qua AWS Bedrock.

**Supported Models**:
- **Claude 3.5 Sonnet**: Cho tasks phức tạp, reasoning
- **Llama 4 Scout**: Cho general generation, cost-effective

**API Functions**:
- `call_llm_stream`: Streaming response (cho real-time UI)
- `call_llm_full`: Complete response 
- `call_llm_with_system_prompt`: Với system prompt
- `call_llm_conversation`: Multi-turn conversation

**Streaming Implementation**:
- Chia response thành chunks 100 ký tự
- Yield từng chunk cho smooth streaming
- Track token usage cho monitoring

---

### 3.11 Answer Generation - `agents/nodes/generate_node.py`

**Chức năng**: Sinh câu trả lời dựa trên retrieved documents và prompt templates.

**Quy trình generation**:
1. **Input Processing**: Extract question, docs, intent, history
2. **No-docs Handling**: 
   - GENERAL intent → Gọi LLM trực tiếp
   - Khác → Trả lời không tìm thấy thông tin
3. **Prompt Creation**: Format docs theo category-specific templates
4. **LLM Generation**: Stream response với appropriate model
5. **Langfuse Logging**: Track inputs, outputs, metadata

**Special Handling**:
- Intent-based response strategies
- Graceful degradation khi không có docs
- Comprehensive error handling với fallback responses

---

### 3.12 Prompt Management - `agents/prompt/prompt_templates.py`

**Chức năng**: Quản lý và format prompts cho các loại content khác nhau.

**Base Template**: Template chung từ config.yaml với vai trò chuyên gia pháp lý

**Category-specific Formatting**:
- **LAW**: `[Luật - Chương - Điều - Khoản - Điểm]`
- **FORM**: `[Form_Code - Mục - Tên trường - Loại]`
- **PROCEDURE**: `[Tên thủ tục - Mã - Cấp thực hiện - Phần]`
- **TERM**: `[Thuật ngữ - Định nghĩa - Category]`

**Context Formatting Logic**:
- Trích xuất metadata quan trọng
- Tạo source references rõ ràng
- Format table content cho procedure docs
- Structured presentation cho từng loại document

---

### 3.13 API Layer - `routers/langgraph_chat.py`

**Chức năng**: Expose HTTP endpoints cho client applications.

**Endpoints**:

#### 3.13.1 `POST /chat/`
- **Input**: `ChatRequest` (question, messages, session_id)
- **Output**: `ChatResponse` (answer, sources, session_id, timestamp)
- **Logic**: 
  1. Tạo initial state từ request
  2. Chạy LangGraph workflow
  3. Extract results từ final state
  4. Return structured response

#### 3.13.2 `POST /chat/stream`
- **Input**: `ChatRequest`
- **Output**: Server-Sent Events stream
- **Logic**:
  1. Chạy workflow để get prompt và sources
  2. Stream LLM output real-time
  3. Send sources metadata
  4. Signal completion

**Streaming Format**:
```json
data: {"type": "chunk", "content": "text"}
data: {"type": "sources", "sources": [...]}
data: {"type": "done"}
```

**Error Handling**: Graceful fallbacks với informative error messages

---

### 3.14 Data Schemas - `models/schemas.py`

**Chức năng**: Định nghĩa structured data models cho API.

**Key Models**:
- `ChatRequest`: Input validation cho chat endpoints
- `ChatResponse`: Structured response format
- `Source`: Metadata về tài liệu tham khảo
- `Message`: Conversation message format

**Validation**: Pydantic models đảm bảo type safety và data integrity.

---

## 4. FLOW HOẠT ĐỘNG CHI TIẾT CỦA TỪNG MODULE

Phần này mô tả luồng hoạt động cụ thể của từng thành phần code, từ input đến output, bao gồm các bước xử lý chi tiết, decision points, và error handling. Mỗi flow diagram thể hiện cách data di chuyển qua các functions và modules.

### 4.1 Main Application Flow - `main.py`

```
[Application Start]
    ↓
[Import Dependencies]
    ↓
[Setup Logging Configuration]
    ↓ 
[Create FastAPI App Instance]
    ↓
[Add CORS Middleware]
    ↓
[Register Routers]
    ├── /chat → langgraph_chat_router
    └── /health → health.router
    ↓
[Start Uvicorn Server] (host=0.0.0.0, port=8000)
    ↓
[Ready to Accept Requests]
```

### 4.2 Configuration Loading Flow - `config/app_config.py`

```
[Module Import]
    ↓
[Load Environment Variables]
    ├── SUPABASE_URL
    ├── SUPABASE_KEY  
    ├── LANGCHAIN_API_KEY
    └── LANGCHAIN_PROJECT
    ↓
[Load YAML Config] → config.yaml
    ↓
[Initialize Embedding Model]
    ├── Model: Alibaba-NLP/gte-multilingual-base
    └── trust_remote_code=True
    ↓
[Setup Qdrant Client]
    ├── Host: localhost
    └── Port: 6333
    ↓
[Initialize Supabase Client] (if credentials available)
    ↓
[Configure LangSmith Tracing] (if enabled)
    ├── Set Environment Variables
    └── Print Status Message
    ↓
[Export Global Instances]
```

### 4.3 LangGraph Workflow Execution Flow - `agents/workflow.py`

```
[Workflow Invocation]
    ↓
[Initialize ChatState]
    ↓
┌─── NODE: set_intent ───┐
│ Input: ChatState       │
│ ├── Extract question   │
│ ├── Call intent_detect │
│ └── Update state.intent│
│ Output: ChatState      │
└─────────────────────────┘
    ↓
┌─── NODE: semantic_cache ───┐
│ Input: ChatState           │
│ ├── Check cache existence │
│ ├── Generate cache key    │
│ └── Return cached result  │
│ Output: ChatState          │
└────────────────────────────┘
    ↓
┌─── NODE: guardrails_input ───┐
│ Input: ChatState             │
│ ├── Validate input safety   │
│ ├── Check content policies  │
│ └── Set error flags         │
│ Output: ChatState            │
└──────────────────────────────┘
    ↓
┌─── NODE: rewrite ───┐
│ Input: ChatState    │
│ ├── Get context    │
│ ├── Select strategy│
│ ├── Call LLM rewrite│
│ └── Update query   │
│ Output: ChatState   │
└─────────────────────┘
    ↓
┌─── NODE: retrieve ───┐
│ Input: ChatState     │
│ ├── Map collections │
│ ├── Generate embed  │
│ ├── Search docs     │
│ ├── Rerank results  │
│ └── Process law docs│
│ Output: ChatState    │
└──────────────────────┘
    ↓
┌─── NODE: generate ───┐
│ Input: ChatState     │
│ ├── Format docs     │
│ ├── Create prompt   │
│ ├── Call LLM        │
│ └── Stream response │
│ Output: ChatState    │
└──────────────────────┘
    ↓
┌─── NODE: validate ───┐
│ Input: ChatState     │
│ ├── Check quality   │
│ ├── Verify sources  │
│ └── Set flags       │
│ Output: ChatState    │
└──────────────────────┘
    ↓
┌─── NODE: update_memory ───┐
│ Input: ChatState          │
│ ├── Store conversation   │
│ ├── Update session       │
│ └── Clean old data       │
│ Output: ChatState         │
└───────────────────────────┘
    ↓
[Return Final State]
```

### 4.4 Intent Detection Flow - `agents/utils/intent_detector.py`

```
[detect_intent() Called]
    ↓
[Prepare Input]
    ├── query: str
    └── trace_id: str (optional)
    ↓
[Build Tool Configuration]
    ├── Create tool specs for 6 intents
    ├── LAW, PROCEDURE, FORM, TERM, TEMPLATE, GENERAL
    └── Each tool has name, description, input_schema
    ↓
[Create Bedrock Request]
    ├── messages: [{"role": "user", "content": query}]
    ├── system: [ROUTER_SYSTEM_PROMPT]
    └── toolConfig: {tools: [tool_specs]}
    ↓
[Call AWS Bedrock LLM]
    ├── Model: us.meta.llama4-scout-17b-instruct-v1:0
    └── Method: converse()
    ↓
[Process LLM Response]
    ├── Case 1: toolUse format
    │   ├── Extract tool_name
    │   ├── Extract new_query
    │   └── Map to IntentType
    ├── Case 2: text format (JSON)
    │   ├── Decode JSON string
    │   ├── Extract parameters
    │   └── Map to IntentType
    └── Case 3: Fallback to GENERAL
    ↓
[Remove Duplicate Intents]
    ├── Keep first occurrence of each intent
    └── Maintain query for each intent
    ↓
[Auto-Enhancement]
    ├── If PROCEDURE detected
    ├── Auto-add LAW intent
    └── Auto-add FORM intent
    ↓
[Return List[(IntentType, str)]]
```

### 4.5 Query Rewriting Flow - `agents/utils/query_rewriter.py`

```
[rewrite_query_with_context() Called]
    ↓
[Input Processing]
    ├── current_question: str
    ├── messages: List
    ├── llm_client: wrapper
    └── intent: IntentType
    ↓
[Get Conversation History]
    ├── Call context_manager.get_recent_history_for_llm()
    ├── Extract recent relevant turns
    └── Format for LLM consumption
    ↓
[Select Rewrite Strategy]
    ├── LAW → STANDARD
    ├── PROCEDURE → SUB_QUERY  
    ├── FORM/TEMPLATE → MULTI_QUERY
    ├── TERM → STANDARD
    └── GENERAL → MULTI_QUERY
    ↓
[Create Strategy-Specific Prompt]
    ├── Base prompt with history + question
    ├── SUB_QUERY: "Chia nhỏ câu hỏi..."
    ├── MULTI_QUERY: "Tạo nhiều biến thể..."
    └── STANDARD: "Diễn giải rõ ràng..."
    ↓
[Call LLM for Rewrite]
    ├── Send prompt to LLM client
    ├── Get rewritten query
    └── Handle errors with fallback
    ↓
[Clean LLM Response]
    ├── Remove quotes and prefixes
    ├── Strip unwanted text
    └── Return clean query
    ↓
[Return Rewritten Query or Original]
```

### 4.6 Document Retrieval Flow - `agents/nodes/retrieve_node.py`

```
[retrieve_context() Called]
    ↓
[Input Validation]
    ├── Check guardrails error
    ├── Extract query (rewritten or original)
    └── Get all_intents from state
    ↓
[Query Enhancement]
    ├── If query < 6 words AND has message history
    ├── Find previous user message
    ├── Merge: prev_question + current_question
    └── Log follow-up detection
    ↓
[Collection Mapping]
    ├── For each intent in all_intents:
    ├── LAW → legal_chunks
    ├── FORM → form_chunks
    ├── TERM → term_chunks
    ├── PROCEDURE → procedure_chunks
    └── GENERAL → general_chunks
    ↓
[Generate Query Embedding]
    ├── Call get_embedding(query)
    ├── Use asyncio executor
    └── Get vector representation
    ↓
[Multi-Collection Search]
    ├── For each collection in parallel:
    ├── Call search_qdrant(collection, embedding, query, 30)
    ├── Apply auto-filtering
    ├── Get results with metadata
    └── Collect all documents
    ↓
[BGE Reranking]
    ├── Prepare documents for reranking
    ├── Call reranker.rerank(query, docs, 30)
    ├── Add rerank_score to metadata
    └── Sort by relevance
    ↓
[Intent-Specific Processing]
    ├── If primary_intent == LAW:
    │   ├── Call _expand_law_chunks_with_structure()
    │   ├── Call _group_law_chunks_tree()
    │   └── Return merged law documents
    └── Else: Return top 30 documents
    ↓
[Update State and Return]
    ├── state["context_docs"] = final_docs
    ├── Log processing time
    └── Return updated state
```

### 4.7 Qdrant Search with Auto-Filtering Flow - `services/qdrant_service.py`

```
[search_qdrant() Called]
    ↓
[Input Processing]
    ├── collection_name: str
    ├── query_embedding: vector
    ├── query: str
    └── limit: int
    ↓
[Select Filter Strategy]
    ├── procedure_chunks → FILTER_PROMPT_PROCEDURE
    ├── legal_chunks → FILTER_PROMPT_LEGAL  
    ├── form_chunks → FILTER_PROMPT_FROM
    ├── term_chunks → FILTER_PROMPT_TERM
    ├── template_chunks → FILTER_PROMPT_TEMPLATE
    └── others → Simple vector search
    ↓
[Generate Auto-Filter]
    ├── Call automate_filtering(query, indexes, prompt)
    ├── Send to LLM with structured output
    ├── Get QdrantFilterWrapper with must/must_not/should
    └── Convert to Qdrant Filter object
    ↓
[Execute Filtered Search]
    ├── Try: qdrant_client.query_points()
    │   ├── collection_name
    │   ├── query_embedding  
    │   ├── query_filter
    │   ├── limit
    │   └── with_payload=True
    ├── If filter returns 0 results:
    │   └── Fallback to vector search
    └── If query_points fails:
        └── Fallback to vector search
    ↓
[Return Results]
    ├── Return (results, filter_condition)
    └── Log filter condition and result count
```

### 4.8 BGE Reranking Flow - `services/reranker_service.py`

```
[rerank() Called]
    ↓
[Input Validation]
    ├── query: str
    ├── documents: List[Dict]
    ├── top_k: int = 10
    └── batch_size: int = 32
    ↓
[Prepare Cross-Encoder Pairs]
    ├── For each document:
    ├── Extract content or metadata
    ├── Create [query, content] pair
    └── Build pairs list
    ↓
[BGE Model Prediction]
    ├── Load BAAI/bge-reranker-v2-m3
    ├── Call model.predict(pairs)
    ├── Use specified batch_size
    ├── Disable progress bar
    └── Get relevance scores
    ↓
[Score Integration]
    ├── For each (doc, score):
    ├── Copy document
    ├── Add rerank_score
    ├── Add original_rank
    └── Create scored_docs list
    ↓
[Sort and Rank]
    ├── Sort by rerank_score (descending)
    ├── Take top_k results
    ├── Add final_rank
    ├── Calculate rank_improvement
    └── Log reranking statistics
    ↓
[Return Reranked Documents]
```

### 4.9 LLM Service Streaming Flow - `services/llm_service.py`

```
[call_llm_stream() Called]
    ↓
[Input Processing]
    ├── prompt: str
    ├── model: str = "claude"
    ├── max_tokens: int = 4000
    └── temperature: float = 0.5
    ↓
[Model Configuration]
    ├── If model == "claude":
    │   ├── Create ClaudeConfig
    │   └── Model: anthropic.claude-3-5-sonnet
    └── Else (llama):
        ├── Create LlamaConfig  
        └── Model: us.meta.llama4-scout-17b-instruct
    ↓
[Bedrock Request]
    ├── Create message object
    ├── Call bedrock_client.generate_message()
    ├── Pass config overrides
    └── Get complete response
    ↓
[Response Processing]
    ├── Extract response text using handler
    ├── Get token usage information
    ├── Log usage statistics
    └── Store in call_llm_stream.last_usage
    ↓
[Chunk and Stream]
    ├── Split response into 100-char chunks
    ├── Yield each chunk
    └── Provide smooth streaming experience
    ↓
[Error Handling]
    ├── Catch any exceptions
    ├── Yield error message
    ├── Reset usage to 0
    └── Log error details
```

### 4.10 Answer Generation Flow - `agents/nodes/generate_node.py`

```
[generate_answer() Called]
    ↓
[Input Extraction]
    ├── question: str
    ├── docs: List[Document]
    ├── intent: IntentType
    └── history: List[Message]
    ↓
[Guardrails Check]
    ├── If error == "input_validation_failed":
    ├── Skip generation
    ├── Log skip reason
    └── Return with timing
    ↓
[No Documents Handling]
    ├── If no docs found:
    ├── If intent == GENERAL:
    │   ├── Call LLM directly
    │   ├── Stream response
    │   └── Log to Langfuse
    └── Else: Return "không tìm thấy thông tin"
    ↓
[Document Formatting]
    ├── Convert docs to formatted_docs
    ├── Extract page_content and metadata
    └── Create doc dictionaries
    ↓
[Prompt Creation]
    ├── Call prompt_manager.create_dynamic_prompt()
    ├── Format documents by category
    ├── Apply base template
    └── Get final prompt
    ↓
[LLM Generation]
    ├── Call call_llm_stream(prompt, model_name)
    ├── Collect answer chunks
    ├── Join into complete answer
    └── Store chunks for streaming
    ↓
[Langfuse Logging]
    ├── Log input prompt
    ├── Log model and metadata
    ├── Log session info
    ├── Log usage details
    └── Log cost information
    ↓
[Error Handling]
    ├── Catch generation exceptions
    ├── Set error state
    ├── Provide fallback response
    └── Log error details
    ↓
[Update State and Return]
    ├── state["answer"] = final_answer
    ├── state["answer_chunks"] = chunks
    ├── Log processing time
    └── Return updated state
```

### 4.11 API Router Standard Chat Flow - `routers/langgraph_chat.py`

```
[POST /chat/ Request]
    ↓
[Request Validation]
    ├── Parse ChatRequest
    ├── Extract question, messages, session_id
    └── Validate schema
    ↓
[State Initialization]
    ├── Generate session_id if not provided
    ├── Call create_initial_state()
    ├── Build ChatState object
    └── Prepare for workflow
    ↓
[LangSmith Configuration]
    ├── Create config dict with thread_id
    ├── If tracing enabled:
    │   ├── Add tags from config
    │   ├── Add metadata
    │   └── Include session info
    └── Cast to RunnableConfig
    ↓
[Workflow Execution]
    ├── Call rag_workflow.ainvoke(state, config)
    ├── Wait for complete workflow
    └── Get final state
    ↓
[Result Extraction]
    ├── Call extract_results_from_state()
    ├── Get answer and sources
    └── Format response data
    ↓
[Response Generation]
    ├── Create ChatResponse object
    ├── Include answer, sources, session_id
    ├── Add timestamp
    └── Return structured response
    ↓
[Error Handling]
    ├── Catch any exceptions
    ├── Log error details
    └── Return HTTP 500 with error message
```

### 4.12 API Router Streaming Chat Flow - `routers/langgraph_chat.py`

```
[POST /chat/stream Request]
    ↓
[Request Processing]
    ├── Parse ChatRequest
    ├── Extract question, messages, session_id
    └── Create initial state
    ↓
[LangSmith Setup]
    ├── Add "streaming" tag
    ├── Include streaming metadata
    └── Prepare config
    ↓
[Workflow Execution]
    ├── Run rag_workflow.ainvoke()
    ├── Get complete result state
    └── Extract prompt and sources
    ↓
[Guardrails Check]
    ├── If input_validation_failed:
    ├── Create guardrails_blocked_stream()
    ├── Stream error message char by char
    └── Return with "done" signal
    ↓
[Prompt Validation]
    ├── If no prompt generated:
    ├── Create fallback_stream()
    ├── Stream fallback message
    └── Return with "done" signal
    ↓
[LLM Streaming]
    ├── Create stream_llm() generator
    ├── Yield buffer-breaking dummy string
    ├── Call call_llm_stream(prompt, "llama")
    ├── For each chunk:
    │   └── Yield {"type": "chunk", "content": chunk}
    ├── Yield sources metadata
    └── Yield {"type": "done"} signal
    ↓
[Return Streaming Response]
    ├── Return StreamingResponse
    ├── Media type: "text/event-stream"
    └── Handle client disconnections
    ↓
[Error Handling]
    ├── Catch streaming exceptions
    ├── Create error_stream() generator
    └── Return error in streaming format
```

---

## 6. LUỒNG XỬ LÝ HOÀN CHỈNH

### 6.1 User Request Flow

```
1. User gửi request đến /chat/ hoặc /chat/stream
2. FastAPI router nhận request, validate schemas
3. Create initial ChatState từ request data
4. Trigger LangGraph workflow execution
```

### 6.2 LangGraph Workflow Execution

```
1. SET_INTENT: Phân loại intent bằng Bedrock LLM
2. SEMANTIC_CACHE: Check cache để tăng tốc (nếu có)
3. GUARDRAILS_INPUT: Validate input safety
4. REWRITE: Cải thiện clarity của query
5. RETRIEVE: Tìm relevant documents từ Qdrant
6. GENERATE: Sinh answer bằng LLM + retrieved context
7. VALIDATE: Check output quality (placeholder)
8. UPDATE_MEMORY: Cập nhật conversation state
```

### 6.3 Document Retrieval Deep Dive

```
1. Intent → Collections mapping
2. Generate embedding cho query
3. Search trong multiple collections parallel
4. Apply auto-generated filters
5. BGE reranking for relevance
6. Special law document expansion
7. Return top-k structured documents
```

### 6.4 Answer Generation Process

```
1. Extract documents, question, intent
2. Format documents theo category-specific templates
3. Create final prompt với base template
4. Call appropriate LLM model
5. Stream response chunks
6. Log everything to LangSmith
7. Return answer + sources
```

---

## 7. CÁC TÍNH NĂNG ĐẶC BIỆT

### 7.1 Multi-Intent Support
- Một câu hỏi có thể thuộc nhiều intents
- Tự động search multiple collections
- Intelligent collection combination

### 7.2 Legal Document Structure Awareness
- Hiểu cấu trúc Điều → Khoản → Điểm
- Tự động mở rộng context với parent/child
- Merge thành document hierarchy hoàn chỉnh

### 7.3 Auto-Filtering
- LLM-powered filter generation
- Collection-specific filter strategies
- Fallback to vector search nếu filter fail

### 7.4 Streaming Architecture
- Real-time response streaming
- Chunk-based delivery
- Sources metadata transmission

### 7.5 Comprehensive Monitoring
- LangSmith integration cho tracing
- Processing time tracking
- Token usage monitoring
- Error logging và analytics

---

## 8. INTEGRATION & DEPENDENCIES

### 8.1 External Services
- **AWS Bedrock**: LLM hosting (Claude, Llama)
- **Qdrant**: Vector database (local instance)
- **LangSmith**: Monitoring và tracing
- **Supabase**: Database (optional)

### 8.2 Key Libraries
- **LangGraph**: Workflow orchestration
- **LangChain**: LLM abstractions
- **FastAPI**: Web framework
- **Sentence Transformers**: Embeddings
- **CrossEncoder**: Reranking
- **Pydantic**: Data validation

---

## 9. ERROR HANDLING & FALLBACKS

### 9.1 Service Failures
- LLM không available → Error messages
- Qdrant connection issues → Empty docs
- Embedding failures → Skip retrieval

### 9.2 Quality Degradation
- No documents found → Intent-based responses
- Reranker fails → Original order
- Rewrite fails → Original query

### 9.3 Input Validation
- Guardrails filtering
- Pydantic schema validation
- Length limits và safety checks

---

## 10. PERFORMANCE OPTIMIZATIONS

### 10.1 Caching Strategies
- Semantic cache cho frequent queries
- Memory-based checkpointing
- Conversation state persistence

### 10.2 Parallel Processing
- Multiple collection searches
- Async/await throughout
- Batch processing cho reranking

### 10.3 Resource Management
- GPU utilization cho reranking
- Connection pooling
- Proper cleanup và resource disposal

---

## TỔNG KẾT

Hệ thống chatbot này được thiết kế như một solution enterprise-grade cho domain cư trú pháp lý, với architecture modularity cao, comprehensive error handling, và advanced AI capabilities. Mỗi component đều có vai trò rõ ràng và tương tác seamlessly để tạo ra một assistant AI intelligent và reliable.

Điểm mạnh chính:
- **Specialized Domain Knowledge**: Tối ưu cho legal domain
- **Intelligent Document Retrieval**: Multi-modal search với auto-filtering
- **Structured Answer Generation**: Context-aware prompting
- **Scalable Architecture**: Modular design với clear separation of concerns
- **Comprehensive Monitoring**: Full observability stack

Hệ thống có thể handle từ simple Q&A đến complex multi-step legal procedures, providing accurate và well-sourced information cho end users.