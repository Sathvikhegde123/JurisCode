# JurisCode

AI-powered legal literacy and courtroom simulation system.

## Current status

- **Backend:** FastAPI service under `backend/` (local Hugging Face + PEFT inference).
- **Models:** **Opposing Counsel** LoRA adapter lives in `models/opposing-counsel/`.
- **Premise** and **objection** adapters will be added under `models/` in a later release.

## Repository layout

```
JurisCode/
├── backend/                 # API, services, routers
├── models/
│   └── opposing-counsel/    # PEFT adapter + tokenizer sidecar files for inference
├── README.md
├── .gitignore
└── .gitattributes           # Git LFS pointers for large weight files
```

## Frontend

A web frontend is planned; it is not in this repository yet.

## Quick start (backend)

See `backend/README.md` for environment setup, `copy .env.example .env`, and `python run.py`.

Point `OPPOSING_COUNSEL_ADAPTER_PATH` at the repo-level adapter (default in `.env.example`: `../models/opposing-counsel`).

## Legal notice

This project is for education and simulation only; it does not provide legal advice.
