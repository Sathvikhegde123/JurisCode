# Model Details and Training Documentation

## 1. Overview

JurisCode’s **mock trial / legal training** stack uses a **single shared causal LM** — default **`Qwen/Qwen2.5-3B-Instruct`** — with **three PEFT LoRA adapters** switched at inference time:

| Role | Adapter name in `ModelManager` | Service entrypoint |
|------|--------------------------------|--------------------|
| Premise Generator | `premise` | `GenerationService.generate_premise` |
| Opposing Counsel | `opposing` | `GenerationService.generate_opposing` |
| Objection / Weakness Detector | `objection` | `GenerationService.generate_objection` |

**Citizen Scenario Analyzer:** **External API** for MVP (by product direction); **not** part of local LoRA switching — **not implemented** in backend at repo scan.

---

## 2. Premise Generator Model

| Aspect | Detail |
|--------|--------|
| **Purpose** | Fact-rich **Indian property-law** dispute scenarios for training (no legal advice in premise text). |
| **Input (API)** | `topic` (from curated list) + `mode` (style) + sampling params (`PremiseGenerateRequest`). |
| **Output** | Single string `premise`. |
| **Model folders** | `all_models/premise_model/` (multiple exports, e.g. `qwen-property-premise-generator-*`, `checkpoint-*`); optional slim copy under `models/` per project layout. |
| **Datasets** | `property_premise_dataset.jsonl`, `property_premise_dataset_train_ready.jsonl` under `all_models/premise_model/` and `dataset_generation/`. |
| **Training artifacts** | `all_models/premise_model/qwen25_premise_generator_lora_training.ipynb`; duplicate under `ipynbFiles/`. |
| **Adapter README** | TRL **1.4.0**, SFT, LoRA tags in export `README.md` files. |
| **Benchmarks** | `all_models/premise_model/run_dual_premise_model_json_benchmark.py`, `property_premise_benchmark.json` (referenced in script). |
| **Status** | **Completed** (inference + data + training artifacts in repo). |
| **Pending work** | Topic/difficulty taxonomy alignment with any future UI; ongoing quality eval. |

---

## 3. Opposing Counsel Model

| Aspect | Detail |
|--------|--------|
| **Purpose** | Adversarial challenge to student arguments; title/possession/procedure/evidence/burden focus; **no invented case citations** (prompt instruction). |
| **Input (API)** | `user_argument` + optional `premise` / `session_id`. |
| **Output** | String `opposing_response`. |
| **Model folders** | `all_models/opposing_counsel/` (e.g. `qwen-opposing-counsel-v1-r32-512-packtrue/false`); `models/opposing-counsel/` deployment copy. |
| **Datasets** | `property_litigation_opposing_counsel_dataset_3000_updated.jsonl` in `dataset_generation/` and `all_models/opposing_counsel/`. |
| **Dataset generation** | `dataset_generation/generate_dataset.py` uses **`google.genai`** with **`GEMINI_API_KEY`** and model **`gemini-2.5-flash`** — for **data synthesis**, not backend inference. |
| **Training artifacts** | `all_models/opposing_counsel/current_model_training_file_opposing_counselling.ipynb`; copies under `all_models/` root and `ipynbFiles/`. |
| **Benchmarks** | `run_dual_model_json_benchmark.py`, `property_opposing_counsel_benchmark.json`, outputs under `all_models/benchmark_outputs/`. |
| **Status** | **Completed** (core path). |
| **Pending work** | Automated CI evaluation; optional structured `issues_raised` in API. |

---

## 4. Objection / Weakness Detector Model

| Aspect | Detail |
|--------|--------|
| **Purpose** | Courtroom-training feedback: objections, gaps, burden issues, contradictions, improvements, strength score. |
| **Input** | Same pattern as opposing (`user_argument`, optional premise/session). |
| **Output** | Raw text → **`parse_objection_evaluation`** → structured dict for API (`text_utils.py`). |
| **Model folder** | `all_models/objection_model/` (e.g. `checkpoint-1900` export). |
| **Datasets** | `dataset_generation/train_objection.jsonl`, `test_objection.jsonl` — **To be verified** for **property-law** alignment (see objection retraining plan). |
| **Status** | **Partially completed / In progress** — works end-to-end but **retraining** for JSON-first property feedback is planned. |
| **Pending work** | High-quality property JSONL; stricter JSON output; possible parser swap to `json.loads`. |

---

## 5. Dataset Format

Standard chat JSONL:

```json
{
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Premise training data matches this pattern in `property_premise_dataset_train_ready.jsonl`.

---

## 6. Training Tools (From Repo Evidence)

### Currently used (evidence)

| Tool | Evidence |
|------|----------|
| **Python** | Entire backend + scripts |
| **PyTorch** | `requirements.txt`, `model_manager.py` |
| **Transformers** | `AutoModelForCausalLM`, `AutoTokenizer` |
| **PEFT / LoRA** | `PeftModel`, `load_adapter`, adapter folders |
| **BitsAndBytes** | Optional **4-bit** load on CUDA (`BitsAndBytesConfig`) |
| **FastAPI / Uvicorn** | Backend stack |
| **Jupyter** | `.ipynb` under `all_models/`, `ipynbFiles/` |
| **JSON / JSONL** | Datasets and benchmark IO |
| **Google Gemini API** | `dataset_generation/generate_dataset.py`, `premise_generation.py` for synthetic data |
| **TRL (training)** | Adapter `README.md` tags in `all_models/premise_model/` exports |

### Not evidenced in backend `requirements.txt`

| Tool | Note |
|------|------|
| **Unsloth** | Not listed in `backend/requirements.txt`; **To be verified** in notebooks only. |
| **QLoRA** as training label | Inference supports 4-bit loading; training recipe = **To be verified** from notebooks. |

---

## 7. Benchmarking

| Artifact | Location |
|----------|----------|
| Opposing dual benchmark script | `all_models/opposing_counsel/run_dual_model_json_benchmark.py` |
| Premise dual benchmark script | `all_models/premise_model/run_dual_premise_model_json_benchmark.py` |
| Sample outputs | `all_models/benchmark_outputs/packtrue_outputs.json`, `packfalse_outputs.json` |

**Consolidated benchmark scores in CI:** To be updated after final benchmark validation.

---

## 8. Runtime Inference Notes

- **Local-only** for mock-trial models: root `README.md` states no OpenAI/Gemini/Claude in inference path.  
- **CUDA** strongly recommended; CPU fallback supported with warnings.  
- **Adapter resolution** supports one-level nested `checkpoint-*` folders (`model_manager.py`).
