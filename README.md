# Workflow Chi Tiết Toàn Bộ Hệ Thống

---

## 1) Kiến trúc hệ thống

```mermaid
flowchart LR
  %% ===================== FRONTEND =====================
  subgraph Frontend["Frontend - React 18"]
    direction TB
    FE_CHAT["Chatbot UI"]
    FE_VOICE["Voice Chat Client (ASR + TTS)"]
    FE_CCCD["CCCD Panel"]
    FE_SCAN["Scan Panel"]
  end

  %% ===================== BACKEND ======================
  subgraph Backend["Backend - FastAPI"]
    subgraph API["API Layer"]
      direction TB
      API_CHAT["REST /chat"]
      API_VOICE["WebSocket /voice"]
      API_CCCD["WebSocket /cccd"]
      API_SCAN["WebSocket /scan"]
    end
    subgraph SVC["Service Layer"]
      direction TB
      SVC_CONV["Conversation Service (LangGraph RAG)"]
      SVC_CCCD["CCCD Service"]
      SVC_SCAN["Scan Service"]
    end
  end

  %% ===================== DATA LAYER ===================
  subgraph Data["Data Layer"]
    QDR["Qdrant (Vector Database)"]
  end

  %% ===================== DEVICES ======================
  subgraph Devices["Devices"]
    direction TB
    DEV_CCCD["CCCD Reader Device"]
    DEV_SCAN["Scan Device"]
  end

  %% ===================== FLOWS ========================
  %% Frontend <-> API (đặt cùng thứ tự dọc để đường thẳng hàng)
  FE_CHAT <--> |HTTP| API_CHAT
  FE_VOICE <--> |WS| API_VOICE
  FE_CCCD <--> |WS| API_CCCD
  FE_SCAN <--> |WS| API_SCAN

  %% APIs -> Services
  API_CHAT --> |text| SVC_CONV
  API_VOICE --> |stream| SVC_CONV
  API_CCCD --> |events| SVC_CCCD
  API_SCAN --> |events| SVC_SCAN

  %% Side-feeds vào pipeline hội thoại dùng chung
  SVC_CCCD --> |context| SVC_CONV
  SVC_SCAN --> |context| SVC_CONV

  %% Retrieval dùng chung cho cả voice + text
  SVC_CONV <--> |vector search| QDR

  %% Devices thẳng hàng với API tương ứng
  DEV_CCCD --> |Network| API_CCCD
  DEV_SCAN --> |Network| API_SCAN

  %% ===================== STYLES =======================
  classDef fe fill:#E8F5E9,stroke:#2E7D32,stroke-width:1px,color:#1B5E20;
  classDef api fill:#E3F2FD,stroke:#1565C0,stroke-width:1px,color:#0D47A1;
  classDef svc fill:#FFF3E0,stroke:#EF6C00,stroke-width:1px,color:#E65100;
  classDef data fill:#F3E5F5,stroke:#6A1B9A,stroke-width:1px,color:#4A148C;
  classDef dev fill:#FBE9E7,stroke:#BF360C,stroke-width:1px,color:#BF360C;

  class FE_CHAT,FE_VOICE,FE_CCCD,FE_SCAN fe;
  class API_CHAT,API_VOICE,API_CCCD,API_SCAN api;
  class SVC_CONV,SVC_CCCD,SVC_SCAN svc;
  class QDR data;
  class DEV_CCCD,DEV_SCAN dev;
```

### Mô tả hệ thống

**Frontend – React 18**

- **Chatbot UI**: gõ văn bản, nhận câu trả lời (HTTP).
- **Voice Chat Client (ASR + TTS)**: thu âm → ASR cục bộ → gửi text qua WebSocket → nhận token trả lời → TTS cục bộ, chống dội (AEC).
- **CCCD Panel**: ...
- **Scan Panel**: ...
  <!-- - **CCCD Panel**: nhận dữ liệu thẻ theo thời gian thực, hiển thị/điền form. -->
  <!-- - **Scan Panel**: nhận dữ liệu scan giấy tờ theo thời gian thực, hiển thị/điền form. -->

