# JurisCode

**JurisCode** (including **JurisCode Bharat**) is an AI-assisted platform for **legal literacy** and **courtroom-style simulation**, focused on **Indian property litigation** training. Learners work through factual scenarios, draft arguments, receive adversarial pushback, and get structured feedback—without relying on paid cloud LLM APIs for core inference.

This repository contains:

- A **FastAPI backend** that runs **local** Hugging Face **Qwen2.5-3B-Instruct** with **PEFT LoRA** adapters.
- **Training and evaluation artifacts** under **`all_models/`** (notebooks, datasets, benchmarks, exported adapters).
- An optional **slim adapter copy** under **`models/`** for simple deployment paths.

---

## Table of contents

1. [What this project does](#what-this-project-does)
2. [Architecture at a glance](#architecture-at-a-glance)
3. [Repository layout](#repository-layout)
4. [Models and data (`all_models`)](#models-and-data-all_models)
5. [Backend quick start](#backend-quick-start)
6. [Environment variables](#environment-variables)
7. [HTTP API overview](#http-api-overview)
8. [Git and Git LFS](#git-and-git-lfs)
9. [Security and what not to commit](#security-and-what-not-to-commit)
10. [Troubleshooting](#troubleshooting)
11. [Roadmap](#roadmap)
12. [Disclaimer](#disclaimer)

---

## What this project does

| Capability | Description |
|------------|-------------|
| **Premise generator** | Builds **fact-rich** Indian property-law scenarios (parties, timelines, possession, documents, title disputes, family settlements, mutation, RERA-style facts, etc.). It is for **training facts only**—not legal advice, holdings, or final conclusions. |
| **Opposing counsel** | Simulates **adversarial** oral-style challenge to the user’s argument (title, possession, procedure, evidence, burden of proof, contradictions). It must **not invent case citations**. |
| **Objection / weakness evaluator** | Surfaces objections, gaps, procedure and burden issues, contradictions, improvement ideas, and an **argument strength score (0–100)** with structured fields and a safe parser fallback. |
| **Practice flow** | Session-based flow: start session, generate premise, submit argument, receive opposing + objection feedback and history (in-memory sessions today). |

All of the above are exposed through the **backend** service. Inference is **local** (PyTorch + Transformers + PEFT); there is **no** OpenAI, Gemini, or Claude API in the inference path.

---

## Architecture at a glance

```text
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI (backend/)                     │
│  Routers: health, premise, opposing, objection, practice     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              GenerationService + SessionService              │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│   ModelManager: one Qwen2.5-3B base + switchable LoRA names   │
│   (premise / opposing / objection) via PEFT                  │
└─────────────────────────────────────────────────────────────┘
```

- **Single shared base model** in GPU float16 or CPU float32, with optional **4-bit** loading on CUDA when enabled.
- **LoRA adapters** are loaded from disk paths in `.env`. Missing adapters log a warning; the API still starts on base weights for that role.

---

## Repository layout

```text
JurisCode/
├── README.md                 # This file (project overview)
├── .gitignore                # Python, secrets, checkpoints, caches, etc.
├── .gitattributes            # Git LFS rules for large binaries
│
├── backend/                  # FastAPI application (JurisCode Bharat API)
│   ├── app/                  # main.py, routers, schemas, services, core
│   ├── requirements.txt
│   ├── run.py                # uvicorn entry: python run.py
│   ├── .env.example          # Copy to .env and edit (never commit .env)
│   └── README.md             # Detailed API docs, curl examples, SSL notes
│
├── scenario-analyzer-backend/ # Citizen Scenario Analyzer (Gemini + SQLite); Legal Clarity Score API — see README inside
├── frontend/                 # Vite/React app (includes Scenario Analyzer UI)
│
├── all_models/               # Research & training artifacts (committed)
│   ├── opposing_counsel/     # Notebooks, benchmarks, datasets, adapter exports
│   ├── premise_model/
│   ├── objection_model/
│   └── benchmark_outputs/
│
└── models/                   # Optional small “deployment” adapter copy (e.g. opposing-counsel)
```

**Naming note:** The canonical training and benchmark tree is **`all_models/`** (not `3models/`). Use **`models/`** only if you keep a trimmed export for a fixed inference path in `.env`.

**Citizen Scenario Analyzer:** The folders **`scenario-analyzer-backend/`** and **`frontend/`** implement the separate guided scenario flow (analyze → Socratic chat → optional **Legal Clarity Score**). That score is a **clarity and learning metric** only; it does not measure legal correctness or predict court outcome. Details and API steps are in **`scenario-analyzer-backend/README.md`**.

Intermediate trainer folders named **`checkpoint-*`** under `all_models/` are **ignored by Git** (see `.gitignore`). Final merged or exported adapters you care about should live in a non-checkpoint directory (as in your `qwen-…` export folders).

---

## Models and data (`all_models`)

Typical contents (varies by branch):

| Area | Examples |
|------|-----------|
| **Opposing counsel** | Training notebook, `property_opposing_counsel_benchmark.json`, dataset `.jsonl`, `run_dual_model_json_benchmark.py`, PEFT folders with `adapter_config.json`, `adapter_model.safetensors`, tokenizer sidecars |
| **Premise model** | Training notebook, premise benchmarks, `.jsonl` datasets, multiple LoRA export variants (e.g. pack true/false, v1/v2) |
| **Objection model** | Adapter + tokenizer files, README from the HF-style export |
| **Benchmarks** | JSON outputs, evaluator prompts, run summaries under `benchmark_outputs/` |

Large files (`*.safetensors`, `*.bin`, many `*.jsonl`, etc.) are tracked with **Git LFS** per `.gitattributes`. After clone, run:

```bash
git lfs install
git lfs pull
```

---

## Backend quick start

Full step-by-step (venv, pip, CORS, docs URLs, curl samples) lives in **`backend/README.md`**. Minimal path:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: set adapter paths to your local exports (see next section)
python run.py
```

Then open **http://localhost:8000/docs** (use `localhost`, not `0.0.0.0`, in the browser).

**Requirements:** Python 3.10+ recommended, PyTorch, Transformers, PEFT, FastAPI, Uvicorn. A CUDA GPU is strongly recommended; CPU works but is slow. The first run may download **Qwen2.5-3B-Instruct** from Hugging Face unless it is already cached or you point `BASE_MODEL_NAME` at a local snapshot.

---

## Environment variables

Copy **`backend/.env.example`** to **`backend/.env`** and adjust.

| Variable | Role |
|----------|------|
| `BASE_MODEL_NAME` | Hugging Face hub id or **local path** to the base causal LM (default: `Qwen/Qwen2.5-3B-Instruct`) |
| `PREMISE_ADAPTER_PATH` | Directory with PEFT `adapter_config.json` (+ weights) for premise role |
| `OPPOSING_COUNSEL_ADAPTER_PATH` | Same for opposing counsel |
| `OBJECTION_ADAPTER_PATH` | Same for objection evaluator |
| `USE_4BIT` | Optional 4-bit load on CUDA (requires compatible `bitsandbytes`) |
| `DEFAULT_*` | Default decoding hyperparameters |
| `LOCAL_FILES_ONLY`, `TRUST_REMOTE_CODE`, `HF_DISABLE_SSL_VERIFY` | Hub / SSL behaviour (see `backend/README.md`) |

Paths in `.env.example` are relative to the **`backend/`** directory (e.g. `../models/opposing-counsel` or a path under `../all_models/.../your-export-folder`).

---

## HTTP API overview

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Service metadata |
| `GET` | `/health` | Liveness, device, `models_loaded` |
| `GET` | `/models/status` | Base model, adapter flags, dtype, Hub-related flags |
| `GET` | `/premise/topics` | Curated topic list |
| `GET` | `/premise/modes` | Generation style modes |
| `POST` | `/premise/generate` | Generate premise + create session |
| `POST` | `/opposing/challenge` | Opposing counsel response |
| `POST` | `/objection/evaluate` | Structured evaluation + score |
| `POST` | `/practice/start` | Start practice session with premise |
| `POST` | `/practice/argument` | Combined opposing + objection + history update |
| `GET` | `/practice/session/{session_id}` | Session details |

CORS is enabled for common local frontends (`localhost:3000`, `localhost:5173`). See **`backend/README.md`** for curl examples and frontend integration notes.

---

## Git and Git LFS

- **Remote:** `https://github.com/prakhar811/JurisCode.git`
- **LFS:** Large weights and datasets use Git LFS (see `.gitattributes`).
- After cloning: `git lfs install` then `git lfs pull` before expecting local weight files.

---

## Security and what not to commit

Do **not** commit:

- `.env` or any file containing **API keys**, **tokens**, or **passwords**
- `serviceAccountKey.json`, private `.pem` / `.key` material
- Virtual environments (`.venv/`, `venv/`)
- `__pycache__/`, `.cache/`, `wandb/`, `runs/`, stray `logs/`
- Trainer **`checkpoint-*`** trees (ignored; keep final exports only)

**`.env.example`** is safe: it contains placeholders only. If you add real secrets to `.env` for local dev, keep `.env` gitignored (already covered in root `.gitignore`).

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Model “not loaded” / SSL errors | `TRUST_REMOTE_CODE`, `LOCAL_FILES_ONLY`, corporate CA, or `HF_DISABLE_SSL_VERIFY` (last resort)—see `backend/README.md` |
| Adapter “missing” | Path in `.env`, presence of `adapter_config.json`, optional one-level nested export folder (see `model_manager.py`) |
| Browser cannot open API | Use **http://localhost:8000/docs**, not `http://0.0.0.0:8000` |
| Huge clone | Ensure **Git LFS** is installed and `git lfs pull` completed |

---

## Roadmap

- **Frontend** for scenario setup, argument drafting, and feedback dashboards
- **Persistent sessions** (database) instead of in-memory only
- **Ontology / symbolic reasoning** layer (out of scope for current backend)
- Additional evaluation and **benchmark** automation

---

## Disclaimer

**JurisCode is an educational and simulation tool.** It does **not** provide legal advice, create an attorney–client relationship, or replace qualified counsel. Always consult a licensed advocate for real disputes and filings.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Keep secrets out of Git; use `.env` locally only.
3. Prefer small, focused commits; run the backend smoke checks described in `backend/README.md` before opening a pull request.

---

## License

Add a `LICENSE` file when you choose a license (e.g. MIT, Apache-2.0). Until then, all rights reserved unless you state otherwise in the repository settings.
