# JurisCode - Master Project Documentation

**Document version:** 2.0 (expanded master reference)  
**Last aligned to repository:** May 2026  
**Repository:** JurisCode — **JurisCode Bharat** API lives under `backend/`

This file is the **primary, most detailed** narrative and reference for stakeholders, developers, and researchers. It deliberately repeats a few critical facts (especially the **separation** of mock trial vs Scenario Analyzer) so the document can be read standalone.

**Companion documents**

| Document | Use when you need |
|----------|-------------------|
| [BACKEND_SCHEMAS_AND_ENDPOINTS.md](./BACKEND_SCHEMAS_AND_ENDPOINTS.md) | Exact HTTP paths, request/response bodies, proposed `/api` naming |
| [SYSTEM_ARCHITECTURE_AND_WORKFLOW.md](./SYSTEM_ARCHITECTURE_AND_WORKFLOW.md) | Mermaid diagrams and visual architecture |
| [COMPONENT_WISE_EXECUTION.md](./COMPONENT_WISE_EXECUTION.md) | Per-component status tables and next steps |
| [MODEL_DETAILS_AND_TRAINING.md](./MODEL_DETAILS_AND_TRAINING.md) | Training artifacts, datasets, benchmarks |
| [OBJECTION_MODEL_RETRAINING_PLAN.md](./OBJECTION_MODEL_RETRAINING_PLAN.md) | Objection JSON target schema and validation |
| [SCENARIO_ANALYZER_CHATBOT.md](./SCENARIO_ANALYZER_CHATBOT.md) | Citizen chatbot design only (not mock trial) |
| [LEGAL_KNOWLEDGE_BASE_AND_SCRAPER.md](./LEGAL_KNOWLEDGE_BASE_AND_SCRAPER.md) | Intended `property_rights/` KB layout |
| [ROADMAP_AND_PENDING_WORK.md](./ROADMAP_AND_PENDING_WORK.md) | Priorities and pending work |

---

## Table of contents

