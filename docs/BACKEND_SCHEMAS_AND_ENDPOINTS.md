# Backend Schemas and Endpoint Details

**Framework:** FastAPI (`backend/app/main.py`).  
**Entry:** `backend/run.py` (uvicorn).  
**Config:** `backend/app/core/config.py` (environment variables via `python-dotenv`, `.env` beside backend).  
**Routers:** `backend/app/routers/` — `health`, `premise`, `opposing`, `objection`, `practice`.  
**Services:** `generation_service.py`, `session_service.py`.  
**Utilities:** `text_utils.py` (objection output parsing).

**Important:** Routers are mounted **without** a global `/api` prefix in code. If documentation elsewhere uses `/api/...`, assume an **optional gateway convention** or map paths accordingly.

---

## 1. Existing Backend Overview

| Concern | Location / notes |
|---------|------------------|
| Main app | `backend/app/main.py` |
| CORS | `localhost:3000`, `localhost:5173` |
| Model load | Lifespan → `model_manager.load()` |
| Env vars | `BASE_MODEL_NAME`, `PREMISE_ADAPTER_PATH`, `OPPOSING_COUNSEL_ADAPTER_PATH`, `OBJECTION_ADAPTER_PATH`, `USE_4BIT`, `DEFAULT_*`, `LOCAL_FILES_ONLY`, `TRUST_REMOTE_CODE`, `HF_DISABLE_SSL_VERIFY` |

**Scenario Analyzer:** **No** router registered in `main.py` at scan time — see Section 4 for **proposed** contract.

---

## 2. Existing Endpoints

| Method | Path | Purpose | Request body / params | Response (summary) | Status |
|--------|------|---------|------------------------|---------------------|--------|
| `GET` | `/` | Service metadata | — | `service`, `docs`, `health` keys | **Completed** |
| `GET` | `/health` | Liveness + device + model load flag | — | `status`, `device`, `models_loaded` | **Completed** |
| `GET` | `/models/status` | Adapter + dtype + hub flags | — | Model manager status dict | **Completed** |
| `GET` | `/premise/topics` | List curated topics | — | `{ "topics": [...] }` | **Completed** |
| `GET` | `/premise/modes` | List generation modes | — | `{ "modes": [...] }` | **Completed** |
| `POST` | `/premise/generate` | Generate premise + create session | `PremiseGenerateRequest` | `PremiseGenerateResponse` | **Completed** |
| `POST` | `/opposing/challenge` | Opposing counsel text | `OpposingChallengeRequest` | `OpposingChallengeResponse` | **Completed** |
| `POST` | `/objection/evaluate` | Parsed objection feedback | `ObjectionEvaluateRequest` | `ObjectionEvaluateResponse` | **Completed** |
| `POST` | `/practice/start` | Start session + premise | `PracticeStartRequest` | `PracticeStartResponse` | **Completed** |
| `POST` | `/practice/argument` | Opposing + objection + history | `PracticeArgumentRequest` | `PracticeArgumentResponse` | **Completed** |
| `GET` | `/practice/session/{session_id}` | Session details | path `session_id` | `SessionDetailsResponse` | **Completed** |

OpenAPI: **`/docs`**, **`/redoc`** (FastAPI default).

---

## 3. Proposed / Expected Mock Trial Endpoints (REST Namespace)

These names align with a common `/api` prefix pattern. **Map to current paths** as follows where applicable:

| Proposed | Current equivalent (if any) |
|----------|------------------------------|
| `POST /api/premise/generate` | `POST /premise/generate` |
| `POST /api/opposing-counsel/generate` | `POST /opposing/challenge` |
| `POST /api/objection/analyze` | `POST /objection/evaluate` |
| `POST /api/mock-trial/turn` | **Partial:** use `POST /practice/argument` (requires prior `session_id` from `/practice/start` or premise session from `/premise/generate`) |

### Premise Generation (Proposed)

`POST /api/premise/generate`

**Request (illustrative — actual schema uses `topic`, `mode`, `randomize`, decoding fields):**

```json
{
  "category": "property_law",
  "topic": "registered_sale_deed",
  "difficulty": "medium"
}
```

**Note:** Implemented API uses string **topics** like `"title dispute"` and **modes** like `"messy real-world property disputes"` (`backend/app/schemas/premise.py`). Mapping `difficulty` → `mode` would be a **Future Enhancement**.

**Response (illustrative):**

```json
{
  "premise": "...",
  "category": "property_law",
  "topic": "...",
  "metadata": {}
}
```

**Actual response includes:** `session_id`, `topic`, `mode`, `premise`, `metadata`.

### Opposing Counsel Generation (Proposed)

`POST /api/opposing-counsel/generate`

**Request:**

```json
{
  "premise": "...",
  "user_argument": "..."
}
```

**Response:**

