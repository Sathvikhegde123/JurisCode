# System Architecture and User Workflow

This document uses **Mermaid** diagrams. **Mock trial** flows and the **Citizen Scenario Analyzer** are kept **strictly separate**.

---

## 1. Original Mock Trial Workflow

```mermaid
flowchart TD
    A[User or Student Opens Platform] --> B[Selects Legal Domain or Topic]
    B --> C[Premise Generator Model]
    C --> D[Realistic Property Litigation Scenario]
    D --> E[User Writes Legal Argument]
    E --> F[Opposing Counsel Model]
    E --> G[Objection or Weakness Detector]
    F --> H[Adversarial Challenge Response]
    G --> I[Objection Feedback and Missing Elements]
    H --> J[Learning Dashboard]
    I --> J
    J --> K[Score Feedback Improvements Retry]
```

**Explanation:** This is the **main legal training workflow** for law students and learners: synthetic premise → drafted argument → adversarial response → structured critique → reflective loop. **The Citizen Scenario Analyzer chatbot is not part of this flow.**

**Implementation note:** Today the backend exposes this logic primarily via **REST** (`/premise`, `/opposing`, `/objection`, `/practice`). A **standalone Learning Dashboard UI** is **not** present in the repository scan; dashboard behavior is **partially** realized through API payloads (`objection_feedback`, score).

---

## 2. Full Platform Architecture

```mermaid
flowchart TD
    U[User] --> FE[Frontend Interface]
    FE --> M[Mode Selection]

    M --> MT[Mock Trial Mode]
    M --> SA[Citizen Scenario Analyzer Chatbot]

    MT --> PM[Premise Generator Model]
    PM --> SC[Property Litigation Scenario]
    SC --> ARG[User Legal Argument]
    ARG --> OC[Opposing Counsel Model]
    ARG --> OBJ[Objection Weakness Detector]
    OC --> DASH[Learning Dashboard]
    OBJ --> DASH

    SA --> API[Scenario Analyzer API]
    API --> PROMPT[Prompt Builder]
    PROMPT --> LLM[External LLM API]
    LLM --> PARSE[JSON Parser]
    PARSE --> SAFETY[Safety Warning Layer]
    SAFETY --> CARDS[Citizen Friendly Response Cards]

    FE --> KB[Legal Scraper Data]
    KB --> ACTS[Acts JSON]
    KB --> CASES[Cases JSON]
    KB --> SECTIONS[Sections JSON]
    KB --> ARTICLES[Articles JSON]
    KB --> CONST[Constitution JSON]

    KB -. Future RAG Integration .-> API
```

**Explanation:** The **frontend** and **Scenario Analyzer backend branch** are shown as the **intended** full platform. **As of repository scan:** FastAPI implements **Mock Trial Mode** services locally; **Scenario Analyzer**, **KB on disk**, and **production frontend** are **not** found as runnable code in-tree. The dashed line marks **future RAG** from scraper data into the analyzer.

---

## 3. Scenario Analyzer Chatbot Workflow

```mermaid
flowchart TD
    A[Citizen Opens Scenario Analyzer] --> B[Enters Real Life Legal Problem]
    B --> C[Backend Receives Scenario]
    C --> D[Input Validation]
    D --> E[API Prompt Construction]
    E --> F[External LLM API]
    F --> G[Structured JSON Response]
    G --> H[Safety Keyword Check]
    H --> I[Frontend Chatbot or Cards]
    I --> J[Explanation Rights Remedies Outcomes Warning]
```

**Explanation:** This is the **target MVP** for citizens: external LLM for generation, JSON-first contract, safety gating, then UI. **Status:** **Planned** (no `/scenario` router in `backend/app/main.py` at scan).

---

## 4. Future Scenario Analyzer With RAG

**Label: Future Enhancement (not implemented in repo).**

```mermaid
flowchart TD
    A[Citizen Scenario] --> B[Fact Extraction]
    B --> C[Issue Classification]
    C --> D[RAG Retriever]
    D --> E[Legal Knowledge Base]
    E --> F[Relevant Legal Chunks]
    F --> G[Rule Matcher]
    G --> H[Rights and Remedies Mapper]
    H --> I[Reasoning Trace]
    I --> J[Safety Layer]
    J --> K[Citizen Friendly Output]
```

**Explanation:** Adds **retrieval** and optional **rule** layers so answers can be **source-grounded** and more auditable. **JSON rule matcher** and **Prolog/Datalog** remain **future** unless explicitly implemented.

---

## 5. Legal Scraper Pipeline

```mermaid
flowchart TD
    A[Raw Legal Sources] --> B[Scraper Parser]
    B --> C[Parsed JSON Output]
    C --> D1[Acts Folder]
    C --> D2[Articles Folder]
    C --> D3[Cases Folder]
    C --> D4[Constitution Folder]
    C --> D5[Sections Folder]
    D1 --> E[Future Normalization]
    D2 --> E
    D3 --> E
    D4 --> E
    D5 --> E
    E --> F[Unified Legal Chunks]
    F --> G[Future Vector Store]
    G --> H[Future RAG Retrieval]
```

**Explanation:** Describes how raw law could flow into structured JSON, then normalized chunks, then a vector index for RAG. **Repository scan:** `property_rights/` output tree **not found**; treat scraper runtime as **Planned / To be verified**.

---

## 6. Technology Stack (Architecture Layer)

| Layer | Technology |
|-------|------------|
| HTTP API | FastAPI + Uvicorn |
| Inference | PyTorch + Transformers + PEFT |
| Sessions | In-memory dict (`SessionService`) |
| Optional quantization | bitsandbytes 4-bit on CUDA |

---

## 7. Deployment View (Logical)

```text
Client (browser) ──HTTP──> FastAPI (localhost:8000)
                              │
                              ├──> ModelManager (GPU/CPU)
                              │       └── Qwen2.5-3B + LoRA adapters
                              │
                              └──> SessionService (RAM-only)
```

**Future:** external LLM client for Scenario Analyzer; database for sessions; vector DB for RAG.
