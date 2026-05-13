# Citizen Scenario Analyzer Chatbot

## 1. What It Is

The **Citizen Scenario Analyzer** is a **separate chatbot-style legal literacy component**. It is **not** part of:

- Premise Generator  
- Opposing Counsel simulator  
- Objection / Weakness Detector  
- Mock-trial practice session APIs (`/practice/*`)

Those components form the **student / legal training** path. The Scenario Analyzer is a **citizen-facing** path for **real-life problems** described in plain language.

**Repository scan (May 2026):** No FastAPI router, service, or schema for a Scenario Analyzer was found under `backend/app/`. Treat backend wiring as **Planned** until code exists. Product direction described below matches stakeholder intent.

---

## 2. Purpose

Help ordinary citizens understand **real-life** legal situations in **simple, educational** language—without replacing a lawyer.

**Example input:**  
“My landlord is forcing me to leave before the agreement ends.”

---

## 3. Current MVP Design (Intended)

Per project direction:

| Aspect | Status |
|--------|--------|
| API-based chatbot using an **external LLM API** | **Planned** (not found in `backend/` as of scan) |
| Backend input validation | **Planned** |
| Structured JSON response | **Planned** |
| Safety warning / disclaimer | **Planned** |
| Frontend chatbot or “cards” UI | **Planned** (no React/Vue app present in repository root scan) |

**Explicitly not claimed for the current MVP:**

- **RAG** over scraped statutes or cases  
- **JSON rule engine**  
- **Prolog / Datalog** reasoning  

Those are **Future Enhancement** only unless implemented in code.

---

## 4. Expected Output (Target Schema)

1. Scenario summary  
2. Detected domain  
3. Issue type  
4. Simplified explanation  
5. Facts identified  
6. Missing facts / questions  
7. Rights possibly involved  
8. Possible remedies  
9. Possible outcomes  
10. Reasoning trace  
11. Consult-lawyer warning (+ reason when true)  
12. Confidence  
13. Disclaimer  

---

## 5. API Endpoint (Proposed)

**Separate from mock-trial endpoints.** A clean REST layout might expose:

`POST /api/scenario/analyze`

**Request (example):**

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

**Response (example):**

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

**Note:** The live backend today mounts routes such as `/premise/generate` **without** an `/api` prefix (see `backend/app/main.py`). A future Scenario Analyzer route may follow the same style (e.g. `/scenario/analyze`) or sit behind a gateway that adds `/api`.

---

## 6. Suggested System Prompt (For External API)

> You are a legal literacy assistant for Indian citizens. Your role is to explain legal situations in simple educational language. You must not provide final legal advice. You must not guarantee outcomes. You must not invent fake citations. You must return only valid JSON matching the required schema. Focus on property-law scenarios for the MVP. Always include missing facts and a legal disclaimer. If the scenario involves urgency, force, police, court notice, fraud, limitation, or risk of losing possession, recommend consulting a qualified local lawyer.

---

## 7. Safety Keywords (Non-Exhaustive)

Useful for heuristic escalation of `consult_lawyer_warning`:

- court notice  
- police  
- FIR  
- arrest  
- threat  
- violence  
- lockout  
- force  
- eviction  
- forged  
- fraud  
- demolition  
- government acquisition  
- limitation  
- inheritance  
- illegal possession  
- property sale fraud  
- builder fraud  

---

## 8. Difference from Mock Trial

| Mock Trial Components | Scenario Analyzer Chatbot |
|----------------------|----------------------------|
| For students / legal training | For citizens / legal literacy |
| Starts with **generated** premise | Starts with **user’s** real-life scenario |
| User writes **legal argument** | User asks for **guidance / explanation** |
| Opposing counsel **challenges** argument | Assistant **explains** and maps issues |
| Objection model gives **structured feedback** | Assistant maps rights/remedies (when implemented) |
| Learning dashboard / session history (concept + partial API) | Explanation + warning + disclaimer |
| **Local** Qwen + LoRA inference in backend | **External API** for MVP (by design) |

---

## 9. Limitations

- **API-only** design for MVP: answers are not automatically grounded in repository legal JSON.  
- **Not legal advice**; state-specific law and procedure vary.  
- **Hallucination risk** inherent to LLMs; mitigations should include disclaimers, structured output, and (future) RAG citations.  
- **No RAG / rule engine / Prolog** in this component until built.

---

## 10. Future Upgrade Path

1. Normalize scraper JSON into unified legal chunks.  
2. Build a vector database over chunks.  
3. Add **RAG** retrieval before generation.  
4. Add **JSON legal rules** / deterministic checks where appropriate.  
5. Add **source citations** in responses.  
6. Add **Prolog/Datalog** or similar for explainable rule chains (research-grade).  
7. Multilingual prompts and UI.  
8. Voice input/output.