1. [Project title](#1-project-title)  
2. [Executive summary](#2-executive-summary)  
3. [Project overview (two module groups)](#3-project-overview-two-module-groups)  
4. [Stakeholders, personas, and use cases](#4-stakeholders-personas-and-use-cases)  
5. [Detailed problem statement](#5-detailed-problem-statement)  
6. [Motivation](#6-motivation)  
7. [Objectives](#7-objectives)  
8. [Non-goals and boundaries](#8-non-goals-and-boundaries)  
9. [Scope](#9-scope)  
10. [Alignment with original synopsis](#10-alignment-with-original-synopsis)  
11. [Repository layout (high signal)](#11-repository-layout-high-signal)  
12. [Complete system modules](#12-complete-system-modules)  
13. [Mock trial: end-to-end technical flow](#13-mock-trial-end-to-end-technical-flow)  
14. [Backend configuration and operations](#14-backend-configuration-and-operations)  
15. [Data, models, and training pipeline](#15-data-models-and-training-pipeline)  
16. [Methodology](#16-methodology)  
17. [Execution criteria](#17-execution-criteria)  
18. [Tools and techniques](#18-tools-and-techniques)  
19. [Prototype and integration patterns](#19-prototype-and-integration-patterns)  
20. [Results and evaluation status](#20-results-and-evaluation-status)  
21. [Risks, limitations, and mitigations](#21-risks-limitations-and-mitigations)  
22. [Security, privacy, and compliance posture](#22-security-privacy-and-compliance-posture)  
23. [Future enhancements](#23-future-enhancements)  
24. [Glossary](#24-glossary)  
25. [Conclusion](#25-conclusion)

---

## 1. Project title

**JurisCode: Legal Literacy and Courtroom Reasoning Platform for Citizen Empowerment and Legal Education**

The name **JurisCode Bharat** appears in the FastAPI application metadata (`backend/app/main.py`) as the branding for the **legal reasoning and trial practice API** component.

---

## 2. Executive summary

JurisCode is designed as a **dual-track** platform:

1. **Mock trial / legal training (students and learners)**  
   A structured loop: **select topic and style → generate property-law premise → draft argument → receive opposing counsel challenge → receive objection/weakness feedback (including a numeric strength score) → reflect and retry.**  
   **Implemented today:** FastAPI backend with **local** inference (**Qwen2.5-3B-Instruct** + **PEFT LoRA** adapters for premise, opposing counsel, and objection roles). Session history is stored **in memory** only.

2. **Citizen Scenario Analyzer (legal literacy chatbot)**  
   A **separate** conversational surface where a citizen describes a **real-life** problem and receives **educational**, structured guidance (explanation, missing facts, possible rights/remedies/outcomes, reasoning trace, lawyer warning, disclaimer).  
   **Product direction:** MVP uses an **external LLM API** (not the local mock-trial stack).  
   **Repository status at last scan:** **No** dedicated Scenario Analyzer router was registered in `backend/app/main.py` — treat as **Planned** until code lands.

**Architectural rule (non-negotiable):** The Scenario Analyzer must **not** be documented or wired as part of the **mock-trial pipeline** (no shared “turn” that silently mixes citizen scenarios with student premises unless explicitly designed as a separate product mode with clear UX).

**Grounding rule:** **RAG**, **JSON rule matching**, and **Prolog/Datalog** are **future enhancements** unless explicitly implemented in the repository. Do not describe them as production features without code evidence.

---

## 3. Project overview (two module groups)

### 3.A Mock trial / legal training system

**Audience:** Law students, legal trainees, and motivated self-learners who want **adversarial practice** in **Indian property litigation**-style disputes.

**Conceptual components**

| Component | Role |
|-----------|------|
| Premise generator | Produces **fact-rich** dispute scenarios (parties, timeline, documents, possession, ambiguity) for training—not final legal conclusions. |
| Opposing counsel | Produces **adversarial** pushback grounded in the premise and the user’s draft argument. |
| Objection / weakness detector | Surfaces **objections**, **evidentiary/procedural/burden** issues, **contradictions**, **improvement suggestions**, and an **argument strength score**. |
| Learning dashboard | Presents **score**, **feedback**, **improvements**, and supports **retry** loops. |
| Session / history | Enables multiple attempts and review of past turns. |

**Canonical user journey (product narrative)**

1. User or student opens the platform.  
2. Selects **legal domain or topic** (in the current API this is a **curated topic string** plus a **generation mode** that controls narrative style).  
3. **Premise generator** creates a **realistic property litigation** scenario.  
4. User writes a **legal argument** in response to that premise.  
5. **Opposing counsel** generates an **adversarial challenge**.  
6. **Objection / weakness detector** analyzes **weaknesses and missing elements**.  
7. **Learning dashboard** shows **score, feedback, improvements**, and supports **retry**.

**Implementation truth table**

| Step | Backend support | UI support (repo scan) |
|------|-----------------|-------------------------|
| Topic/mode selection | `GET /premise/topics`, `GET /premise/modes` | **Planned** |
| Premise | `POST /premise/generate`, `POST /practice/start` | **Planned** |
| Argument + opposing + objection | `POST /practice/argument`, or compose `/opposing/challenge` + `/objection/evaluate` | **Planned** |
| Dashboard / retry | Payload includes score + structured lists + `GET /practice/session/{id}` history | **Partial** (API only) |

### 3.B Citizen Scenario Analyzer chatbot

**Audience:** **Ordinary citizens** who may not know legal terminology.

**Example input:** “My landlord is forcing me to leave before the agreement ends.”

**Target output categories (legal literacy, not decisive advice)**

| Output | Why it matters |
|--------|----------------|
| Scenario summary | Reduces confusion; anchors the rest of the response. |
| Detected domain / issue type | Helps the user name what kind of problem it resembles. |
| Simplified explanation | Bridges jargon gap. |
| Facts identified vs missing | Reduces “jumping to conclusions” without key facts. |
| Rights possibly involved / remedies / outcomes | Educational framing of **possibilities**, not guarantees. |
| Reasoning trace | Supports transparency (subject to model honesty limits). |
| Lawyer warning + disclaimer | Risk communication and non-advice posture. |

**Independence requirements**

- Must **not** reuse the **premise generator** as if the citizen’s life story were a “student hypothetical.”  
- Must **not** route through `/practice` unless the product explicitly adds a **separate** citizen mode (not recommended without careful UX).  
- MVP remains **API-based** external LLM; **not RAG-based** unless retrieval is implemented.

**Status:** **Planned** backend route and client integration — see [SCENARIO_ANALYZER_CHATBOT.md](./SCENARIO_ANALYZER_CHATBOT.md).

---

## 4. Stakeholders, personas, and use cases

### 4.1 Primary stakeholders

| Stakeholder | Interest |
|-------------|----------|
| **Law students / trainees** | Repeatable practice, structured critique, exam/clinic-style reasoning drills. |
| **Educators / clinics** | Controlled scenarios, reduced setup time, consistent adversarial feedback (with human supervision recommended). |
| **Citizens (non-lawyers)** | Plain-language orientation, safer expectations, guidance on “what to ask a lawyer.” |
| **Engineering / ML team** | Maintainable services, reproducible datasets, evaluation harnesses, deployment paths. |
| **Legal reviewers (recommended)** | Periodic review of prompts, dataset bias, and high-risk outputs—especially before public release. |

### 4.2 Personas

**Persona A — “Asha, law student”**  
Needs weekly practice drafting **issue spotting** and **argument structure** under time pressure. Uses mock trial mode: premise → argument → opposing → objection → revise.

**Persona B — “Ravi, tenant”**  
Needs to understand whether his situation might involve **notice**, **illegal eviction risk**, or **forum options**. Uses Scenario Analyzer: describes facts → receives educational framing → is warned to consult local counsel if risk keywords appear.

**Persona C — “Dr. Mehta, clinic supervisor”**  
Needs auditability: wants **history**, **consistent disclaimers**, and eventually **grounded citations** from a knowledge base (future RAG).

### 4.3 Representative use cases (mock trial)

| ID | Use case | Primary endpoints |
|----|----------|-------------------|
| MT-1 | Generate a new training premise for “boundary dispute” | `POST /premise/generate` |
| MT-2 | Student writes argument; wants adversarial response only | `POST /opposing/challenge` |
| MT-3 | Student wants critique + score only | `POST /objection/evaluate` |
| MT-4 | Full loop with server-side session | `POST /practice/start` → `POST /practice/argument` → `GET /practice/session/{id}` |

### 4.4 Representative use cases (Scenario Analyzer — planned)

| ID | Use case | Expected endpoint (proposed) |
|----|----------|------------------------------|
| SA-1 | Citizen describes landlord conflict | `POST /api/scenario/analyze` (or `/scenario/analyze` without gateway prefix) |
| SA-2 | Citizen adds state/language context | `user_context` object in request JSON |

---

## 5. Detailed problem statement

### 5.1 Citizen-side problems

- **Opaque legal language:** Statutes and judgments are hard to parse without training; citizens may misinterpret even basic terms like “possession,” “title,” “injunction,” or “specific performance.”  
- **Unknown unknowns:** People may not realize what facts matter (notice, registration, payment trail, factual possession timeline).  
- **Harm from confident wrong answers:** Generic chatbots can sound authoritative while omitting jurisdictional nuance, evidentiary requirements, or urgency (e.g., possession loss).

### 5.2 Student-side problems

- **Passive learning limits transfer:** Reading alone rarely trains **adversarial thinking** under uncertainty.  
- **Feedback scarcity:** Peers and supervisors are time-constrained; consistent “opposing counsel” practice is hard to scale.  
- **Hallucinated authority:** Models may invent citations unless constrained; that is especially dangerous in legal education settings if students treat outputs as “authorities.”

### 5.3 System-level gap

There is a gap between **raw legal corpora** and **usable pedagogy**. JurisCode addresses this by combining:

- **Synthetic scenario generation** and **adapters specialized by role** (premise vs opposing vs objection).  
- **Structured critique fields** (today via parsing; tomorrow via JSON-native objection outputs).  
- A **separate** citizen literacy channel (planned) with explicit **disclaimers** and **lawyer escalation** paths.  
- A roadmap toward **scraped/normalized law** and **RAG** for grounding (not claimed as shipped).

---

## 6. Motivation

- **Access to legal awareness:** Lower the activation energy to understand “what kind of problem is this?”  
- **Citizen empowerment:** Clarify options and questions to ask counsel—without replacing counsel.  
- **SDG 4 (Quality Education):** Promote structured learning, practice, and explainability.  
- **Legal literacy for non-lawyers:** Scenario Analyzer track.  
- **Practical training for law students:** Mock-trial track with adversarial pressure.  
- **Interactive learning:** Tight feedback loops beat one-shot reading.  
- **Narrowing the law–citizen gap:** Plain language + explicit uncertainty + missing-fact prompts.  
- **Explainable reasoning (directional):** Move from opaque chat to **structured fields**, traces, and (future) citations.

---

## 7. Objectives

### 7.1 Primary objectives

1. Build a **property-focused legal training simulation** (mock trial track).  
2. Generate **realistic** property-law **premises** with factual ambiguity suitable for argument practice.  
3. Enable users to **practice drafting legal arguments** against those premises.  
4. Generate **opposing counsel-style challenges** that stress-test reasoning.  
5. Detect **weaknesses, objections, missing evidence**, and related **gaps**.  
6. Provide **feedback** suitable for a **learning dashboard** (API-complete; UI pending).  
7. Build a **separate** **Citizen Scenario Analyzer** chatbot for real-life scenarios.  
8. Provide **simplified explanations** for common legal situations (citizen track).  
9. Add **safety disclaimers** and **lawyer consultation warnings** where appropriate.  
10. Prepare the architecture for **future RAG** and **rule-based / symbolic** reasoning layers.

### 7.2 Secondary objectives

1. Maintain **clean, versioned JSONL** datasets and clear provenance for synthetic generation.  
2. Keep training and inference **modular** (separate adapters per role).  
3. Document **APIs and schemas** (OpenAPI at `/docs` plus `docs/` markdown).  
4. Organize **legal scraper outputs** into a predictable folder taxonomy when available.  
5. Enable **future domain expansion** beyond the current property-first focus.  
6. Enable **future multilingual** support for citizen literacy.

---

## 8. Non-goals and boundaries

The following are explicit **non-goals** for the current repository positioning:

| Non-goal | Rationale |
|----------|-----------|
| **Final legal advice** | Only licensed professionals can advise on specific matters. |
| **Lawyer replacement** | Tooling is educational and simulative. |
| **Guaranteed outcomes** | Litigation outcomes depend on facts, evidence, judges, procedure, and jurisdiction. |
| **Automated court filings** | High risk; out of scope. |
| **Universal coverage of Indian law** | Current training emphasis is **property litigation** style scenarios. |
| **Claiming RAG/Prolog without implementation** | Documentation must track **code truth**. |

---

## 9. Scope

### 9.1 Current scope (evidence-backed)

| Capability | Status | Evidence |
|------------|--------|----------|
| FastAPI service | **Completed** | `backend/app/main.py`, `backend/run.py` |
| Local HF + PEFT inference | **Completed** | `backend/app/core/model_manager.py` |
| Premise endpoints | **Completed** | `backend/app/routers/premise.py` |
| Opposing endpoints | **Completed** | `backend/app/routers/opposing.py` |
| Objection endpoints | **Partially completed** | `routers/objection.py` + `utils/text_utils.py` parsing |
| Practice session flow | **Completed** | `routers/practice.py`, `services/session_service.py` |
| Training artifacts | **Completed** | `all_models/`, `dataset_generation/`, `ipynbFiles/` |
| Synthetic dataset generation (Gemini) | **Completed** | `dataset_generation/generate_dataset.py` (API key driven) |
| Scenario Analyzer backend | **Planned** | No router import in `main.py` at last scan |
| Frontend app in this repo | **Planned** | No TS/JS app tree at repo root in last scan |
| `property_rights/` scraper corpus | **Planned / To be verified** | Directory not found in last scan |

### 9.2 Out of current scope / future scope

- Full **RAG** and **citation-grounded** citizen answers at scale  
- **Prolog/Datalog** reasoning in production  
- Complete **legal ontology**  
- **Production-grade** legal advice workflows  
- **All** Indian legal domains without additional datasets and review  

---

## 10. Alignment with original synopsis

Typical synopsis themes for a computational legal education project include:

- Legal **literacy** and **citizen empowerment**  
- **Simplification** and **scenario-based** understanding  
- **Computational legal reasoning**  
- **Explainable** logic and structured outputs  
- **SDG 4** alignment (quality education)

**Mapping to the repository today**

| Synopsis theme | Where it shows up now | Where it is planned |
|----------------|----------------------|---------------------|
| Legal education | Mock-trial APIs + LoRA roles | Frontend learning paths |
| Citizen literacy | Documented Scenario Analyzer design | Backend route + UI |
| Computational reasoning | Local LLM inference + adapter switching | Optional symbolic layer |
| Explainability | Objection lists + score + raw text | JSON-native objection; RAG citations |
| Knowledge base | Datasets + intended scraper layout | `property_rights/` + chunking + vector index |

---

## 11. Repository layout (high signal)

```text
JurisCode/
├── README.md                 # Project overview + API table + disclaimer
├── docs/                     # Professional documentation set (this file)
├── backend/                  # FastAPI app (JurisCode Bharat API)
│   ├── app/
│   │   ├── main.py           # App entry, CORS, router includes, lifespan model load
│   │   ├── core/             # config.py, model_manager.py
│   │   ├── routers/          # health, premise, opposing, objection, practice
│   │   ├── schemas/          # Pydantic models per router
│   │   ├── services/         # generation_service.py, session_service.py
│   │   └── utils/            # text_utils.py (objection parsing)
│   ├── requirements.txt
│   ├── run.py
│   ├── .env.example
│   └── ARCHITECTURE.md       # Backend architecture (Mermaid)
├── all_models/               # Notebooks, datasets, benchmarks, adapter exports
├── dataset_generation/       # Scripts (includes Gemini-based synthetic JSONL)
├── models/                   # Optional slim adapter copies for deployment paths
└── ipynbFiles/               # Additional notebook copies
```

**Important naming note:** The canonical training tree is **`all_models/`**. The optional **`models/`** directory can hold trimmed exports referenced by `.env` paths (see root `README.md`).

---

## 12. Complete system modules

### 12.1 Frontend interface

| Item | Detail |
|------|--------|
| Purpose | Mode selection; mock trial screens; **separate** Scenario Analyzer UI; dashboard. |
| Expected surfaces | Topic/mode picker; premise reader; argument editor; opposing panel; objection panel; session timeline; chatbot view for citizens. |
| Repo status | **Planned** in this repository snapshot; CORS allows `http://localhost:3000` and `http://localhost:5173` in `main.py`. |
| Integration contract | Client must call correct endpoints; must not merge citizen flow into `/practice` without explicit product design. |

### 12.2 Backend API layer

| Item | Detail |
|------|--------|
| Framework | **FastAPI** |
| Routers | `health`, `premise`, `opposing`, `objection`, `practice` |
| OpenAPI | `/docs`, `/redoc` |
| Core runtime | `ModelManager` loads tokenizer + causal LM + LoRA adapters (if paths resolve) |
| Degraded mode | API may start without successful model load; health endpoints still respond |

### 12.3 Premise generator model

| Item | Detail |
|------|--------|
| Purpose | Generate **training premises** only (no advice/holding in the premise prompt design). |
| Prompting | System prompt in `generation_service.py` forbids legal analysis in premise generation. |
| Topics | Curated `TOPICS` list in `schemas/premise.py` (e.g., title dispute, partition suit, tenant eviction, RERA complaint). |
| Modes | Curated `GENERATION_MODES` (e.g., “messy real-world property disputes”). |
| Artifacts | `all_models/premise_model/`, JSONL datasets, training notebooks |

### 12.4 Opposing counsel model

| Item | Detail |
|------|--------|
| Purpose | Adversarial challenge: title/possession/procedure/evidence/burden/contradictions. |
| Safety instruction | Prompt instructs: **do not invent case citations** (`generation_service.py`). |
| Artifacts | Large JSONL dataset + `all_models/opposing_counsel/` + benchmark scripts |

### 12.5 Objection / weakness detector

| Item | Detail |
|------|--------|
| Purpose | Structured training feedback and strength scoring. |
| Current output shape | API returns `ObjectionEvaluateResponse` fields (lists + int score + raw). |
| Parser | `parse_objection_evaluation()` is **best-effort** over model prose. |
| Improvement direction | Retrain for **valid JSON** assistant outputs aligned to property litigation (see objection plan). |

### 12.6 Learning dashboard

| Item | Detail |
|------|--------|
| Purpose | Present score, narrative feedback, improvements, retry. |
| Current realization | **API payloads** and **session history** (`/practice/session/{id}`). |
| UI | **Planned** |

### 12.7 Legal scraper / knowledge base

| Item | Detail |
|------|--------|
| Purpose | Future grounding, citations, retrieval, and hallucination control. |
| Intended structure | `property_rights/{acts,articles,cases,constitution,sections}/` |
| Repo status | **Not evidenced** in last scan; treat as roadmap |

### 12.8 Citizen Scenario Analyzer chatbot

| Item | Detail |
|------|--------|
| Purpose | Separate citizen literacy product surface. |
| MVP | External LLM API + JSON validation + safety layer (planned). |
| Excluded from | Premise/opposing/objection/practice pipeline |

---

## 13. Mock trial: end-to-end technical flow

### 13.1 Request lifecycle (practice mode)

1. **Start:** `POST /practice/start`  
   - Chooses `topic` and `mode` (explicit or randomized).  
   - Calls `GenerationService.generate_premise()`.  
   - Creates an in-memory session via `SessionService.create()`.

2. **Argument submission:** `POST /practice/argument`  
   - Loads premise from session.  
   - Runs `generate_opposing()` then `generate_objection()`.  
   - Parses objection output via `parse_objection_evaluation()`.  
   - Appends a history record via `session_service.add_argument()`.

3. **Review:** `GET /practice/session/{session_id}`  
   - Returns topic/mode/premise and full argument history.

### 13.2 Alternative composition (granular endpoints)

Some clients may prefer:

- `POST /premise/generate` (also creates a session today)  
- `POST /opposing/challenge` (optional `session_id` to reuse premise)  
- `POST /objection/evaluate` (optional `session_id`)

This pattern supports UI designs that fetch opposing and objection feedback independently (e.g., progressive disclosure).

### 13.3 Adapter switching mechanics (critical implementation detail)

`ModelManager` loads one base model and attaches multiple LoRA adapters when adapter directories resolve. At generation time, `GenerationService` calls `set_adapter("premise" | "opposing" | "objection")` before `generate()`.

**Operational implication:** Latency includes adapter switching overhead; batching strategies should be considered for future UX (not implemented as a batch endpoint today).

---

## 14. Backend configuration and operations

### 14.1 Environment variables (from `backend/app/core/config.py`)

| Variable | Role |
|----------|------|
| `BASE_MODEL_NAME` | HF hub id or local path for base causal LM (default `Qwen/Qwen2.5-3B-Instruct`) |
| `PREMISE_ADAPTER_PATH` | Directory containing PEFT adapter files for premise role |
| `OPPOSING_COUNSEL_ADAPTER_PATH` | Directory for opposing counsel adapter |
| `OBJECTION_ADAPTER_PATH` | Directory for objection adapter |
| `USE_4BIT` | Optional 4-bit quantization path on CUDA (bitsandbytes) |
| `DEFAULT_MAX_NEW_TOKENS`, `DEFAULT_TEMPERATURE`, `DEFAULT_TOP_P`, `DEFAULT_REPETITION_PENALTY` | Decoding defaults |
| `LOCAL_FILES_ONLY` | Disallow Hub downloads when true |
| `TRUST_REMOTE_CODE` | Passed through to HF loading |
| `HF_DISABLE_SSL_VERIFY` | Insecure debugging escape hatch (warned in logs) |

Paths resolve relative to the **`backend/`** root unless absolute.

### 14.2 Runtime dependencies and hardware expectations

- **CUDA strongly recommended** for acceptable latency; CPU is supported with warnings.  
- Model download may occur on first run unless cached or `LOCAL_FILES_ONLY=true` with local snapshots.  
- Git LFS may be required for large weights in some clones (see root `README.md`).

### 14.3 Known documentation maintenance item

`backend/README.md` was observed to contain **corrupted / merged** content in a prior scan. Treat repair as a maintenance task; do not assume it matches `README.md` at repo root.

---

## 15. Data, models, and training pipeline

### 15.1 Dataset formats

Primary supervised fine-tuning style rows use chat messages:

```json
{
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

This pattern appears in premise training JSONL (e.g. `all_models/premise_model/property_premise_dataset_train_ready.jsonl`).

### 15.2 Synthetic dataset generation (important distinction)

`dataset_generation/generate_dataset.py` uses **Google Gemini** (`google.genai`) with `GEMINI_API_KEY` for **dataset synthesis**. This is **not** the same as the backend inference stack, which is described as **local Qwen + LoRA** in the root `README.md`.

**Why this matters:** Governance for API keys, spend, and data handling applies to dataset scripts separately from deployment inference.

### 15.3 Objection dataset caveat (to verify)

The objection training JSONL under `dataset_generation/` should be audited for **domain alignment** (property litigation courtroom training vs other domains). Misaligned training data is a common cause of “right architecture, wrong behavior.”

### 15.4 Benchmarks and evaluation artifacts

The repository includes benchmark runners and output JSON under `all_models/` (e.g., opposing and premise dual benchmark scripts, `all_models/benchmark_outputs/`). Treat quantitative “final scores” as **To be updated after final benchmark validation** unless a pinned evaluation report is added.

---

## 16. Methodology

1. **Requirements:** Separate citizen vs student journeys; define safety posture per track.  
2. **Domain selection:** Property litigation first; enumerate topics/modes in code for consistency.  
3. **Dataset creation:** JSONL chat transcripts; synthetic generation plus manual QA targets.  
4. **Fine-tuning:** Role-specific LoRA adapters on a shared base model; export adapters for inference.  
5. **Service integration:** Single `ModelManager` to reduce memory duplication; explicit adapter switching.  
6. **Parsing strategy:** Heuristic parsing for objection until JSON compliance is high enough to parse strictly.  
7. **Evaluation:** Benchmark JSON + (optional) external LLM rubric prompts in benchmark tooling—**To be verified** per team process.  
8. **Citizen MVP:** External API + schema validation + keyword safety checks (planned).  
9. **Knowledge base:** Scrape → structured JSON → normalize → chunk → index → RAG (future).  
10. **Continuous improvement:** Retrain objection; add UI; add persistence; add grounding.

---

## 17. Execution criteria

### 17.1 Functional acceptance (mock trial)

| Requirement | Meaning of “done” |
|-------------|-------------------|
| Premise generation | Returns a coherent premise for valid topic/mode inputs under normal operating conditions. |
| Opposing generation | Returns adversarial text referencing premise facts at a useful frequency (qualitative rubric). |
| Objection generation | Returns non-empty feedback lists or a meaningful summary; score within 0–100. |
| Sessions | Stable session IDs for a single server process; history grows monotonically with submissions. |

### 17.2 Technical acceptance

| Requirement | Meaning of “done” |
|-------------|-------------------|
| OpenAPI accuracy | `/docs` matches deployed routers and schemas. |
| Configurability | `.env` can point adapters to `models/` or `all_models/` exports. |
| Failure transparency | Health and model status endpoints reflect load failures. |

### 17.3 Safety acceptance

| Requirement | Meaning of “done” |
|-------------|-------------------|
| Non-advice posture | Product copy and API docs reinforce educational use. |
| Citation hygiene | Prompts discourage invented case citations in training simulators. |
| Citizen track | Disclaimers + lawyer warning fields present once implemented. |

---

## 18. Tools and techniques

### 18.1 Implemented / evidenced

- Python, FastAPI, Uvicorn, Pydantic v2  
- PyTorch, Hugging Face Transformers, PEFT  
- Optional bitsandbytes 4-bit loading on CUDA  
- JSON/JSONL datasets; benchmark scripts  
- Jupyter notebooks for training workflows  
- Google Gemini API for **dataset_generation** scripts (not inference path per root README)

### 18.2 Planned / future

- Frontend framework (React/Vite or other) — **To be verified**  
- External LLM client for Scenario Analyzer — **Planned**  
- Vector database + retriever (RAG) — **Future enhancement**  
- JSON rules + Prolog/Datalog experiments — **Future enhancement**

---

## 19. Prototype and integration patterns

### 19.1 Minimal client sequence (practice)

```http
POST /practice/start
POST /practice/argument
GET /practice/session/{session_id}
```

### 19.2 Minimal client sequence (premise + granular)

```http
POST /premise/generate
POST /opposing/challenge
POST /objection/evaluate
```

### 19.3 Session ID behavior (important)

`SessionService` stores sessions in a Python dict:

- **Data is lost on process restart.**  
- **Not suitable for multi-instance deployment** without replacement storage.

This is acceptable for local prototypes; it is a **key limitation** for production.

---

## 20. Results and evaluation status

| Area | What exists | What is pending |
|------|-------------|------------------|
| Premise quality | Benchmark scripts + JSON outputs | Consolidated report + human rubric sign-off |
| Opposing quality | Benchmark scripts + outputs | Same |
| Objection quality | Parser + subjective review | Retrain + JSON schema compliance metrics |
| Scenario Analyzer | Design docs | Implementation + red-team testing |

**Aggregate benchmark scores:** To be updated after final benchmark validation.

---

## 21. Risks, limitations, and mitigations

| Risk | Impact | Mitigation (current or planned) |
|------|--------|----------------------------------|
| Hallucinated citations | Misleads learners/citizens | Prompt bans + future RAG citations + human review for high-stakes releases |
| Wrong jurisdiction / state law | Incorrect guidance | Scenario Analyzer should collect `user_context.state` (planned) + disclaimers |
| Over-reliance on strength score | False precision | Present score as heuristic; encourage revision loops |
| Volatile sessions | Lost progress | Planned DB persistence |
| Misaligned objection training data | Weak property feedback | Audit JSONL; retrain (see objection plan) |
| External API costs/leakage | Ops/security | Secrets in `.env` only; rate limits; logging policy |

---

## 22. Security, privacy, and compliance posture

### 22.1 Secrets and configuration

- Do not commit `.env` files or API keys (see root `README.md` security section).  
- `GEMINI_API_KEY` is relevant to dataset scripts; any future Scenario Analyzer provider keys must follow the same hygiene.

### 22.2 Data handling

- In-memory sessions: minimize storing personally identifying information in prompts until a retention policy exists.  
- If logs capture user arguments, treat logs as **sensitive** (legal content).

### 22.3 Product compliance framing

This platform is **educational** and must not be marketed as a lawyer substitute. Disclaimers should remain visible in UI for both tracks.

---

## 23. Future enhancements

- **RAG** over normalized legal chunks from `property_rights/` (or equivalent KB)  
- **Chunk normalization pipeline** (stable IDs, citations, jurisdiction tags)  
- **Vector database** and hybrid retrieval (semantic + metadata filters)  
- **JSON legal rule engine** for deterministic guardrails  
- **Prolog/Datalog** prototypes for explainable rule chains (research-grade)  
- **Multilingual** citizen literacy and localized statutory references  
- **Voice** input/output for accessibility  
- **Broader domains** beyond property (requires new datasets and review)  
- **User feedback loop** to flag bad outputs  
- **Admin tools** for dataset and KB curation  

---

## 24. Glossary

| Term | Meaning in JurisCode |
|------|----------------------|
| **Mock trial track** | Student simulation: premise → argument → opposing → objection → retry. |
| **Scenario Analyzer** | Separate citizen chatbot track; external API MVP; not mock trial. |
| **LoRA / PEFT** | Low-rank adaptation weights loaded on top of a shared base model. |
| **Adapter switching** | Selecting which LoRA weights are active for the next generation call. |
| **Premise** | Synthetic fact pattern for training (not a court judgment). |
| **Objection model** | Evaluator role producing critique; distinct from courtroom “objection sustained” in a literal trial transcript sense. |
| **RAG** | Retrieval-augmented generation; **future** unless implemented. |
| **JSONL** | JSON lines format for datasets (one JSON object per line). |

---

## 25. Conclusion

JurisCode is intentionally **two-minded**: it supports **rigorous, adversarial legal training** for learners working inside **controlled property-law premises**, and it aims—via a **separate** **Citizen Scenario Analyzer**—to improve **legal literacy** for real-world stories told in plain language. Keeping these tracks **separate in architecture and documentation** reduces safety risk, reduces user confusion, and preserves a credible roadmap: **local specialized models** for pedagogy today, and **retrieval + rules + symbolic methods** as disciplined **future enhancements** rather than implied shipped features.

For day-to-day engineering status, use [COMPONENT_WISE_EXECUTION.md](./COMPONENT_WISE_EXECUTION.md) and [ROADMAP_AND_PENDING_WORK.md](./ROADMAP_AND_PENDING_WORK.md).
