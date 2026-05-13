# JurisCode

AI-powered legal literacy and courtroom simulation system.

## Current status

- **Backend:** FastAPI service under `backend/` (local Hugging Face + PEFT inference).
- **Models & artifacts:** Trained LoRA adapters, datasets, benchmarks, and training notebooks live under **`all_models/`** (opposing counsel, premise generator, objection model). A slim copy of the opposing adapter for deployment also exists under `models/opposing-counsel/` if you use that path in `.env`.

## Repository layout

```
JurisCode/
├── backend/                 # FastAPI app, routers, services
├── models/                  # Optional slim inference copy (e.g. opposing-counsel)
├── all_models/              # Full artifacts: adapters, tokenizers, .ipynb, benchmarks, .json/.jsonl
│   ├── opposing_counsel/
│   ├── premise_model/
│   ├── objection_model/
│   └── benchmark_outputs/
├── README.md
├── .gitignore               # Ignores checkpoints, .env, venv, cache, wandb, etc.
└── .gitattributes           # Git LFS for weights and large data files
```

Intermediate **`checkpoint-*`** directories under `all_models/` are **not** committed (see `.gitignore`).

## Frontend

A web frontend is planned; it is not in this repository yet.

## Quick start (backend)

See `backend/README.md` for environment setup, `copy .env.example .env`, and `python run.py`.

Point adapter paths in `.env` at either `../models/...` or a folder under `../all_models/...` depending on which export you use.

## Legal notice

This project is for education and simulation only; it does not provide legal advice.
