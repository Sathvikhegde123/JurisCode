# Objection Model Retraining Plan

## 1. Why Retraining Is Needed

The objection / weakness role must give **property-law-specific**, **training-useful** feedback (missing facts, burden issues, procedure, evidence gaps) rather than generic critique.

**Current implementation (repo):**

- `GenerationService.generate_objection()` prompts the model for summary, objections, gaps, score, etc. (`backend/app/services/generation_service.py`).  
- `parse_objection_evaluation()` performs **best-effort parsing** of **plain text** into buckets + score (`backend/app/utils/text_utils.py`).  
- API response schema is `ObjectionEvaluateResponse` with **lists and integer score**, not the richer nested JSON described as a target in stakeholder docs.

**Gap:** Reliability and consistency of fields depend on model prose layout. A **smaller, high-quality property-law dataset** with **assistant outputs as valid JSON** should improve parseability and legal focus.

**Dataset note (To be verified):** The first line of `dataset_generation/train_objection.jsonl` (spot-check) references **criminal trial / JSON ruling** style content, which may **not** align with **Indian property litigation** training. Curators should confirm whether this file is legacy or must be replaced for property objection SFT.

---

## 2. Role in Mock Trial Workflow

User argument is processed by:

1. **Opposing Counsel Model** — adversarial challenge (`/opposing/challenge` or within `/practice/argument`).  
2. **Objection / Weakness Detector** — evaluator feedback (`/objection/evaluate` or same practice call).

Both receive **premise + user_argument** when session context exists.

**The Citizen Scenario Analyzer is not part of this workflow.**

---

## 3. Expected Input (Logical)

```json
{
  "premise": "...",
  "user_argument": "..."
}
```

(Also supported today: optional `session_id` to pull premise from session.)

---

## 4. Expected Output (Target JSON for Training / Future API)

```json
{
  "overall_objection": "...",
  "objection_type": "...",
  "severity": "Low",
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

**Current API shape (implemented):** `summary`, `objections`, `evidentiary_gaps`, `procedural_issues`, `burden_of_proof_issues`, `contradictions`, `improvement_suggestions`, `argument_strength_score`, `raw_response` — see `backend/app/schemas/objection.py`.

---

## 5. Dataset Categories (Property Litigation Coverage)

Use as a **checklist** for balanced training data:

1. Registered sale deed dispute  
2. Vendor title dispute  
3. Mutation vs title  
4. Possession dispute  
5. Oral partition  
6. Ancestral property sale  
7. Co-sharer dispute  
8. Gift deed challenge  
9. Forged sale deed  
10. Agreement to sell / specific performance  
11. Power of attorney sale  
12. Will / succession dispute  
13. Tenant eviction  
14. Encroachment  
15. Boundary dispute  
16. Easement rights  
17. Builder delay  
18. Injunction suit  
19. Adverse possession claim  
20. Limitation issue  

---

## 6. Validation Criteria

Dataset rows should pass checks for:

- Valid **JSONL** (one JSON object per line)  
- Chat **`messages`** structure where used  
- Assistant segment = **valid JSON** if JSON-only training is required  
- Required keys present (per chosen schema)  
- `severity` in allowed set (`Low` / `Medium` / `High`)  
- Non-empty `weaknesses` where appropriate  
- **No fake citations** (enforce in instructions + manual QA)  
- Reasonable **category distribution** across topics  

---

## 7. Benchmark Plan (Manual or Scripted)

Run 8–10 fixed cases post-training, for example:

| # | Scenario theme |
|---|----------------|
| 1 | Sale deed vs oral partition |
| 2 | Mutation vs title |
| 3 | Tenant eviction without notice |
| 4 | Forged sale deed |
| 5 | Specific performance without readiness/willingness |
| 6 | Injunction without possession |
| 7 | Adverse possession vague claim |
| 8 | Will dispute |
| 9 | Builder delay |
| 10 | Boundary dispute |

**Repository:** Opposing counsel benchmarking exists (`all_models/opposing_counsel/run_dual_model_json_benchmark.py`, `property_opposing_counsel_benchmark.json`). **Dedicated objection benchmark suite:** To be verified / created.

**Quantitative scores:** To be updated after final benchmark validation.

---

## 8. Integration Plan

1. Train or fine-tune objection LoRA with JSON-consistent assistant outputs on property scenarios.  
2. Export adapter; point `OBJECTION_ADAPTER_PATH` in `backend/.env`.  
3. Optionally replace `parse_objection_evaluation` with **strict JSON parse** once model compliance is high enough.  
4. Map JSON fields to API response (either extend `ObjectionEvaluateResponse` or version `/objection/evaluate` to v2).  
5. Surface results in the **Learning Dashboard** UI when the frontend exists; until then, clients consume JSON from `/objection/evaluate` or `/practice/argument`.