**Backend – FastAPI**

- **API Layer**

  - `REST /chat` (HTTP): nhận tin nhắn text từ Chatbot UI.
  - `WS /voice` (WebSocket): kênh hai chiều cho voice (client gửi **text frames**, server stream **tokens**).
  - `WS /cccd`, `WS /scan` (WebSocket): nhận **events** từ thiết bị, đẩy realtime lên panel.

- **Service Layer**

  - **Conversation Service (LangGraph RAG)**: pipeline dùng chung cho **text** và **voice** (validate → embed → Qdrant search → rerank → build context → LLM → validate).
  <!-- - **CCCD Service**: tiếp nhận/chuẩn hoá dữ liệu thẻ, kiểm tra hợp lệ, phát sự kiện lên FE, và **bơm “context”** sang Conversation Service khi cần.
  - **Scan Service**: tương tự cho giấy tờ scan. -->
  - **CCCD Service**: ...
  - **Scan Service**: tương tự cho giấy tờ scan.

**Data Layer**

- **Qdrant (Vector Database)**: nguồn tri thức cho RAG.

**Devices**

- **CCCD Reader Device**, **Scan Device**: kết nối mạng tới `WS /cccd` và `WS /scan`.

### 1.1 kiến trúc langgraph RAG

```mermaid
flowchart TB
  %% =================== STYLES ===================
  classDef op fill:#E3F2FD,stroke:#1565C0,stroke-width:1px,color:#0D47A1;
  classDef inj fill:#E0F7FA,stroke:#006064,stroke-width:1px,color:#004D40;
  classDef proc fill:#FFFDE7,stroke:#FBC02D,stroke-width:1px,color:#E65100;
  classDef store fill:#F1F8E9,stroke:#33691E,stroke-width:1px,color:#1B5E20;
  classDef ret fill:#E8F5E9,stroke:#2E7D32,stroke-width:1px,color:#1B5E20;
  classDef rank fill:#FFF8E1,stroke:#EF6C00,stroke-width:1px,color:#E65100;
  classDef gen fill:#F3E5F5,stroke:#6A1B9A,stroke-width:1px,color:#4A148C;
  classDef guard fill:#FFEBEE,stroke:#C62828,stroke-width:1px,color:#B71C1C;
  classDef out fill:#E8EAF6,stroke:#3949AB,stroke-width:1px,color:#1A237E;

  %% ================= INGESTION & INDEXING =================
  subgraph ING["Ingestion & Indexing"]
    direction TB

    %% --- Preprocess ---
    subgraph PRE["Preprocess"]
      direction TB
      SRC["Sources"]:::inj
      UP["Upload or Sync"]:::inj
      CR["Crawler"]:::inj
      PARSE["Parse (DOCX/MD/HTML)"]:::proc
      CLEAN["Clean & Normalize"]:::proc
      SRC -->|files| UP
      SRC -->|discovery| CR
      UP --> PARSE
      CR --> PARSE
      PARSE --> CLEAN
    end

    %% --- Branch by domain (side-by-side) ---
    subgraph BRANCH["Domain Branching"]
      direction LR
      %% Legal lane
      subgraph LEG["Legal (collection: legal)"]
        direction TB
        L_CHUNK["Chunk by Article"]:::proc
        L_META["Attach metadata"]:::proc
        L_EMB["Embed (Qwen3 0.6B)"]:::ret
        L_UPS["Upsert to Qdrant"]:::store
        L_CHUNK --> L_META --> L_EMB --> L_UPS
      end

      %% Procedure lane
      subgraph PROC["Procedure (collection: procedure)"]
        direction TB
        P_CHUNK["Chunk 4 sections"]:::proc
        P_META["Attach metadata"]:::proc
        P_EMB["Embed (Qwen3 0.6B)"]:::ret
        P_UPS["Upsert to Qdrant"]:::storeTrình tự xử lý (Sequence: Request → Answer)
        P_CHUNK --> P_META --> P_EMB --> P_UPS
      end
    end

    CLEAN --> L_CHUNK
    CLEAN --> P_CHUNK
  end

  %% ====================== RAG PIPELINE =====================
  subgraph RAG["LangGraph RAG"]
    direction TB

    %% 1) Input & Validation
    subgraph INP["1 · Input & Validation"]
      direction TB
      IN["Input (query + history)"]:::op
      VAL_IN["Validate (Guardrails)"]:::guard
      IN -->|text| VAL_IN
    end

    %% 2) Query Analysis (NOW STEP 2)
    subgraph ANAL["2 · Query Analysis"]
      direction TB
      QANA["Query Analysis"]:::op
    end

    %% 3) Retrieval (per-collection search)
    subgraph RETR["3 · Retrieval"]
      direction TB
      EMB["Embed (Qwen3 0.6B)"]:::ret
      S_LEGAL["Qdrant Search (collection: legal)"]:::ret
      S_PROC["Qdrant Search (collection: procedure)"]:::ret
      MERGE["Merge candidates"]:::ret
    end

    %% 4) Ranking & Context
    subgraph RNK["4 · Ranking & Context"]
      direction TB
      RER["Rerank (BAAI/bge-reranker-v2-m3)"]:::rank
      CTX["Build Context (top-k)"]:::rank
    end

    %% 5) Generation
    subgraph GENR["5 · Generation"]
      direction TB
      GEN["Generate (Llama 4 - Bedrock)"]:::gen
    end

    %% 6) Output Validation
    subgraph OUTV["6 · Output Validation"]
      direction TB
      VAL_OUT["Validate (Guardrails)"]:::guard
      OUT["Final Answer"]:::out
    end
  end

  %% --------- RAG Edges (between subgraphs) ---------
  VAL_IN -->|ok| QANA
  QANA -->|plan| EMB
  EMB -->|route legal| S_LEGAL
  EMB -->|route procedure| S_PROC
  S_LEGAL --> MERGE
  S_PROC --> MERGE
  MERGE -->|candidates| RER
  RER -->|top-k| CTX
  CTX -->|prompt| GEN
  GEN -->|completion| VAL_OUT
  VAL_OUT -->|safe| OUT

  %% ------------- Bridges from indexing to RAG -------------
  L_UPS -->|legal collection| S_LEGAL
  P_UPS -->|procedure collection| S_PROC


```

