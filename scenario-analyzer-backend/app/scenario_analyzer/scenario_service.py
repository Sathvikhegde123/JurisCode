from __future__ import annotations

from copy import deepcopy
import logging
import uuid
from typing import Any

from app.config import settings
from app.repositories import scenario_repository as repo
from app.scenario_analyzer.compact_view_builder import build_compact_view
from app.scenario_analyzer.followup_question_builder import build_initial_follow_up_questions
from app.scenario_analyzer.gemini_client import call_gemini
from app.scenario_analyzer.response_parser import ensure_required_fields, extract_json_from_text
from app.scenario_analyzer.safety_layer import apply_safety_override, detect_safety_risk
from app.scenario_analyzer.scenario_classifier import classify_scenario
from app.scenario_analyzer.scenario_prompt_builder import build_scenario_prompt
from app.scenario_analyzer.schemas import RESPONSE_SCHEMA
from app.scenario_analyzer.source_pack_loader import load_source_pack

logger = logging.getLogger(__name__)


def _is_dev() -> bool:
    return settings.APP_ENV.strip().lower() == "development"


def _as_str_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val if x is not None]
    if isinstance(val, str):
        return [val]
    return [str(val)]


def _sanitize_full_report_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce types so downstream JSON and DB storage are consistent."""
    out = dict(data)
    for key in (
        "facts_identified",
        "missing_facts",
        "rights_possibly_involved",
        "possible_remedies",
        "possible_outcomes",
        "reasoning_trace",
    ):
        out[key] = _as_str_list(out.get(key))

    refs = out.get("official_sources_referenced")
    clean: list[dict[str, Any]] = []
    if isinstance(refs, list):
        for item in refs:
            if isinstance(item, dict):
                d = dict(item)
                v = d.get("verified")
                if v is not None and not isinstance(v, bool):
                    d["verified"] = str(v).lower() in ("true", "1", "yes")
                clean.append(d)
            elif isinstance(item, str):
                clean.append(
                    {
                        "act_name": item,
                        "section_reference": "",
                        "source_type": "",
                        "source_origin": "",
                        "relevance": "",
                        "verified": False,
                    }
                )
    out["official_sources_referenced"] = clean

    w = out.get("consult_lawyer_warning")
    if not isinstance(w, bool):
        out["consult_lawyer_warning"] = str(w).lower() in ("true", "1", "yes")

    for k in (
        "scenario_summary",
        "detected_domain",
        "issue_type",
        "simplified_explanation",
        "source_pack_used",
        "source_grounding_status",
        "warning_reason",
        "confidence",
        "disclaimer",
    ):
        v = out.get(k)
        if v is None:
            out[k] = ""
        elif not isinstance(v, str):
            out[k] = str(v)

    return out


def _official_refs_from_pack(source_pack: dict[str, Any]) -> list[dict[str, Any]]:
    refs = source_pack.get("official_sources") or []
    if not isinstance(refs, list):
        return []
    out: list[dict[str, Any]] = []
    for item in refs:
        if isinstance(item, dict):
            d = dict(item)
            v = d.get("verified")
            if v is not None and not isinstance(v, bool):
                d["verified"] = str(v).lower() in ("true", "1", "yes")
            out.append(d)
        elif isinstance(item, str):
            out.append(
                {
                    "act_name": item,
                    "section_reference": "",
                    "source_type": "",
                    "source_origin": "",
                    "relevance": "",
                    "verified": False,
                }
            )
    return out


def _adjust_confidence(full_report: dict[str, Any]) -> None:
    facts = _as_str_list(full_report.get("facts_identified"))
    missing = _as_str_list(full_report.get("missing_facts"))
    conf = str(full_report.get("confidence") or "").strip()
    cl = conf.lower()

    if len(facts) >= 4 and len(missing) <= 1:
        if cl in ("low", "medium", ""):
            full_report["confidence"] = "High"
        else:
            full_report["confidence"] = "High"
        return

    if cl == "high":
        full_report["confidence"] = "Medium"
    elif not conf:
        full_report["confidence"] = "Medium"


def _strip_internal_for_storage(full_report: dict[str, Any]) -> dict[str, Any]:
    out = dict(full_report)
    for k in (
        "classification_debug",
        "matched_safety_keywords",
        "gemini_debug",
        "debug_error",
    ):
        out.pop(k, None)
    return out


def _detected_issue_label(issue_type: str, source_pack: dict[str, Any]) -> str:
    if source_pack.get("_fallback_used"):
        return issue_type.replace("_", " ").title()
    name = str(source_pack.get("display_name") or "").strip()
    if name:
        return name
    return issue_type.replace("_", " ").title()


def _normalize_user_context(user_context: dict[str, Any] | None) -> dict[str, Any]:
    uc = dict(user_context or {})
    uc.setdefault("state", "Unknown")
    uc.setdefault("language", "English")
    return uc


def _issue_theme_sentence(issue_type: str) -> str:
    return {
        "partition_ancestral_property": "family or ancestral property, co-heirs, and possible claims around sales or partitions",
        "tenant_eviction": "landlord–tenant rights, notices, and lawful possession",
        "sale_deed_dispute": "sale deeds, title chains, and disputes over ownership or possession",
        "rera_delay": "builder delays, agreed possession timelines, and buyer remedies that may exist under RERA and contract law",
        "mutation_vs_title": "revenue or mutation records compared with registered title documents",
    }.get(
        issue_type,
        "property-related documents, possession, and rights that depend on verified facts",
    )


def _word_count(s: str) -> int:
    return len([w for w in (s or "").split() if w.strip()])


def _fallback_full_report(
    issue_type: str,
    source_pack: dict[str, Any],
    *,
    user_scenario: str = "",
    pipeline_errors: list[str] | None = None,
    debug_error: str | None = None,
) -> dict[str, Any]:
    refs = source_pack.get("official_sources") or []
    if not isinstance(refs, list):
        refs = []
    cleaned = " ".join((user_scenario or "").split())
    if len(cleaned) > 420:
        cleaned = cleaned[:420] + "…"
    theme = _issue_theme_sentence(issue_type)
    scenario_summary = (
        f"You described the following situation: {cleaned}. "
        f"Based on that description, the closest match for awareness purposes relates to {theme}. "
        f"Exact outcomes depend on documents, forum, and local practice, so the emphasis here is on "
        f"clarifying facts and sensible next checks rather than predicting a court result."
    )
    if _word_count(scenario_summary) < 18:
        scenario_summary += (
            " This overview is for general legal literacy only and is not legal advice; "
            "a qualified lawyer can review your papers if you need case-specific guidance."
        )

    simplified_explanation = (
        f"Because the structured model output could not be read reliably, this page uses a cautious, "
        f"source-pack-grounded outline instead of a full AI narrative. Your description still matters: "
        f"we treat it as involving {theme}. Use the guided chat to add dates, parties, documents, and "
        f"what changed step by step so the picture becomes clearer."
    )

    if _is_dev() and pipeline_errors:
        logger.warning("Scenario fallback used; pipeline_errors=%s", pipeline_errors)
    if _is_dev() and debug_error:
        logger.warning("Scenario fallback debug_error=%s", debug_error)

    out: dict[str, Any] = {
        "scenario_summary": scenario_summary,
        "detected_domain": "Property Law",
        "issue_type": issue_type,
        "simplified_explanation": simplified_explanation,
        "facts_identified": [],
        "missing_facts": [
            "Keep copies of relevant documents such as deeds, receipts, notices, and written communications.",
            "Clarify who holds possession and whether any mutation or revenue records have changed recently.",
            "Note whether any statutory notice period or forum (civil, consumer, RERA, rent authority) may apply once facts are clearer.",
        ],
        "rights_possibly_involved": [],
        "possible_remedies": [
            "Organize a chronological file of documents and messages related to the dispute.",
            "If possession, demolition, or record changes are imminent, consider urgent local legal advice.",
        ],
        "possible_outcomes": [],
        "reasoning_trace": [],
        "source_pack_used": issue_type,
        "official_sources_referenced": deepcopy(refs) if refs else [],
        "source_grounding_status": (
            "Limited: curated statutory summaries from the selected pack were considered, "
            "but automated structuring was incomplete. Section-level verification remains pending."
        ),
        "consult_lawyer_warning": False,
        "warning_reason": "",
        "confidence": "Medium",
        "disclaimer": RESPONSE_SCHEMA["disclaimer"],
    }
    if _is_dev() and debug_error:
        out["debug_error"] = debug_error
    if _is_dev() and pipeline_errors:
        out["gemini_debug"] = " | ".join(pipeline_errors)
    return out


def _compose_first_assistant_message(compact_view: dict[str, Any], questions: list[str]) -> str:
    first = ""
    for q in questions:
        q = str(q).strip()
        if q:
            first = q
            break
    if not first:
        first = "What documents do you currently have related to this issue?"
    lead = first[:1].lower() + first[1:] if first else ""
    return f"I'll help narrow this down step by step. First, {lead}"


def _persist_and_build_analyze_payload(
    *,
    session_id: str,
    scenario: str,
    user_context: dict[str, Any],
    classification: dict[str, Any],
    issue_type: str,
    source_pack: dict[str, Any],
    full_report: dict[str, Any],
    safety: dict[str, Any],
    include_full_report_debug: bool = False,
) -> dict[str, Any]:
    full_report = _sanitize_full_report_dict(full_report)
    full_report["official_sources_referenced"] = _official_refs_from_pack(source_pack)
    full_report["source_pack_used"] = issue_type
    _adjust_confidence(full_report)

    detected_label = _detected_issue_label(issue_type, source_pack)
    compact_view = build_compact_view(
        full_report,
        detected_issue_label=detected_label,
        safety_result=safety,
        original_scenario=scenario,
    )
    suggested = build_initial_follow_up_questions(issue_type, full_report, source_pack)

    stored_report = _strip_internal_for_storage(full_report)

    official_snapshot = _official_refs_from_pack(source_pack)

    repo.create_session(
        session_id=session_id,
        original_scenario=scenario,
        user_context=user_context,
        issue_type=str(full_report.get("issue_type") or issue_type),
        detected_domain=str(full_report.get("detected_domain") or ""),
        source_pack_used=issue_type,
        confidence=str(full_report.get("confidence") or ""),
        consult_lawyer_warning=bool(full_report.get("consult_lawyer_warning")),
        warning_reason=str(full_report.get("warning_reason") or ""),
        source_grounding_status=str(full_report.get("source_grounding_status") or ""),
        classification_debug=classification,
    )

    repo.save_report(
        session_id=session_id,
        compact_view=compact_view,
        full_report=stored_report,
        suggested_follow_up_questions=suggested,
        official_sources=official_snapshot,
    )

    first_msg = _compose_first_assistant_message(compact_view, suggested)
    repo.add_chat_message(
        session_id,
        "assistant",
        first_msg,
        message_json={"kind": "analyze_opening", "compact_view": compact_view, "questions": suggested},
    )

    payload: dict[str, Any] = {
        "session_id": session_id,
        "issue_type": issue_type,
        "compact_view": compact_view,
        "suggested_follow_up_questions": suggested,
        "full_report_available": True,
    }
    if _is_dev() and include_full_report_debug:
        payload["full_report"] = stored_report
    return payload


def _run_gemini_full_report(
    text: str,
    uc: dict[str, Any],
    source_pack: dict[str, Any],
    safety: dict[str, Any],
    issue_type: str,
) -> dict[str, Any]:
    system_prompt, user_prompt = build_scenario_prompt(text, uc, source_pack, RESPONSE_SCHEMA)
    pipeline_errors: list[str] = []
    parsed: dict[str, Any] | None = None
    try:
        if _is_dev():
            logger.info("Calling Gemini (model=%s)...", settings.GEMINI_MODEL)
        raw = call_gemini(system_prompt, user_prompt, temperature=0.2, max_output_tokens=2048)
        if _is_dev():
            preview = raw[:500] + ("…" if len(raw) > 500 else "")
            logger.debug("Gemini raw response (first 500 chars): %s", preview)
        try:
            parsed = extract_json_from_text(raw)
        except ValueError as pe:
            pipeline_errors.append(f"JSON parse: {pe}")
            parsed = None
    except Exception as e:
        pipeline_errors.append(f"Gemini: {type(e).__name__}: {e}")
        parsed = None

    if parsed is None:
        response = _fallback_full_report(
            issue_type,
            source_pack,
            user_scenario=text,
            pipeline_errors=pipeline_errors or None,
        )
    else:
        response = parsed

    try:
        response = apply_safety_override(response, safety)
        response = ensure_required_fields(response, RESPONSE_SCHEMA)
    except Exception as e:
        logger.exception("post-process failed: %s", e)
        response = _fallback_full_report(
            issue_type,
            source_pack,
            user_scenario=text,
            pipeline_errors=pipeline_errors + [f"post-process: {e}"],
            debug_error=str(e),
        )

    return _sanitize_full_report_dict(response)


def analyze_scenario(
    scenario: str,
    user_context: dict[str, Any] | None = None,
    *,
    include_full_report_debug: bool = False,
) -> dict[str, Any]:
    """
    Stage 1: full report via Gemini, persist to SQLite, return compact API payload.
    On unexpected failure, still returns a valid analyze-shaped dict when possible.
    """
    session_id = str(uuid.uuid4())
    text = (scenario or "").strip()
    uc = _normalize_user_context(user_context)

    try:
        if len(text) < 10:
            classification = classify_scenario(text or "x")
            issue_type = classification["issue_type"]
            sp = load_source_pack(issue_type)
            safety = detect_safety_risk(text, sp)
            fr = _fallback_full_report(
                issue_type,
                sp,
                user_scenario=text,
                debug_error="Scenario must be at least 10 characters.",
            )
            fr = apply_safety_override(fr, safety)
            fr = ensure_required_fields(fr, RESPONSE_SCHEMA)
            return _persist_and_build_analyze_payload(
                session_id=session_id,
                scenario=text,
                user_context=uc,
                classification=classification,
                issue_type=issue_type,
                source_pack=sp,
                full_report=fr,
                safety=safety,
                include_full_report_debug=include_full_report_debug,
            )

        classification = classify_scenario(text)
        issue_type = classification["issue_type"]
        source_pack = load_source_pack(issue_type)
        safety = detect_safety_risk(text, source_pack)

        full_report = _run_gemini_full_report(text, uc, source_pack, safety, issue_type)

        return _persist_and_build_analyze_payload(
            session_id=session_id,
            scenario=text,
            user_context=uc,
            classification=classification,
            issue_type=issue_type,
            source_pack=source_pack,
            full_report=full_report,
            safety=safety,
            include_full_report_debug=include_full_report_debug,
        )
    except Exception as e:
        logger.exception("analyze_scenario fatal: %s", e)
        try:
            classification = classify_scenario(text or "property dispute")
            issue_type = classification["issue_type"]
            sp = load_source_pack(issue_type)
            safety = detect_safety_risk(text, sp)
            fr = _fallback_full_report(
                issue_type,
                sp,
                user_scenario=text,
                pipeline_errors=[f"{type(e).__name__}: {e}"],
                debug_error=str(e),
            )
            fr = apply_safety_override(fr, safety)
            fr = ensure_required_fields(fr, RESPONSE_SCHEMA)
            return _persist_and_build_analyze_payload(
                session_id=session_id,
                scenario=text,
                user_context=uc,
                classification=classification,
                issue_type=issue_type,
                source_pack=sp,
                full_report=fr,
                safety=safety,
                include_full_report_debug=include_full_report_debug,
            )
        except Exception as e2:
            logger.exception("analyze_scenario emergency failed: %s", e2)
            return {
                "session_id": session_id,
                "issue_type": "sale_deed_dispute",
                "compact_view": {
                    "detected_issue": "Property / legal issue",
                    "short_summary": (
                        "The analyzer hit an unexpected error. Please try again or consult a lawyer if urgent."
                    ),
                    "main_points": ["The system could not complete analysis."],
                    "recommended_next_steps": [
                        "Retry with a clearer description.",
                        "Consult a qualified local lawyer if the matter is urgent.",
                    ],
                    "lawyer_warning": {
                        "required": True,
                        "reason": "Analysis could not be completed safely.",
                    },
                    "confidence": "Low",
                    "disclaimer": RESPONSE_SCHEMA["disclaimer"],
                },
                "suggested_follow_up_questions": [
                    "What documents do you currently have?",
                    "Who is currently in possession?",
                    "Has any notice or court process happened?",
                ],
                "full_report_available": False,
            }