```json
{
  "opposing_response": "...",
  "issues_raised": [],
  "confidence": "Medium"
}
```

**Actual response:** `opposing_response`, `metadata` only (`issues_raised`, `confidence` — **Planned**).

### Objection / Weakness Detection (Proposed)

`POST /api/objection/analyze`

**Request:**

```json
{
  "premise": "...",
  "user_argument": "..."
}
```

**Response (target rich JSON — not identical to current `ObjectionEvaluateResponse`):**

```json
{
  "overall_objection": "...",
  "objection_type": "...",
  "severity": "High",
  "weaknesses": [
    {
      "point": "...",
      "why_it_matters": "...",
      "missing_element": "..."
    }
  ],
  "missing_facts_or_evidence": [],
  "possible_opposing_response": "...",
  "suggested_improvement": "...",
  "courtroom_feedback": "..."
}
```

**Current implemented response:** see `ObjectionEvaluateResponse` in Section 8.

### Full Mock Trial Turn (Proposed)

`POST /api/mock-trial/turn`

**Request:**

```json
{
  "category": "property_law",
  "premise": "...",
  "user_argument": "..."
}
```

**Response:**

```json
{
  "premise": "...",
  "opposing_response": "...",
  "objection_feedback": {},
  "dashboard_feedback": {}
}
```

**Current partial equivalent:** `POST /practice/argument` returns `opposing_response` and `objection_feedback` dict; **`dashboard_feedback`** key is **not** present as a separate aggregate — **Planned**.

---

## 4. Separate Scenario Analyzer Chatbot Endpoint

**This endpoint is separate from mock-trial endpoints.** It is **not** implemented in the scanned backend.

**Proposed:** `POST /api/scenario/analyze`

**Request:**

```json
{
  "scenario": "My landlord is forcing me to leave before the agreement ends.",
  "user_context": {
    "state": "Karnataka",
    "language": "English",
    "domain": "property_law"
  }
}
```

**Response:**

```json
{
  "scenario_summary": "...",
  "detected_domain": "Property Law",
  "issue_type": "...",
  "simplified_explanation": "...",
  "facts_identified": [],
  "missing_facts": [],
  "rights_possibly_involved": [],
  "possible_remedies": [],
  "possible_outcomes": [],
  "reasoning_trace": [],
  "consult_lawyer_warning": true,
  "warning_reason": "...",
  "confidence": "Medium",
  "source_grounding_status": "API-only MVP. Retrieval over scraped legal data is planned.",
  "disclaimer": "This is legal information for awareness and education, not legal advice."
}
```

---

## 5. Error Schema

FastAPI typically returns validation errors automatically. For application errors, routers use `HTTPException` with string `detail`.

**Suggested standardized error JSON (Future Enhancement):**

```json
{
  "error": true,
  "message": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

---

## 6. Safety Schema (Proposed for Scenario Analyzer)

```json
{
  "consult_lawyer_warning": true,
  "warning_reason": "...",
  "disclaimer": "This is legal information for awareness and education, not legal advice."
}
```

---

## 7. Dataset Schemas (JSONL)

### Chat-style training rows (found)

Premise / opposing datasets use a **`messages`** array with `system` / `user` / `assistant` roles, for example in `all_models/premise_model/property_premise_dataset_train_ready.jsonl` and `dataset_generation/property_litigation_opposing_counsel_dataset_3000_updated.jsonl`.

```json
{
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Objection training file:** `dataset_generation/train_objection.jsonl` — **To be verified** for domain alignment (spot-check showed criminal-trial JSON style; may need replacement for property objection SFT).

---

## 8. Objection Model Output Schema

### Implemented API (`ObjectionEvaluateResponse`)

| Field | Type |
|-------|------|
| `summary` | `string` |
| `objections` | `list[string]` |
| `evidentiary_gaps` | `list[string]` |
| `procedural_issues` | `list[string]` |
| `burden_of_proof_issues` | `list[string]` |
| `contradictions` | `list[string]` |
| `improvement_suggestions` | `list[string]` |
| `argument_strength_score` | `int` (0–100, clamped in parser) |
| `raw_response` | `string` |

### Target JSON (retraining goal)

See `OBJECTION_MODEL_RETRAINING_PLAN.md` Section 4.

---

## 9. Practice Session Schemas (Implemented)

- `PracticeStartRequest`: optional `topic`, `mode`, `randomize` (default `True`).  
- `PracticeArgumentRequest`: `session_id`, `user_argument`.  
- `PracticeArgumentResponse`: includes `objection_feedback` as **dict** (parser output).  
- `SessionDetailsResponse`: session metadata + `history` list.

---

## 10. Opposing & Premise Request Highlights

- `OpposingChallengeRequest`: optional `session_id`, optional `premise`, required `user_argument`, decoding knobs.  
- `PremiseGenerateRequest`: optional `topic`, `mode`, `randomize`, decoding knobs.