### 1.2 kiến trúc voice chatbot

```mermaid
flowchart TB
  %% =================== STYLES ===================
  classDef client fill:#E8F5E9,stroke:#2E7D32,stroke-width:1px,color:#1B5E20;
  classDef api fill:#E3F2FD,stroke:#1565C0,stroke-width:1px,color:#0D47A1;
  classDef svc fill:#FFF3E0,stroke:#EF6C00,stroke-width:1px,color:#E65100;
  classDef data fill:#F3E5F5,stroke:#6A1B9A,stroke-width:1px,color:#4A148C;
  classDef gen fill:#EDE7F6,stroke:#5E35B1,stroke-width:1px,color:#4527A0;

  %% =================== CLIENT ===================
  subgraph CLIENT["Voice Client — React 18"]
    direction TB
    MIC["Mic Capture"]:::client
    AEC["Echo Cancel (AEC)"]:::client
    NR["Noise Reduction"]:::client
    VAD["VAD (webrtcvad)"]:::client
    ASR_C["ASR (PhoWhisper, local)"]:::client
    TTS["TTS (pyttsx3, local)"]:::client
    SPK["Speaker Output"]:::client

    MIC --> AEC --> NR --> VAD --> ASR_C
    TTS --> SPK
    SPK -->|playback ref| AEC
    VAD -. barge-in .-> TTS
  end

  %% =================== BACKEND ===================
  subgraph BACKEND["Backend — FastAPI"]
    direction TB
    API_VOICE["WebSocket /voice"]:::api
    CONV["Conversation Service (LangGraph RAG)"]:::svc
    LLM["Llama 4 (Bedrock)"]:::gen
  end

  %% =================== DATA ===================
  subgraph DATA["Data"]
    direction TB
    QDR["Qdrant (Vector DB)"]:::data
  end

  %% =================== FLOWS ===================
  %% Uplink (Client -> Server): chỉ gửi text
  ASR_C -->|text frames| API_VOICE

  %% Server pipeline
  API_VOICE -->|text frames| CONV
  CONV <--> |retrieval| QDR
  CONV -->|prompt| LLM
  LLM -->|completion tokens| CONV

  %% Downlink (Server -> Client)
  CONV -->|answer tokens| API_VOICE
  API_VOICE -->|text tokens| TTS

  %% =================== CLASS BINDINGS ===================
  class MIC,AEC,NR,VAD,ASR_C,TTS,SPK client;
  class API_VOICE api;
  class CONV svc;
  class QDR data;
  class LLM gen;
```

