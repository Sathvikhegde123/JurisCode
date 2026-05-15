# Citizen Legal Scenario Analyzer

Standalone MVP for JurisCode.

## What it does

Separate citizen-facing legal scenario analyzer using the Gemini API and curated source packs. It runs in **two stages** (with an optional **Legal Clarity Score** step on demand):

1. **Analyze** — Builds a **full structured legal report** internally, saves it to **SQLite**, and returns a **compact summary** plus `session_id` and suggested follow-up questions.  
2. **Chat** — Continues a **Socratic, conversational** thread using the stored report, source pack, and chat history (also in SQLite).  
3. **Legal Clarity Score** (optional) — After the user explicitly requests it, computes and stores a **clarity-only** 100-point score (see README section below); it does not judge legal correctness or predict outcome.

## What it is not

- Not part of the mock trial workflow  
- Not RAG yet  
- Not legal advice  
- Not a lawyer replacement  

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your `GEMINI_API_KEY` to `.env`, then:

```bash
python run_server.py
```

By default the API listens on `http://127.0.0.1:8001` (`APP_PORT` in `.env`; see `app/config.py`).

## Workflow (analyze → chat → optional clarity score)

### 1. Analyze scenario

`POST /api/scenario/analyze`

Generates the full report internally, stores it in SQLite, and returns `session_id`, `compact_view`, `suggested_follow_up_questions`, and `full_report_available`.

### 2. Continue chat

`POST /api/scenario/chat`

Body: `{ "session_id": "<uuid>", "message": "..." }`  
Uses the stored report and history for Socratic follow-up.

### 3. View full report

`GET /api/scenario/report/{session_id}`

Returns the stored full JSON report (for a “View full report” action in the UI).

### 4. Chat history

`GET /api/scenario/chat/{session_id}`

Returns messages for the session.

### 5. Legal Clarity Score (on demand)

`POST /api/scenario/score/{session_id}` — builds a **100-point clarity metric** from the stored session, full report, and chat history, then saves it (overwrites any previous score for that session).

`GET /api/scenario/score/{session_id}` — returns the saved score, or **404** with:

```json
{ "score_available": false, "message": "Score has not been generated for this session yet." }
```

Swagger lists both routes under `/api/scenario`.

## Legal Clarity Score

Legal Clarity Score is a **100-point clarity metric** generated **only** after the user explicitly requests scoring (e.g. “Finish & Generate Clarity Score” in the UI). It does **not** measure legal correctness, legal validity, or case outcome.

**Formula**

Legal Clarity Score = Issue Understanding + Fact Clarity + Document Clarity + Risk Clarity

**Rubric**

| Category | Max | Sub-weights |
|----------|-----|-------------|
| **Issue Understanding** | 25 | Issue category detected: 15; Specific sub-issue detected: 5; User confirmed/refined issue: 5 |
| **Fact Clarity** | 30 | Ownership/history: 8; Timeline: 6; Possession: 6; Parties/legal heirs: 5; Current dispute trigger: 5 |
| **Document Clarity** | 25 | Sale/gift/will/agreement: 7; Mutation/revenue record: 6; Tax/rent/payment receipts: 4; Notice/complaint/court papers: 4; Missing documents identified: 4 |
| **Risk Clarity** | 20 | Urgency: 5; Possession/dispossession risk: 5; Fraud/forgery/mutation change: 5; Lawyer/police/court trigger: 5 |

**Score bands**

- 0–39: Low Clarity  
- 40–59: Basic Clarity  
- 60–79: Good Clarity  
- 80–100: Strong Clarity  

**Teacher explanation**

We designed this as a **clarity score**, not a legal correctness score. It measures whether the Socratic conversation clarified the issue, key facts, documents, and risk factors. This makes the score educational and explainable **without** predicting legal outcomes.

Implementation notes:

- **Gemini** receives the full rubric and conversation context; the service **recomputes** the total from clamped sub-scores (never trusts the model’s top-level total blindly).  
- **Fallback:** If Gemini fails or JSON is invalid, a **keyword/rule-based** scorer fills sub-scores, then the same normalization applies.

### Development-only

- `GET /api/scenario/sessions` — recent sessions  
- `GET /api/scenario/debug/config` — config snapshot  
- Optional query on analyze: `include_full_report_debug=true` — includes `full_report` in the analyze response  

## Database

SQLite stores:

- Sessions (scenario text, user context, classification metadata, warnings)  
- Full and compact report JSON  
- Chat messages  
- **Legal Clarity Score** rows (`scenario_scores`: one upserted row per `session_id`)

Configure with `DATABASE_URL` in `.env` (default: `sqlite:///./scenario_analyzer.db`).

## API (short)

### `GET /health`

Returns service status, `gemini_model`, and `database: "sqlite"`.

### `POST /api/scenario/analyze`

Example request:

```json
{
  "scenario": "My landlord is forcing me to leave before the agreement ends.",
  "user_context": {
    "state": "Karnataka",
    "language": "English"
  }
}
```

### `GET /api/scenario/source-packs`

Returns the list of curated pack identifiers.

## Source packs

JSON packs live in `source_packs/`. Each pack contains curated statutory summaries, document checklists, safety triggers, and response guidance used to ground Gemini output.

## Data sources

Place official PDFs under `data_sources/` in the provided act folders when you add them. The MVP does not parse these files; they are for future verification and RAG.

## Current limitations

- Exact statutory section verification is pending  
- No retrieval over PDFs  
- Source packs are curated summaries only  
- Output is legal information for awareness, not advice  
- Keyword classifier; misclassification is possible  

## Tests

```bash
python -m pytest
```

## Manual HTTP smoke test

With the server running and `GEMINI_API_KEY` set:

```bash
python tests/manual_test_requests.py
```
