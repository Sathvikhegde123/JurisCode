# JurisCode Bharat — Backend

AI-Based Legal Reasoning and Trial Practice Platform backend for Indian property litigation education.

This service exposes FastAPI endpoints that run **entirely on local hardware** using Hugging Face Transformers with a shared **Qwen2.5-3B-Instruct** base checkpoint and **optional PEFT LoRA** adapters. No OpenAI, Gemini, Claude, or other hosted LLM APIs are used.

---

## 1. Overview

Three AI roles share one base model; adapters are switched with PEFT:

| Component | Role |
|-----------|------|
| **Premise Generator** | Produces realistic Indian property-law **fact patterns** for training: parties, timelines, possession, documents, title disputes, family conflicts, mutation, sale deeds, partition, adverse possession, RERA-related facts, etc. It does **not** give legal advice, final answers, or normative legal analysis—only factual scenarios. |
| **Opposing Counsel** | Responds as adversarial Indian courtroom counsel: title and possession analysis, evidentiary scrutiny, civil procedure, burden of proof, contradictions, and fact-specific challenges—**without inventing case citations**. |
| **Objection / Weakness Evaluator** | Reviews the user’s argument for objections, gaps, procedure, burden issues, contradictions, improvements, and a **0–100 strength score**, with structured fields plus parser fallback when the model returns prose. |

---

## 2. Folder Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── model_manager.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── premise.py
│   │   ├── opposing.py
│   │   ├── objection.py
│   │   └── practice.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── premise.py
│   │   ├── opposing.py
│   │   ├── objection.py
│   │   └── practice.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── generation_service.py
│   │   └── session_service.py
│   └── utils/
│       ├── __init__.py
│       └── text_utils.py
├── models/
│   ├── premise_generator_lora/
│   ├── opposing_counsel_lora/
│   └── objection_evaluator_lora/
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── run.py
```

> **Note:** `.gitignore` excludes `models/` and weight files so checkpoints and LoRA weights are not committed. Create the adapter directories locally and place your trained adapters there (see below).

---

## 3. Environment Setup

```bash
cd backend
python -m venv venv
```

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

**macOS / Linux:**

```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` if you need custom paths, 4-bit loading, or generation defaults.

---

## 4. Placing LoRA Adapters

After training, place each LoRA export (must include `adapter_config.json` and adapter weights) under:

```
backend/
└── models/
    ├── premise_generator_lora/
    ├── opposing_counsel_lora/
    └── objection_evaluator_lora/
```

Paths are configurable via `.env` (`PREMISE_ADAPTER_PATH`, `OPPOSING_COUNSEL_ADAPTER_PATH`, `OBJECTION_ADAPTER_PATH`).

You may keep a **single extra subfolder** under each role directory (for example `models/opposing_counsel_lora/qwen-opposing-counsel-v1-.../adapter_config.json`). On startup the backend resolves **one level deep** and prefers a real run folder over `checkpoint-*` when both exist.

If a folder is missing or incomplete, the API **still starts**: the server logs a warning and uses the **base model** for that role until a valid adapter is provided.

---

## Hugging Face Hub, SSL, and offline loading

The base model is loaded with Hugging Face `transformers`. After weights are read from the cache, the library can still issue **HTTPS** calls (for example when `trust_remote_code=true` pulls optional remote files). On networks with **corporate TLS inspection** or a **broken certificate chain**, you may see `SSL: CERTIFICATE_VERIFY_FAILED` and the API will start in **degraded mode** (no model).

Configure these in `.env`:

| Variable | Purpose |
|----------|---------|
| `TRUST_REMOTE_CODE` | Default `true`. Set to `false` if you use a recent `transformers` build that loads Qwen2.5 without remote code—this often **avoids extra Hub requests** after the snapshot is cached. |
| `LOCAL_FILES_ONLY` | Set to `true` to forbid Hub downloads; the full model must already be in the HF cache (or use a local `BASE_MODEL_NAME` path). |
| `HF_DISABLE_SSL_VERIFY` | Set to `true` only as a **last resort** to disable TLS verification in Python (insecure). Prefer fixing the corporate root CA (`SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`) instead. |

After changing `.env`, restart `python run.py`. Use `GET /models/status` to confirm `loaded: true` and to see the effective `local_files_only`, `trust_remote_code`, and `hf_disable_ssl_verify` flags.

---

## 5. Run Backend

From `backend/`:

```bash
python run.py
```

| Resource | URL |
|----------|-----|
| API root | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health | http://localhost:8000/health |

Use **`localhost` or `127.0.0.1`** in the browser. The address **`0.0.0.0`** is only for binding the server to all interfaces; most browsers show `ERR_ADDRESS_INVALID` if you open `http://0.0.0.0:8000`.

