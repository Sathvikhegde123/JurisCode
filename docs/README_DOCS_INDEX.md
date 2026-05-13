# JurisCode Documentation Index

This folder contains the professional documentation set for the **JurisCode** repository. It reflects a **May 2026** scan of the codebase unless individual files state otherwise.

| File | Purpose |
|------|---------|
| [MASTER_DOCUMENTATION.md](./MASTER_DOCUMENTATION.md) | Complete project documentation (overview, problem statement, modules, methodology, limitations). |
| [COMPONENT_WISE_EXECUTION.md](./COMPONENT_WISE_EXECUTION.md) | Per-component execution status, inputs/outputs, and next steps. |
| [SYSTEM_ARCHITECTURE_AND_WORKFLOW.md](./SYSTEM_ARCHITECTURE_AND_WORKFLOW.md) | Architecture narratives and Mermaid diagrams (mock trial vs Scenario Analyzer). |
| [BACKEND_SCHEMAS_AND_ENDPOINTS.md](./BACKEND_SCHEMAS_AND_ENDPOINTS.md) | Implemented FastAPI routes, Pydantic schemas, proposed REST shapes, and error/safety schemas. |
| [MODEL_DETAILS_AND_TRAINING.md](./MODEL_DETAILS_AND_TRAINING.md) | Model roles, datasets, notebooks, benchmarks, and training-related tooling. |
| [LEGAL_KNOWLEDGE_BASE_AND_SCRAPER.md](./LEGAL_KNOWLEDGE_BASE_AND_SCRAPER.md) | Intended legal KB layout, JSON shapes, and future RAG use (**scraper output folders not found in repo scan**). |
| [OBJECTION_MODEL_RETRAINING_PLAN.md](./OBJECTION_MODEL_RETRAINING_PLAN.md) | Plan to retrain/correct the objection model and validate structured outputs. |
| [SCENARIO_ANALYZER_CHATBOT.md](./SCENARIO_ANALYZER_CHATBOT.md) | Separate citizen-facing chatbot design (API-based MVP; **not** wired in backend as of scan). |
| [ROADMAP_AND_PENDING_WORK.md](./ROADMAP_AND_PENDING_WORK.md) | Completed, in-progress, planned, and future work with a priority table. |

**Important:** The **Mock Trial / Legal Training** stack and the **Citizen Scenario Analyzer** are **two separate module groups**. Do not document the Scenario Analyzer as part of the mock-trial pipeline.
