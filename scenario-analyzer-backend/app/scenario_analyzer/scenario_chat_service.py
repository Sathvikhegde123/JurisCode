"""Stage 2: Socratic chat using stored report, source pack, and SQLite history."""

from __future__ import annotations

import logging
from typing import Any

from app.repositories import scenario_repository as repo
from app.scenario_analyzer.gemini_client import call_gemini
from app.scenario_analyzer.response_parser import extract_json_from_text, merge_chat_response_defaults
from app.scenario_analyzer.safety_layer import apply_safety_override, detect_safety_risk
from app.scenario_analyzer.schemas import RESPONSE_SCHEMA
from app.scenario_analyzer.socratic_prompt_builder import build_socratic_chat_prompt
from app.scenario_analyzer.source_pack_loader import load_source_pack

logger = logging.getLogger(__name__)

DISCLAIMER = RESPONSE_SCHEMA["disclaimer"]

# (assistant_message with exactly one leading question, recommended_next_steps)
_ISSUE_AWARE_FALLBACK: dict[str, tuple[str, list[str]]] = {
    "partition_ancestral_property": (
        "Thanks for sharing that. This still appears to involve family or ancestral property. "
        "First, who originally owned the property, and did that person leave a will?",
        [
            "Preserve sale deeds, family-tree notes, and mutation extracts if you have them.",
            "Consult a local property lawyer if someone is selling or changing records without consent.",
        ],
    ),
    "tenant_eviction": (
        "Thanks; this still looks like a landlord–tenant situation. "
        "First, do you have a written rental agreement, and has the landlord given written notice to vacate?",
        [
            "Keep rent receipts, notices, and any messages about deposit or lockout.",
            "Seek local legal help if eviction is threatened without due process.",
        ],
    ),
    "sale_deed_dispute": (
        "Thanks; this still appears to involve a sale deed or title dispute. "
        "First, do you have a registered sale deed and the previous title documents in the chain?",
        [
            "Collect possession proof and correspondence with the seller or broker.",
            "Consult a local lawyer if forgery or forced signature is alleged.",
        ],
    ),
    "rera_delay": (
        "Thanks; this still appears to involve builder delay or RERA-related facts. "
        "First, what was the promised possession date in your builder–buyer agreement?",
        [
            "Keep allotment letters, payment proofs, and delay letters from the builder.",
            "Check the project's RERA registration page for filings and timelines.",
        ],
    ),
    "mutation_vs_title": (
        "Thanks; this still appears to involve revenue records versus title documents. "
        "First, whose name is currently shown in the mutation or revenue records?",
        [
            "Gather RTC or mutation extracts and the sale or inheritance papers you rely on.",
            "Consult a local lawyer if records and possession do not match your title.",
        ],
    ),
}

_DEFAULT_FALLBACK = (
    "Thanks; this still appears to be a property-related legal issue. "
    "First, what documents do you currently have (agreements, notices, or revenue extracts), "
    "and who is in possession today?",
    [
        "Keep copies of relevant documents and written communication.",
        "Consult a qualified local lawyer if the matter is urgent or records are changing.",
    ],
)


def _fallback_bundle(issue_type: str) -> tuple[str, list[str]]:
    return _ISSUE_AWARE_FALLBACK.get(issue_type, _DEFAULT_FALLBACK)


def _api_failure_chat_response(session_id: str, issue_type: str) -> dict[str, Any]:
    assistant, steps = _fallback_bundle(issue_type)
    return {
        "session_id": session_id,
        "assistant_message": assistant,
        "updated_understanding": [],
        "next_follow_up_questions": [],
        "recommended_next_steps": steps[:3],
        "lawyer_warning": {
            "required": False,
            "reason": "",
        },
        "disclaimer": DISCLAIMER,
    }


def _as_str_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None and str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _synthetic_assistant_message(latest_user_message: str, issue_type: str) -> str:
    """When the model returned JSON but left assistant_message empty."""
    raw = (latest_user_message or "").strip()
    snippet = raw[:200] + ("…" if len(raw) > 200 else "")
    head = (
        "Thanks for that detail. "
        if not snippet
        else f"Thanks for sharing. Referring to: {snippet} "
    )
    body, _ = _fallback_bundle(issue_type)
    return (head + body).strip()[:4000]


