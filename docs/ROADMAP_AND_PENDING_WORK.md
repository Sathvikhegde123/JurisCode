# Roadmap and Pending Work

This roadmap is derived from **repository inspection** (May 2026) plus stated product direction (two separate module groups: **Mock Trial** vs **Scenario Analyzer**).

---

## Completed (Evidence in Repo)

| Area | Evidence |
|------|----------|
| **FastAPI backend** | `backend/app/main.py`, `backend/requirements.txt` |
| **Local inference stack** | `ModelManager`: Qwen2.5-3B-Instruct + PEFT LoRA adapters (`backend/app/core/model_manager.py`) |
| **Premise generation API** | `GET/POST /premise/*` in `backend/app/routers/premise.py` |
| **Opposing counsel API** | `POST /opposing/challenge` in `backend/app/routers/opposing.py` |
| **Objection evaluation API** | `POST /objection/evaluate` + text parsing in `backend/app/utils/text_utils.py` |
| **Practice / mock session flow** | `POST /practice/start`, `POST /practice/argument`, `GET /practice/session/{id}` |
| **In-memory sessions** | `backend/app/services/session_service.py` |
| **Training artifacts** | `all_models/` (adapters, notebooks, benchmarks, JSONL datasets) |
| **Dataset generation scripts** | `dataset_generation/*.py` (uses **Gemini** API for synthetic JSONL—**not** runtime inference) |
| **Project README** | Root `README.md` (accurate high-level API table) |

---

## In Progress / Partially Completed

| Item | Component | Notes |
|------|-----------|-------|
| **Objection model quality & output shape** | Objection / Weakness Detector | Model runs; response is **free text** parsed into lists + score. Target **strict JSON** schema is a **Future Enhancement / retraining goal** (see `OBJECTION_MODEL_RETRAINING_PLAN.md`). |
| **“Learning Dashboard” as product** | Frontend | Backend returns `objection_feedback` and `argument_strength_score`; **no dedicated dashboard UI** found in repo. |
| **Documentation hygiene** | Docs | `backend/README.md` appears **corrupted / merged** with other content at time of scan—**To be verified** and repaired outside `docs/` if desired. |
| **Scenario Analyzer** | Citizen module | **Not implemented** in backend per scan; design in `SCENARIO_ANALYZER_CHATBOT.md`. |

---

## Planned

| Task | Component | Status |
|------|-----------|--------|
| **Scenario Analyzer** route + external API client + Pydantic schemas | Backend | Planned |
| **Dedicated frontend** (mock trial + analyzer entry) | Frontend | Planned (explicitly in root `README.md` roadmap) |
| **Persistent sessions** (DB) | Backend | Planned |
| **Automated benchmark CI** | MLOps | Partially present as scripts under `all_models/`; **To be verified** for CI wiring |

---

## Future Enhancements

- **RAG** over legal knowledge base  
- **JSON rule matcher** for deterministic checks  
- **Prolog/Datalog** or similar symbolic layer  
- **Multilingual** and **voice** interfaces  
- **Ontology** / richer legal metadata  
- **Admin panel** for curating scraper outputs  

---

## Priority Table

| Priority | Task | Component | Status | Reason |
|----------|------|-----------|--------|--------|
| P0 | Keep mock-trial APIs stable (`/premise`, `/opposing`, `/objection`, `/practice`) | Backend | **Completed** | Core training loop exists. |
| P0 | Clarify two product surfaces in UI when frontend exists | Frontend | **Planned** | Avoid mixing citizen chatbot with student mock trial. |
| P1 | Objection model **retrain / align** to property-law JSON feedback | ML | **In Progress** | Stakeholder direction; current parser is heuristic on prose. |
| P1 | Implement **Scenario Analyzer** backend + env-based API keys | Backend | **Planned** | Citizen MVP path. |
| P2 | Legal KB folder + normalization pipeline | Data / RAG prep | **Planned** | `property_rights/` tree **not found** in repo scan. |
| P2 | Persistent session store | Backend | **Planned** | In-memory only today. |
| P3 | Vector DB + RAG | Architecture | **Future Enhancement** | Not in codebase. |
| P3 | Rule engine / Prolog | Architecture | **Future Enhancement** | Not in codebase. |