### 1.3 CCCD

### 1.4 Scan

---

## 2) Trình tự xử lý (Sequence: Request → Answer)

```mermaid
sequenceDiagram
  autonumber
  participant User
  participant TextUI as Chat UI (React)
  participant Voice as Voice Client (React)
  participant ASR as ASR Local (PhoWhisper)
  participant REST as REST /chat (FastAPI)
  participant WS as WS /voice (FastAPI)
  participant RAG as Conversation Service (LangGraph RAG)
  participant Qdrant
  participant LLM as Llama 4 (Bedrock)
  participant TTS as TTS Local
  participant Speaker

  Note over Voice: AEC -> NR -> VAD on client
  Note over REST,WS: Both use the same RAG pipeline

  alt Input: Text (Chat UI)
    User->>TextUI: Type message
    TextUI->>REST: POST /chat (text)
    REST->>RAG: Forward text
  else Input: Voice (ASR local)
    User->>Voice: Speak
    Voice->>ASR: PCM 16 kHz frames (10–20 ms)
    ASR-->>Voice: Text (partial/final)
    Voice->>WS: Send text frames
    WS->>RAG: Forward text
  end

  %% -------- Shared RAG pipeline --------
  RAG->>RAG: Validate input
  RAG->>RAG: Embed (Qwen3 0.6B)
  RAG->>Qdrant: Vector search (k)
  Qdrant-->>RAG: Candidates
  RAG->>RAG: Rerank (bge m3)
  RAG->>RAG: Build context
  RAG->>LLM: Prompt with context

  loop Stream tokens
    LLM-->>RAG: Token
    alt Text channel
      RAG-->>REST: Token
      REST-->>TextUI: Token
    else Voice channel
      RAG-->>WS: Token
      WS-->>Voice: Token
      Voice->>TTS: Token
      TTS->>Speaker: Audio
      Speaker-->>Voice: Playback reference -> AEC
    end
  end

  LLM-->>RAG: Done
  alt Final delivery (Text)
    RAG-->>REST: Final answer
    REST-->>TextUI: Final answer
  else Final delivery (Voice)
    RAG-->>WS: Final answer
    WS-->>Voice: Final answer
  end

  opt Barge-in (while TTS playing)
    User->>Voice: Speak
    Voice->>TTS: Stop playback
    Voice->>WS: Send new text
  end


```

---

## 3) Công nghệ & Frameworks

- **Frontend**: React 18 (SPA, WebSocket/HTTP, mic capture, UI).
- **Backend**: FastAPI (router `/chat`, REST & WebSocket).
- **RAG Orchestration**: LangGraph (state machine & nodes).
- **Vector Database**: Qdrant (HNSW/IVF, payload filter).
- **Embeddings**: Qwen3 0.6B.
- **Reranker**: BAAI/bge-reranker-v2-m3.
- **LLM**: Llama 4 trên AWS Bedrock (qua Boto3).
- **Observability**: Langfuse (tracing, errors, metrics, cost).
- **Guardrails**: Bedrock Guardrails (input/output moderation).

---

```mermaid
test ở đây
```
