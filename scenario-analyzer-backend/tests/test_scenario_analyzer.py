"""
Scenario Analyzer — unit tests + HTTP API tests (single file).

API sections below document request/response JSON shapes for manual testing and pytest.
Mocks use the same structures so tests run without GEMINI_API_KEY.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import config as app_config
from app.database import init_db, reset_engine
from app.repositories import scenario_repository as repo
from app.scenario_analyzer.response_parser import extract_json_from_text
from app.scenario_analyzer.safety_layer import detect_safety_risk
from app.scenario_analyzer.scenario_classifier import classify_scenario
from app.scenario_analyzer.scenario_service import analyze_scenario
from app.scenario_analyzer.source_pack_loader import load_source_pack

# =============================================================================
# API JSON contracts (reference + reuse in tests)
# =============================================================================
#
# 1) GET /health
#    200 response (example shape):
#    {
#      "status": "ok",
#      "component": "Citizen Legal Scenario Analyzer",
#      "mode": "standalone",
#      "database": "sqlite",
#      "gemini_model": "<from .env>",
#      "scenario_routes_loaded_from": "<path>/scenario_routes.py",
#      "scenario_api_paths": ["/api/scenario/analyze", "/api/scenario/chat", ...]
#    }
#
# 2) GET /openapi.json
#    200: OpenAPI 3.1 document; paths must include /api/scenario/chat, /report/{session_id}, etc.
#
# 3) GET /api/scenario/source-packs
#    200:
#    { "available_source_packs": ["tenant_eviction", "mutation_vs_title", ...] }
#
# 4) GET /api/scenario/debug/config  (APP_ENV=development only; else 404)
#    200:
#    {
#      "gemini_key_loaded": true,
#      "gemini_model": "gemini-2.5-flash",
#      "source_packs_path_exists": true,
#      "available_source_packs": ["<pack_id>", ...],
#      "database_url_prefix": "sqlite"
#    }
#
# 5) GET /api/scenario/sessions  (development only; else 404)
#    200: { "sessions": [{ "session_id", "original_scenario", "issue_type", "source_pack_used", "created_at" }] }
#
# 6) POST /api/scenario/analyze
#    Request body:
#    {
#      "scenario": "<string, min length 10>",
#      "user_context": { "state": "Karnataka", "language": "English" }   // optional
#    }
#    Query (optional, development only): include_full_report_debug=true
#    200 success:
#    {
#      "session_id": "<uuid>",
#      "compact_view": {
#        "detected_issue": "<string>",
#        "short_summary": "<string>",
#        "main_points": ["<string>", ...],
#        "recommended_next_steps": ["<string>", ...],
#        "lawyer_warning": { "required": <bool>, "reason": "<string>" },
#        "confidence": "Low|Medium|High",
#        "disclaimer": "<fixed disclaimer string>"
#      },
#      "suggested_follow_up_questions": ["<string>", ...],
#      "full_report_available": true,
#      "full_report": { ... }   // only if dev + include_full_report_debug=true
#    }
#    422: Pydantic validation (e.g. scenario too short)
#
# 7) GET /api/scenario/report/{session_id}
#    200: { "session_id": "<uuid>", "full_report": { ... full report schema ... } }
#    404: unknown session / no report row
#
# 8) POST /api/scenario/chat
#    Request:
#    { "session_id": "<uuid>", "message": "<string, min length 1>" }
#    200:
#    {
#      "session_id": "<uuid>",
#      "assistant_message": "<string>",
#      "updated_understanding": ["<string>", ...],
#      "next_follow_up_questions": ["<string>", ...],
#      "recommended_next_steps": ["<string>", ...],
#      "lawyer_warning": { "required": <bool>, "reason": "<string>" },
#      "disclaimer": "<fixed disclaimer string>"
#    }
#    404: unknown session_id or missing report
#    422: empty message
#
# 9) GET /api/scenario/chat/{session_id}
#    200:
#    {
#      "session_id": "<uuid>",
#      "messages": [
#        { "role": "assistant|user|system", "content": "<string>", "created_at": "<iso>" }
#      ]
#    }
#    404: unknown session
#
# =============================================================================

DISCLAIMER = (
    "This is legal information for awareness and education, not legal advice."
)

# --- Example: POST /api/scenario/analyze (valid request) ---
JSON_ANALYZE_REQUEST_EXAMPLE: dict[str, Any] = {
    "scenario": "My landlord is forcing me to leave before the rental agreement ends.",
    "user_context": {"state": "Karnataka", "language": "English"},
}

# --- Example: invalid analyze (triggers 422) ---
JSON_ANALYZE_REQUEST_INVALID_SHORT: dict[str, Any] = {"scenario": "short"}

# --- Mock body: what Gemini returns as text for analyze (full report schema) ---
MOCK_GEMINI_ANALYZE_FULL_REPORT: dict[str, Any] = {
    "scenario_summary": "Summary for tests.",
    "detected_domain": "property_law",
    "issue_type": "tenant_eviction",
    "simplified_explanation": "Educational explanation.",
    "facts_identified": ["Written agreement mentioned."],
    "missing_facts": ["Notice details unclear."],
    "rights_possibly_involved": [],
    "possible_remedies": ["Preserve documents."],
    "possible_outcomes": [],
    "reasoning_trace": ["Test trace."],
    "source_pack_used": "tenant_eviction",
    "official_sources_referenced": [],
    "source_grounding_status": "curated",
    "consult_lawyer_warning": False,
    "warning_reason": "",
    "confidence": "Medium",
    "disclaimer": DISCLAIMER,
}

# --- Mock: POST /api/scenario/chat Gemini JSON response ---
MOCK_GEMINI_CHAT_REPLY: dict[str, Any] = {
    "assistant_message": "Thanks. A few more details would help.",
    "updated_understanding": ["User described rent context."],
    "next_follow_up_questions": ["Is the agreement written?", "Any notice given?"],
    "recommended_next_steps": ["Keep copies of rent receipts."],
    "lawyer_warning": {"required": False, "reason": ""},
    "disclaimer": DISCLAIMER,
}

# --- Mock: POST /api/scenario/score Gemini JSON response ---
MOCK_GEMINI_SCORE_REPLY: dict[str, Any] = {
    "legal_clarity_score": 0,
    "clarity_level": "Good Clarity",
    "score_breakdown": {
        "issue_understanding": {
            "score": 20,
            "max_score": 25,
            "reason": "Issue category is clear from classification.",
            "sub_scores": {
                "issue_category_detected": 15,
                "specific_sub_issue_detected": 3,
                "user_confirmed_or_refined_issue": 2,
            },
        },
        "fact_clarity": {
            "score": 18,
            "max_score": 30,
            "reason": "Some timeline and party details emerged.",
            "sub_scores": {
                "ownership_or_history_clarified": 5,
                "timeline_clarified": 4,
                "possession_clarified": 3,
                "parties_or_legal_heirs_clarified": 3,
                "current_dispute_trigger_clarified": 3,
            },
        },
        "document_clarity": {
            "score": 12,
            "max_score": 25,
            "reason": "Agreement mentioned; receipts thin.",
            "sub_scores": {
                "core_document_mentioned": 5,
                "mutation_or_revenue_record_mentioned": 2,
                "receipt_or_payment_proof_mentioned": 2,
                "notice_complaint_or_court_papers_mentioned": 2,
                "missing_documents_identified": 1,
            },
        },
        "risk_clarity": {
            "score": 10,
            "max_score": 20,
            "reason": "Urgency and notice context partially clarified.",
            "sub_scores": {
                "urgency_detected": 3,
                "possession_or_dispossession_risk_clarified": 3,
                "fraud_forgery_or_mutation_change_clarified": 2,
                "lawyer_police_or_court_trigger_clarified": 2,
            },
        },
    },
    "strengths": ["Clear rental relationship described."],
    "remaining_gaps": ["Exact dates of notices still unclear."],
    "summary_feedback": "Good progress on facts; more document detail would help clarity.",
    "teacher_explanation": (
        "This score measures how clearly the scenario was clarified through the conversation. "
        "It does not measure legal correctness or predict legal outcome."
    ),
}

# --- Example: POST /api/scenario/chat (valid request) ---
JSON_CHAT_REQUEST_EXAMPLE = (
    lambda session_id: {
        "session_id": session_id,
        "message": "The landlord wants me out tomorrow with no notice.",
    }
)

# Keys we assert on API success bodies
KEYS_HEALTH = (
    "status",
    "component",
    "mode",
    "database",
    "gemini_model",
    "scenario_api_paths",
    "scenario_routes_loaded_from",
)
KEYS_ANALYZE_200 = ("session_id", "issue_type", "compact_view", "suggested_follow_up_questions", "full_report_available")
KEYS_COMPACT_VIEW = (
    "detected_issue",
    "short_summary",
    "main_points",
    "recommended_next_steps",
    "lawyer_warning",
    "confidence",
    "disclaimer",
)
KEYS_REPORT_200 = ("session_id", "full_report")
KEYS_CHAT_200 = (
    "session_id",
    "assistant_message",
    "updated_understanding",
    "next_follow_up_questions",
    "recommended_next_steps",
    "lawyer_warning",
    "disclaimer",
)
KEYS_CHAT_HISTORY_200 = ("session_id", "messages")
KEYS_CHAT_MESSAGE = ("role", "content", "created_at")
KEYS_SCORE_200 = (
    "session_id",
    "legal_clarity_score",
    "clarity_level",
    "score_breakdown",
    "strengths",
    "remaining_gaps",
    "summary_feedback",
    "teacher_explanation",
)

EXPECTED_SCENARIO_API_PATHS = frozenset(
    {
        "/api/scenario/analyze",
        "/api/scenario/chat",
        "/api/scenario/chat/{session_id}",
        "/api/scenario/debug/config",
        "/api/scenario/report/{session_id}",
        "/api/scenario/score/{session_id}",
        "/api/scenario/sessions",
        "/api/scenario/source-packs",
    }
)

SOURCE_PACK_ORDER = [
    "tenant_eviction",
    "mutation_vs_title",
    "sale_deed_dispute",
    "rera_delay",
    "partition_ancestral_property",
]


# --- pytest fixtures ---


@pytest.fixture
def mock_analyze_gemini(monkeypatch):
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_service.call_gemini",
        lambda *_a, **_k: json.dumps(MOCK_GEMINI_ANALYZE_FULL_REPORT),
    )


@pytest.fixture
def session_from_analyze(client: TestClient, mock_analyze_gemini):
    resp = client.post("/api/scenario/analyze", json=JSON_ANALYZE_REQUEST_EXAMPLE)
    assert resp.status_code == 200
    data = resp.json()
    for k in KEYS_ANALYZE_200:
        assert k in data
    return data["session_id"]


# =============================================================================
# Unit tests (classifier, safety, packs, parser, DB)
# =============================================================================


def test_unit_classify_tenant_eviction():
    r = classify_scenario(
        "My landlord is forcing me to leave before the rental agreement ends."
    )
    assert r["issue_type"] == "tenant_eviction"
    assert r["score"] >= 1


def test_unit_classify_mutation():
    r = classify_scenario(
        "My brother changed mutation records after my father died without notice."
    )
    assert r["issue_type"] == "mutation_vs_title"


def test_unit_classify_sale_deed():
    r = classify_scenario(
        "I have a dispute about my registered sale deed with the buyer and seller."
    )
    assert r["issue_type"] == "sale_deed_dispute"


def test_unit_classify_rera_delay():
    r = classify_scenario(
        "The builder delayed possession of my apartment for two years under RERA."
    )
    assert r["issue_type"] == "rera_delay"


def test_unit_classify_partition():
    r = classify_scenario(
        "My uncle sold ancestral family property without informing legal heirs."
    )
    assert r["issue_type"] == "partition_ancestral_property"


def test_unit_safety_layer_warning():
    s = "The police came and there was a court notice about eviction."
    r = detect_safety_risk(s, None)
    assert r["consult_lawyer_warning"] is True
    assert len(r["matched_safety_keywords"]) >= 1


def test_unit_source_pack_loading():
    pack = load_source_pack("tenant_eviction")
    assert pack["issue_type"] == "tenant_eviction"


def test_unit_source_pack_fallback():
    pack = load_source_pack("nonexistent_issue_type_xyz")
    assert pack.get("_fallback_used") is True
    assert pack.get("_requested_issue_type") == "nonexistent_issue_type_xyz"


def test_unit_extract_json_from_fence():
    text = 'Here:\n```json\n{"a": 1}\n```'
    assert extract_json_from_text(text) == {"a": 1}


def test_unit_extract_json_with_prefix_and_suffix():
    text = 'Sure — here you go:\n{"ok": true, "n": 3}\nHope this helps.'
    assert extract_json_from_text(text) == {"ok": True, "n": 3}


def test_unit_extract_json_skips_stray_brace_then_raw_decodes():
    text = 'Note: {invalid} then real payload {"assistant_message": "hi", "x": 1}'
    out = extract_json_from_text(text)
    assert out["assistant_message"] == "hi"
    assert out["x"] == 1


def test_unit_extract_json_raw_decode_trailing_prose_after_object():
    text = '{"a": 1} Thanks — let me know if you need more.'
    assert extract_json_from_text(text) == {"a": 1}


def test_unit_database_init_runs():
    reset_engine()
    init_db()


def test_unit_analyze_scenario_fallback_on_api_error(monkeypatch):
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_service.call_gemini",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("api down")),
    )
    out = analyze_scenario(JSON_ANALYZE_REQUEST_EXAMPLE["scenario"])
    assert "session_id" in out
    assert out["issue_type"]
    assert out["compact_view"]["short_summary"]
    assert out["compact_view"]["lawyer_warning"]["required"] is False


def test_unit_analyze_scenario_with_mock_gemini(monkeypatch):
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_service.call_gemini",
        lambda *_a, **_k: json.dumps(MOCK_GEMINI_ANALYZE_FULL_REPORT),
    )
    out = analyze_scenario(
        JSON_ANALYZE_REQUEST_EXAMPLE["scenario"],
        JSON_ANALYZE_REQUEST_EXAMPLE.get("user_context"),
    )
    assert out["compact_view"]["short_summary"]
    assert out["full_report_available"] is True
    sid = out["session_id"]
    row = repo.get_report(sid)
    assert row is not None
    assert row["full_report"].get("issue_type") == "tenant_eviction"


# =============================================================================
# API — GET /health
# =============================================================================


def test_api_health_ok(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    for k in KEYS_HEALTH:
        assert k in body, f"missing key {k}"
    assert body["status"] == "ok"
    assert body["component"] == "Citizen Legal Scenario Analyzer"
    assert body.get("database") == "sqlite"
    assert set(body["scenario_api_paths"]) == EXPECTED_SCENARIO_API_PATHS
    assert str(body["scenario_routes_loaded_from"]).endswith("scenario_routes.py")


# =============================================================================
# API — GET /openapi.json
# =============================================================================


def test_api_openapi_contains_scenario_paths(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = set(r.json().get("paths", {}).keys())
    assert "/api/scenario/chat" in paths
    assert "/api/scenario/report/{session_id}" in paths
    assert "/api/scenario/analyze" in paths
    assert "/api/scenario/score/{session_id}" in paths


# =============================================================================
# API — GET /api/scenario/source-packs
# =============================================================================


def test_api_source_packs_ok(client: TestClient):
    r = client.get("/api/scenario/source-packs")
    assert r.status_code == 200
    assert r.json()["available_source_packs"] == SOURCE_PACK_ORDER


# =============================================================================
# API — GET /api/scenario/debug/config
# =============================================================================


def test_api_debug_config_ok_in_development(monkeypatch, client: TestClient):
    monkeypatch.setattr(app_config.settings, "APP_ENV", "development")
    r = client.get("/api/scenario/debug/config")
    assert r.status_code == 200
    j = r.json()
    assert set(j.keys()) >= {"gemini_key_loaded", "gemini_model", "source_packs_path_exists", "available_source_packs"}


def test_api_debug_config_404_in_production(monkeypatch, client: TestClient):
    monkeypatch.setattr(app_config.settings, "APP_ENV", "production")
    assert client.get("/api/scenario/debug/config").status_code == 404


# =============================================================================
# API — GET /api/scenario/sessions
# =============================================================================


def test_api_sessions_ok_in_development(monkeypatch, client: TestClient):
    monkeypatch.setattr(app_config.settings, "APP_ENV", "development")
    r = client.get("/api/scenario/sessions")
    assert r.status_code == 200
    assert "sessions" in r.json()


def test_api_sessions_404_in_production(monkeypatch, client: TestClient):
    monkeypatch.setattr(app_config.settings, "APP_ENV", "production")
    assert client.get("/api/scenario/sessions").status_code == 404


# =============================================================================
# API — POST /api/scenario/analyze
# =============================================================================


def test_api_analyze_422_short_scenario(client: TestClient):
    r = client.post("/api/scenario/analyze", json=JSON_ANALYZE_REQUEST_INVALID_SHORT)
    assert r.status_code == 422


def test_api_analyze_200_without_gemini_key(monkeypatch, client: TestClient):
    monkeypatch.setattr(app_config.settings, "GEMINI_API_KEY", None)
    r = client.post("/api/scenario/analyze", json={"scenario": JSON_ANALYZE_REQUEST_EXAMPLE["scenario"]})
    assert r.status_code == 200
    data = r.json()
    for k in KEYS_ANALYZE_200:
        assert k in data
    cv = data["compact_view"]
    for k in KEYS_COMPACT_VIEW:
        assert k in cv


def test_api_analyze_200_shape_with_mock_gemini(client: TestClient, mock_analyze_gemini):
    r = client.post("/api/scenario/analyze", json=JSON_ANALYZE_REQUEST_EXAMPLE)
    assert r.status_code == 200
    data = r.json()
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        data["session_id"],
        re.I,
    )
    cv = data["compact_view"]
    for k in KEYS_COMPACT_VIEW:
        assert k in cv
    assert cv["lawyer_warning"]["required"] in (True, False)
    assert isinstance(data["suggested_follow_up_questions"], list)
    assert len(data["suggested_follow_up_questions"]) <= 4
    assert data["full_report_available"] is True


def test_api_analyze_full_report_debug_query_development(monkeypatch, client: TestClient, mock_analyze_gemini):
    monkeypatch.setattr(app_config.settings, "APP_ENV", "development")
    r = client.post(
        "/api/scenario/analyze?include_full_report_debug=true",
        json={"scenario": JSON_ANALYZE_REQUEST_EXAMPLE["scenario"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "full_report" in data
    assert data["full_report"].get("issue_type") == "tenant_eviction"


def test_api_analyze_full_report_debug_ignored_in_production(monkeypatch, client: TestClient, mock_analyze_gemini):
    monkeypatch.setattr(app_config.settings, "APP_ENV", "production")
    r = client.post(
        "/api/scenario/analyze?include_full_report_debug=true",
        json={"scenario": JSON_ANALYZE_REQUEST_EXAMPLE["scenario"]},
    )
    assert r.status_code == 200
    assert "full_report" not in r.json()


@pytest.mark.skipif(
    not (app_config.settings.GEMINI_API_KEY or "").strip(),
    reason="GEMINI_API_KEY not set; skipping live Gemini call",
)
def test_api_analyze_live_gemini_optional(client: TestClient):
    r = client.post("/api/scenario/analyze", json=JSON_ANALYZE_REQUEST_EXAMPLE)
    assert r.status_code == 200
    out = r.json()
    assert "disclaimer" in out["compact_view"]
    assert out.get("session_id")


# =============================================================================
# API — GET /api/scenario/report/{session_id}
# =============================================================================


def test_api_report_404_unknown_session(client: TestClient):
    assert client.get(f"/api/scenario/report/{uuid.uuid4()}").status_code == 404


def test_api_report_200_after_analyze(client: TestClient, session_from_analyze):
    r = client.get(f"/api/scenario/report/{session_from_analyze}")
    assert r.status_code == 200
    data = r.json()
    for k in KEYS_REPORT_200:
        assert k in data
    assert data["session_id"] == session_from_analyze
    assert data["full_report"].get("scenario_summary")


# =============================================================================
# API — POST /api/scenario/chat
# =============================================================================


def test_api_chat_404_unknown_session(client: TestClient):
    r = client.post(
        "/api/scenario/chat",
        json={"session_id": str(uuid.uuid4()), "message": "Hello"},
    )
    assert r.status_code == 404


def test_api_chat_422_empty_message(client: TestClient, session_from_analyze):
    r = client.post(
        "/api/scenario/chat",
        json={"session_id": session_from_analyze, "message": ""},
    )
    assert r.status_code == 422


def test_api_chat_200_fallback_when_gemini_key_missing(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(app_config.settings, "GEMINI_API_KEY", None)
    r = client.post(
        "/api/scenario/chat",
        json=JSON_CHAT_REQUEST_EXAMPLE(session_from_analyze),
    )
    assert r.status_code == 200
    data = r.json()
    for k in KEYS_CHAT_200:
        assert k in data
    assert data["next_follow_up_questions"] == []
    assert "?" in data["assistant_message"]


def test_api_chat_200_with_mock_gemini(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_chat_service.call_gemini",
        lambda *_a, **_k: json.dumps(MOCK_GEMINI_CHAT_REPLY),
    )
    r = client.post(
        "/api/scenario/chat",
        json=JSON_CHAT_REQUEST_EXAMPLE(session_from_analyze),
    )
    assert r.status_code == 200
    data = r.json()
    for k in KEYS_CHAT_200:
        assert k in data
    assert data["session_id"] == session_from_analyze
    assert data["assistant_message"]


def test_api_chat_200_fallback_when_gemini_raises(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_chat_service.call_gemini",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    r = client.post(
        "/api/scenario/chat",
        json={"session_id": session_from_analyze, "message": "More facts here."},
    )
    assert r.status_code == 200
    data = r.json()
    # Issue-aware API failure copy (tenant pack for this session), not generic "could not process"
    assert "landlord" in data["assistant_message"].lower() or "tenant" in data["assistant_message"].lower()
    assert data["next_follow_up_questions"] == []
    assert "?" in data["assistant_message"]


def test_api_chat_partial_json_empty_assistant_gets_synthetic(monkeypatch, client: TestClient, session_from_analyze):
    """Model JSON missing assistant text: merge + synthetic, not full API failure."""
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_chat_service.call_gemini",
        lambda *_a, **_k: json.dumps(
            {
                "assistant_message": "",
                "updated_understanding": ["User added more facts."],
                "next_follow_up_questions": [],
                "recommended_next_steps": [],
                "lawyer_warning": {"required": False, "reason": ""},
                "disclaimer": DISCLAIMER,
            }
        ),
    )
    r = client.post(
        "/api/scenario/chat",
        json={"session_id": session_from_analyze, "message": "We still live on the property."},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["assistant_message"]) > 40
    assert data["updated_understanding"]
    assert data["next_follow_up_questions"] == []


# =============================================================================
# API — GET /api/scenario/chat/{session_id}
# =============================================================================


def test_api_chat_history_404_unknown_session(client: TestClient):
    assert client.get(f"/api/scenario/chat/{uuid.uuid4()}").status_code == 404


def test_api_chat_history_200_after_analyze(client: TestClient, session_from_analyze):
    r = client.get(f"/api/scenario/chat/{session_from_analyze}")
    assert r.status_code == 200
    data = r.json()
    for k in KEYS_CHAT_HISTORY_200:
        assert k in data
    assert data["session_id"] == session_from_analyze
    assert "assistant" in {m["role"] for m in data["messages"]}
    for m in data["messages"]:
        for k in KEYS_CHAT_MESSAGE:
            assert k in m


def test_api_chat_history_includes_user_after_post_chat(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(
        "app.scenario_analyzer.scenario_chat_service.call_gemini",
        lambda *_a, **_k: json.dumps(
            {
                "assistant_message": "Noted.",
                "updated_understanding": [],
                "next_follow_up_questions": ["Next?"],
                "recommended_next_steps": [],
                "lawyer_warning": {"required": False, "reason": ""},
                "disclaimer": DISCLAIMER,
            }
        ),
    )
    client.post(
        "/api/scenario/chat",
        json={"session_id": session_from_analyze, "message": "I have a written lease."},
    )
    r = client.get(f"/api/scenario/chat/{session_from_analyze}")
    assert r.status_code == 200
    roles = [m["role"] for m in r.json()["messages"]]
    assert "user" in roles
    assert "assistant" in roles


# =============================================================================
# API — Legal Clarity Score
# =============================================================================


def test_api_score_get_404_unknown_session(client: TestClient):
    assert client.get(f"/api/scenario/score/{uuid.uuid4()}").status_code == 404


def test_api_score_get_404_not_generated_yet(client: TestClient, session_from_analyze):
    r = client.get(f"/api/scenario/score/{session_from_analyze}")
    assert r.status_code == 404
    j = r.json()
    assert j.get("score_available") is False
    assert "message" in j


def test_api_score_post_uses_fallback_without_gemini(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(app_config.settings, "GEMINI_API_KEY", None)
    r = client.post(f"/api/scenario/score/{session_from_analyze}")
    assert r.status_code == 200
    data = r.json()
    for k in KEYS_SCORE_200:
        assert k in data
    assert data["session_id"] == session_from_analyze
    assert 0 <= data["legal_clarity_score"] <= 100
    assert data["score_breakdown"]["issue_understanding"]["max_score"] == 25


def test_api_score_post_with_mock_gemini(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(
        "app.scenario_analyzer.scoring_service.call_gemini",
        lambda *_a, **_k: json.dumps(MOCK_GEMINI_SCORE_REPLY),
    )
    r = client.post(f"/api/scenario/score/{session_from_analyze}")
    assert r.status_code == 200
    data = r.json()
    # Total must be recomputed from sub-scores (not trust model top-level 0)
    assert data["legal_clarity_score"] == 15 + 3 + 2 + 5 + 4 + 3 + 3 + 3 + 5 + 2 + 2 + 2 + 1 + 3 + 3 + 2 + 2
    assert data["clarity_level"] in ("Low Clarity", "Basic Clarity", "Good Clarity", "Strong Clarity")
    g = client.get(f"/api/scenario/score/{session_from_analyze}")
    assert g.status_code == 200
    assert g.json()["legal_clarity_score"] == data["legal_clarity_score"]


def test_api_score_post_overwrites_existing(monkeypatch, client: TestClient, session_from_analyze):
    monkeypatch.setattr(
        "app.scenario_analyzer.scoring_service.call_gemini",
        lambda *_a, **_k: json.dumps(MOCK_GEMINI_SCORE_REPLY),
    )
    assert client.post(f"/api/scenario/score/{session_from_analyze}").status_code == 200
    monkeypatch.setattr(
        "app.scenario_analyzer.scoring_service.call_gemini",
        lambda *_a, **_k: json.dumps({**MOCK_GEMINI_SCORE_REPLY, "legal_clarity_score": 999}),
    )
    r2 = client.post(f"/api/scenario/score/{session_from_analyze}")
    assert r2.status_code == 200
    assert r2.json()["legal_clarity_score"] < 200
