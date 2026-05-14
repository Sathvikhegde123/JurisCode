# Citizen Legal Scenario Analyzer

Standalone MVP for JurisCode.

## What it does

Separate citizen-facing legal scenario analyzer using the Gemini API and curated source packs. It runs in **two stages**:

1. **Analyze** — Builds a **full structured legal report** internally, saves it to **SQLite**, and returns a **compact summary** plus `session_id` and suggested follow-up questions.  
2. **Chat** — Continues a **Socratic, conversational** thread using the stored report, source pack, and chat history (also in SQLite).

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

## New two-stage workflow

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

### Development-only

- `GET /api/scenario/sessions` — recent sessions  
- `GET /api/scenario/debug/config` — config snapshot  
- Optional query on analyze: `include_full_report_debug=true` — includes `full_report` in the analyze response  

## Database

SQLite stores:

- Sessions (scenario text, user context, classification metadata, warnings)  
- Full and compact report JSON  
- Chat messages  

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