---

## 6. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness and device summary |
| `GET` | `/models/status` | Base model, adapter flags, dtype, current adapter, Hub settings |
| `GET` | `/premise/topics` | Fixed list of 20 litigation topics |
| `GET` | `/premise/modes` | Generation style modes |
| `POST` | `/premise/generate` | Generate premise + create session |
| `POST` | `/opposing/challenge` | Adversarial counsel reply |
| `POST` | `/objection/evaluate` | Structured evaluation + score |
| `POST` | `/practice/start` | Start session with premise |
| `POST` | `/practice/argument` | Combined opposing + objection + history |
| `GET` | `/practice/session/{session_id}` | Session details and history |

---

## 7. Example `curl` Requests

**Health**

```bash
curl http://localhost:8000/health
```

**Model status**

```bash
curl http://localhost:8000/models/status
```

**Premise generation**

```bash
curl -X POST http://localhost:8000/premise/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"topic\": \"title dispute\", \"mode\": \"messy real-world property disputes\", \"randomize\": false}"
```

*(Use `\` instead of `^` for line continuation on macOS/Linux.)*

**Opposing counsel**

```bash
curl -X POST http://localhost:8000/opposing/challenge ^
  -H "Content-Type: application/json" ^
  -d "{\"user_argument\": \"The sale deed is registered and therefore title is perfect.\", \"premise\": \"Two brothers dispute ancestral land in Pune.\"}"
```

**Objection evaluation**

```bash
curl -X POST http://localhost:8000/objection/evaluate ^
  -H "Content-Type: application/json" ^
  -d "{\"user_argument\": \"Mutation records are missing but possession is 20 years.\", \"premise\": \"Revenue record dispute in rural Maharashtra.\"}"
```

**Practice start**

```bash
curl -X POST http://localhost:8000/practice/start ^
  -H "Content-Type: application/json" ^
  -d "{\"randomize\": true}"
```

**Practice argument** (replace `SESSION_ID`)

```bash
curl -X POST http://localhost:8000/practice/argument ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\": \"SESSION_ID\", \"user_argument\": \"I rely on adverse possession and long possession.\"}"
```

**Session details**

```bash
curl http://localhost:8000/practice/session/SESSION_ID
```

---

## 8. Frontend Integration Flow

**Page 1 — Scenario setup**

1. `GET /premise/topics` and `GET /premise/modes` to populate UI.
2. `POST /premise/generate` or `POST /practice/start` to obtain `session_id`, `topic`, `mode`, and `premise`.

**Page 2 — Argument drafting**

1. Show the returned premise.
2. Collect the learner’s argument.
3. Either call `POST /opposing/challenge` and `POST /objection/evaluate` separately (pass `session_id` to reuse the stored premise), or call `POST /practice/argument` for a single combined step.

**Page 3 — Feedback dashboard**

Display:

- Opposing counsel narrative
- Parsed objection payload: `summary`, `objections`, `evidentiary_gaps`, `procedural_issues`, `burden_of_proof_issues`, `contradictions`, `improvement_suggestions`, `argument_strength_score`, and `raw_response` for transparency

---

## 9. GPU / CPU Notes

- **CUDA is strongly recommended** for acceptable latency.
- **CPU fallback** is supported (`device` falls back to CPU); first load and generation will be slow.
- `USE_4BIT=true` only applies when **CUDA** is available **and** `bitsandbytes` works on your platform; otherwise the server logs a warning and loads without 4-bit quantization.
- Qwen2.5-3B in float16 often needs on the order of **6–7 GB VRAM** (varies by batching and framework version).
- 4-bit loading can significantly reduce VRAM usage when enabled.

---

## 10. Future Scope (not implemented here)

- Ontology / Prolog reasoning layer  
- Citizen scenario analyzer / rights module  
- Voice mock trial (speech-to-text / text-to-speech)  
- Gamification and scoring dashboards  
- Persistent database-backed sessions (today: **in-memory** only; replace with SQLite/PostgreSQL when needed)

---

## Sessions

Sessions are stored **in memory** in `SessionService`. Restarting the process clears them. For production, plug in a database using the same service boundary.

---

## License / disclaimer

This software is for **education and simulation** only. It does not provide legal advice. Always consult a qualified advocate for real matters.
