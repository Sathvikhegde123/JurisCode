# Component-Wise Execution Status

**Last aligned to repository scan:** May 2026.

---

## Component 1: Premise Generator Model

| Field | Detail |
|-------|--------|
| **Purpose** | Generate **realistic Indian property litigation** factual scenarios for training. |
| **Role in workflow** | First model step after topic/mode selection. |
| **Input** | `topic` (curated string), `mode` (style string), optional decoding parameters; or `randomize`. |
| **Output** | Single string premise; API also returns `session_id` for downstream use. |
| **Files / folders** | `backend/app/routers/premise.py`, `schemas/premise.py`, `services/generation_service.py`; data in `all_models/premise_model/`, `dataset_generation/`; notebooks in `all_models/premise_model/`, `ipynbFiles/`. |
| **Status** | **Completed** (backend + weights + datasets). |
| **Completed work** | FastAPI endpoints `/premise/topics`, `/premise/modes`, `/premise/generate`; LoRA inference integration. |
| **Pending work** | Optional UI for topic/mode; mapping to any future “difficulty” knob. |
| **Next step** | Frontend wiring + UX testing with real students. |

---

## Component 2: Opposing Counsel Model

| Field | Detail |
|-------|--------|
| **Purpose** | Simulate **adversarial opposing counsel** responses. |
| **Role in workflow** | Challenges the user’s argument against the premise. |
| **Input** | `user_argument`, optional `premise` or `session_id`. |
| **Output** | Adversarial natural-language response. |
| **Files / folders** | `backend/app/routers/opposing.py`, `schemas/opposing.py`, `generation_service.py`; `all_models/opposing_counsel/`; `dataset_generation/generate_dataset.py`; benchmarks `run_dual_model_json_benchmark.py`. |
| **Status** | **Completed**. |
| **Completed work** | `/opposing/challenge`; dual-adapter benchmark tooling; large JSONL dataset. |
| **Pending work** | Optional structured `issues_raised` list in API response. |
| **Next step** | Extend response schema if frontend needs bullet issues without client-side NLP. |

---

## Component 3: Objection / Weakness Detector

| Field | Detail |
|-------|--------|
| **Purpose** | Surface weaknesses, procedural/evidence/burden issues, contradictions, improvements, and a **0–100** strength score. |
| **Role in workflow** | Parallel critique path alongside opposing counsel. |
| **Input** | `user_argument`, optional premise/session. |
| **Output (implemented)** | Parsed structure: `summary`, list fields, `argument_strength_score`, `raw_response`. |
| **Output (target after retrain)** | Strict JSON with nested `weaknesses`, `severity`, etc. — see `OBJECTION_MODEL_RETRAINING_PLAN.md`. |
| **Analyzes (intent)** | Legal weaknesses; missing facts; missing evidence; procedural defects; contradiction; burden of proof; statutory gaps; relief mismatch; improvement suggestions. |
| **Files / folders** | `backend/app/routers/objection.py`, `schemas/objection.py`, `utils/text_utils.py`; `all_models/objection_model/`; `dataset_generation/train_objection.jsonl`. |
| **Status** | **In progress / being retrained** (per project direction); **functionally Partially completed** in API. |
| **Completed work** | `/objection/evaluate`; integration in `/practice/argument`; heuristic parser. |
| **Pending work** | Property-specific JSONL curation; model fine-tune; optional strict JSON parsing. |
| **Next step** | Build and validate small high-quality property objection dataset; re-export adapter. |

**Expected output schema (retraining target):**

```json
{
  "overall_objection": "...",
  "objection_type": "...",
  "severity": "Low/Medium/High",
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

---

## Component 4: Mock Trial Workflow

**Canonical workflow (only this chain for mock trial):**

1. User opens platform  
2. Selects legal domain or topic  
3. **Premise Generator Model** → realistic property litigation scenario  
4. User writes legal argument  
5. **Opposing Counsel Model** → adversarial challenge  
6. **Objection / Weakness Detector** → structured critique  
7. **Learning Dashboard** → score, feedback, improvements, retry  

**Explicit exclusion:** The **Citizen Scenario Analyzer chatbot** is **NOT** part of this workflow.

**Backend mapping:** `/practice/start` → `/practice/argument` implements premise + dual generation + history; alternatively compose `/premise/generate` + `/opposing/challenge` + `/objection/evaluate`.

---

## Component 5: Learning Dashboard

| Field | Detail |
|-------|--------|
| **Purpose** | Present **score**, narrative **feedback**, **improvements**, and support **retry** loops. |
| **Expected outputs** | Score from objection parser; opposing text; history of attempts. |
| **Status** | **Partially completed** — data exists via API (`argument_strength_score`, `objection_feedback`, `history`); **no** dedicated dashboard frontend found in repo. |
| **Next step** | Build UI consuming `/practice/session/{id}` and `/objection/evaluate`. |

---

## Component 6: Legal Scraper / Legal Knowledge Base

| Field | Detail |
|-------|--------|
| **Purpose** | Organize Indian legal source material for future retrieval and grounding. |
| **Data folders (target)** | `acts/`, `articles/`, `cases/`, `constitution/`, `sections/` under `property_rights/` |
| **Completed** | **To be verified** — folder tree **not** found in repository scan. |
| **Pending** | Scraper deployment, normalization, deduplication, citation metadata. |
| **Future RAG use** | Vector index over normalized chunks feeding Scenario Analyzer or student research modes. |

---

## Component 7: Citizen Scenario Analyzer Chatbot

| Field | Detail |
|-------|--------|
| **Purpose** | **Citizen-facing legal literacy** for real-life problems in plain language. |
| **Target user** | Ordinary citizen (non-lawyer). |
| **Input** | Natural-language scenario (+ optional `user_context`). |
| **Output** | Scenario summary; detected domain; issue type; simplified explanation; facts identified; missing facts; rights possibly involved; possible remedies; possible outcomes; reasoning trace; lawyer warning; disclaimer; confidence. |
| **Current MVP** | **API-based** external LLM (**Planned** in backend code at scan). |
| **Future** | RAG, JSON rules, Prolog/Datalog — **Future Enhancement**. |
| **Independence** | **Not** connected to premise/opposing/objection/mock-trial routes. |

---

## Component 8: Future RAG Layer

| Status | **Future Enhancement** |
|--------|------------------------|
| **Notes** | No vector DB or retriever code observed in backend. |

---

## Component 9: Future Rule Engine / Prolog-Datalog

| Status | **Future Enhancement** |
|--------|------------------------|
| **Notes** | No rule engine or logic programming integration in repo scan. |

---

## Final Status Table

| Component | Status | Priority | Completed | Pending | Next step |
|-----------|--------|----------|-----------|---------|-----------|
| Premise Generator | **Completed** | P0 | API + LoRA + datasets | UI | Frontend |
| Opposing Counsel | **Completed** | P0 | API + LoRA + benchmarks | Structured issues in API | Schema optional fields |
| Objection Detector | **In progress** | P1 | API + parser | Retrain / JSON outputs | Dataset + adapter |
| Mock Trial Workflow | **Partially completed** | P0 | Backend practice flow | Full UI dashboard | Frontend |
| Learning Dashboard | **Planned / Partial** | P1 | API fields | Dedicated UI | Design + implement |
| Legal KB / Scraper | **Planned** | P2 | — | Corpus on disk | Scrape + normalize |
| Scenario Analyzer | **Planned** | P1 | Design docs | Backend route + API client | Implement `/scenario` |
| RAG Layer | **Future** | P3 | — | All | After KB exists |
| Rules / Prolog | **Future** | P3 | — | All | Research prototype |