def continue_socratic_chat(session_id: str, message: str) -> dict[str, Any]:
    sess = repo.get_session(session_id)
    if sess is None:
        raise ValueError("session_not_found")

    rep = repo.get_report(session_id)
    if rep is None:
        raise ValueError("report_not_found")

    full_report: dict[str, Any] = dict(rep.get("full_report") or {})
    original = str(sess.get("original_scenario") or "")
    issue_type = str(sess.get("source_pack_used") or sess.get("issue_type") or "sale_deed_dispute")
    source_pack = load_source_pack(issue_type)

    history_rows = repo.get_chat_history(session_id, limit=40)
    conversation_history = [{"role": h["role"], "content": h["content"]} for h in history_rows]

    prior_user_message_count = sum(1 for h in history_rows if h.get("role") == "user")
    max_follow_up_questions = 1

    text_msg = (message or "").strip()
    repo.add_chat_message(session_id, "user", text_msg)

    combined_for_safety = f"{original}\n{text_msg}"
    safety = detect_safety_risk(combined_for_safety, source_pack)

    parsed: dict[str, Any] | None = None
    raw: str | None = None
    try:
        sys_p, usr_p = build_socratic_chat_prompt(
            original,
            full_report,
            source_pack,
            conversation_history,
            text_msg,
            prior_user_message_count=prior_user_message_count,
            max_follow_up_questions=max_follow_up_questions,
        )
        raw = call_gemini(
            sys_p,
            usr_p,
            temperature=0.28,
            max_output_tokens=2048,
        )
        parsed = extract_json_from_text(raw)
    except Exception as e:
        preview = (raw or "").strip()[:800]
        logger.warning(
            "Socratic chat Gemini/parse failed: %s | output_preview=%r",
            e,
            preview,
        )
        parsed = None

    if parsed is None:
        fb = _api_failure_chat_response(session_id, issue_type)
        merged_lw = fb["lawyer_warning"]
        fake = {
            "consult_lawyer_warning": merged_lw["required"],
            "warning_reason": merged_lw["reason"],
            "reasoning_trace": list(full_report.get("reasoning_trace") or []),
        }
        overridden = apply_safety_override(fake, safety)
        fb["lawyer_warning"]["required"] = bool(overridden.get("consult_lawyer_warning"))
        if fb["lawyer_warning"]["required"]:
            fb["lawyer_warning"]["reason"] = str(
                overridden.get("warning_reason") or fb["lawyer_warning"]["reason"]
            ).strip()
        repo.add_chat_message(session_id, "assistant", fb["assistant_message"], message_json=fb)
        return fb

    merged = merge_chat_response_defaults(parsed)

    if not str(merged.get("assistant_message") or "").strip():
        merged["assistant_message"] = _synthetic_assistant_message(text_msg, issue_type)

    merged["next_follow_up_questions"] = []

    if not _as_str_list(merged.get("recommended_next_steps")):
        _, steps = _fallback_bundle(issue_type)
        merged["recommended_next_steps"] = steps[:3]

    merged["updated_understanding"] = _as_str_list(merged.get("updated_understanding"))[:8]

    merged["recommended_next_steps"] = _as_str_list(merged.get("recommended_next_steps"))[:3]

    fake_response = {
        "consult_lawyer_warning": merged["lawyer_warning"]["required"],
        "warning_reason": merged["lawyer_warning"]["reason"],
        "reasoning_trace": list(full_report.get("reasoning_trace") or []),
    }
    overridden = apply_safety_override(fake_response, safety)
    merged["lawyer_warning"]["required"] = bool(overridden.get("consult_lawyer_warning"))
    if merged["lawyer_warning"]["required"]:
        merged["lawyer_warning"]["reason"] = str(
            overridden.get("warning_reason") or merged["lawyer_warning"]["reason"] or ""
        ).strip()

    out = {
        "session_id": session_id,
        "assistant_message": str(merged["assistant_message"]).strip(),
        "updated_understanding": merged["updated_understanding"],
        "next_follow_up_questions": [],
        "recommended_next_steps": merged["recommended_next_steps"],
        "lawyer_warning": merged["lawyer_warning"],
        "disclaimer": str(merged.get("disclaimer") or DISCLAIMER),
    }
    repo.add_chat_message(session_id, "assistant", out["assistant_message"], message_json=out)
    return out
