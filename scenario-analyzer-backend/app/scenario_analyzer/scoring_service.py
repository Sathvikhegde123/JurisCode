"""Legal Clarity Score: Gemini + deterministic fallback + normalization."""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from typing import Any

from app.repositories import scenario_repository as repo
from app.scenario_analyzer.gemini_client import call_gemini
from app.scenario_analyzer.response_parser import extract_json_from_text
from app.scenario_analyzer.scoring_prompt_builder import (
    build_scoring_system_prompt,
    build_scoring_user_prompt,
)

logger = logging.getLogger(__name__)

DEFAULT_TEACHER = (
    "This score measures how clearly the scenario was clarified through the conversation. "
    "It does not measure legal correctness or predict legal outcome."
)

KNOWN_ISSUE_TYPES = frozenset(
    {
        "partition_ancestral_property",
        "mutation_vs_title",
        "sale_deed_dispute",
        "rera_delay",
        "tenant_eviction",
    }
)

_UNSAFE_PATTERNS = [
    (re.compile(r"\bwinning chance\b", re.I), "clarity of facts"),
    (re.compile(r"\bcase strength\b", re.I), "clarity of understanding"),
    (re.compile(r"\blegal validity\b", re.I), "clarity of documents"),
    (re.compile(r"\blegal correctness\b", re.I), "clarity of understanding"),
    (re.compile(r"\bsuccess probability\b", re.I), "clarity of risk factors"),
    (re.compile(r"\bcourt success\b", re.I), "clarity of procedural context"),
    (re.compile(r"\blegally valid\b", re.I), "document clarity"),
]


def _sanitize_text(s: str) -> str:
    out = str(s or "")
    for pat, repl in _UNSAFE_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _as_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(round(float(v)))
    except (TypeError, ValueError):
        return default


def _clamp_int(v: Any, lo: int, hi: int) -> int:
    x = _as_int(v, lo)
    return max(lo, min(hi, x))


def _empty_sub_scores() -> dict[str, Any]:
    return {
        "issue_understanding": {
            "score": 0,
            "max_score": 25,
            "reason": "",
            "sub_scores": {
                "issue_category_detected": 0,
                "specific_sub_issue_detected": 0,
                "user_confirmed_or_refined_issue": 0,
            },
        },
        "fact_clarity": {
            "score": 0,
            "max_score": 30,
            "reason": "",
            "sub_scores": {
                "ownership_or_history_clarified": 0,
                "timeline_clarified": 0,
                "possession_clarified": 0,
                "parties_or_legal_heirs_clarified": 0,
                "current_dispute_trigger_clarified": 0,
            },
        },
        "document_clarity": {
            "score": 0,
            "max_score": 25,
            "reason": "",
            "sub_scores": {
                "core_document_mentioned": 0,
                "mutation_or_revenue_record_mentioned": 0,
                "receipt_or_payment_proof_mentioned": 0,
                "notice_complaint_or_court_papers_mentioned": 0,
                "missing_documents_identified": 0,
            },
        },
        "risk_clarity": {
            "score": 0,
            "max_score": 20,
            "reason": "",
            "sub_scores": {
                "urgency_detected": 0,
                "possession_or_dispossession_risk_clarified": 0,
                "fraud_forgery_or_mutation_change_clarified": 0,
                "lawyer_police_or_court_trigger_clarified": 0,
            },
        },
    }


def normalize_score_response(score_data: dict[str, Any]) -> dict[str, Any]:
    """Clamp sub-scores, recalc totals, derive clarity_level, sanitize wording."""
    out = dict(score_data or {})
    bd = out.get("score_breakdown")
    if not isinstance(bd, dict):
        bd = _empty_sub_scores()
    else:
        bd = deepcopy(bd)
        defaults = _empty_sub_scores()
        for cat, dflt in defaults.items():
            if cat not in bd or not isinstance(bd[cat], dict):
                bd[cat] = deepcopy(dflt)
                continue
            cur = bd[cat]
            for k, v in dflt.items():
                if k not in cur:
                    cur[k] = v
            subs = cur.get("sub_scores")
            if not isinstance(subs, dict):
                cur["sub_scores"] = deepcopy(dflt["sub_scores"])
            else:
                for sk, sv in dflt["sub_scores"].items():
                    if sk not in subs:
                        subs[sk] = sv

    # Clamp sub-scores
    iu = bd["issue_understanding"]["sub_scores"]
    iu["issue_category_detected"] = _clamp_int(iu.get("issue_category_detected"), 0, 15)
    iu["specific_sub_issue_detected"] = _clamp_int(iu.get("specific_sub_issue_detected"), 0, 5)
    iu["user_confirmed_or_refined_issue"] = _clamp_int(iu.get("user_confirmed_or_refined_issue"), 0, 5)
    bd["issue_understanding"]["score"] = _clamp_int(
        sum(
            [
                iu["issue_category_detected"],
                iu["specific_sub_issue_detected"],
                iu["user_confirmed_or_refined_issue"],
            ]
        ),
        0,
        25,
    )

    fc = bd["fact_clarity"]["sub_scores"]
    fc["ownership_or_history_clarified"] = _clamp_int(fc.get("ownership_or_history_clarified"), 0, 8)
    fc["timeline_clarified"] = _clamp_int(fc.get("timeline_clarified"), 0, 6)
    fc["possession_clarified"] = _clamp_int(fc.get("possession_clarified"), 0, 6)
    fc["parties_or_legal_heirs_clarified"] = _clamp_int(fc.get("parties_or_legal_heirs_clarified"), 0, 5)
    fc["current_dispute_trigger_clarified"] = _clamp_int(fc.get("current_dispute_trigger_clarified"), 0, 5)
    bd["fact_clarity"]["score"] = _clamp_int(
        sum(
            [
                fc["ownership_or_history_clarified"],
                fc["timeline_clarified"],
                fc["possession_clarified"],
                fc["parties_or_legal_heirs_clarified"],
                fc["current_dispute_trigger_clarified"],
            ]
        ),
        0,
        30,
    )

    dc = bd["document_clarity"]["sub_scores"]
    dc["core_document_mentioned"] = _clamp_int(dc.get("core_document_mentioned"), 0, 7)
    dc["mutation_or_revenue_record_mentioned"] = _clamp_int(dc.get("mutation_or_revenue_record_mentioned"), 0, 6)
    dc["receipt_or_payment_proof_mentioned"] = _clamp_int(dc.get("receipt_or_payment_proof_mentioned"), 0, 4)
    dc["notice_complaint_or_court_papers_mentioned"] = _clamp_int(
        dc.get("notice_complaint_or_court_papers_mentioned"), 0, 4
    )
    dc["missing_documents_identified"] = _clamp_int(dc.get("missing_documents_identified"), 0, 4)
    bd["document_clarity"]["score"] = _clamp_int(
        sum(
            [
                dc["core_document_mentioned"],
                dc["mutation_or_revenue_record_mentioned"],
                dc["receipt_or_payment_proof_mentioned"],
                dc["notice_complaint_or_court_papers_mentioned"],
                dc["missing_documents_identified"],
            ]
        ),
        0,
        25,
    )

    rc = bd["risk_clarity"]["sub_scores"]
    rc["urgency_detected"] = _clamp_int(rc.get("urgency_detected"), 0, 5)
    rc["possession_or_dispossession_risk_clarified"] = _clamp_int(
        rc.get("possession_or_dispossession_risk_clarified"), 0, 5
    )
    rc["fraud_forgery_or_mutation_change_clarified"] = _clamp_int(
        rc.get("fraud_forgery_or_mutation_change_clarified"), 0, 5
    )
    rc["lawyer_police_or_court_trigger_clarified"] = _clamp_int(
        rc.get("lawyer_police_or_court_trigger_clarified"), 0, 5
    )
    bd["risk_clarity"]["score"] = _clamp_int(
        sum(
            [
                rc["urgency_detected"],
                rc["possession_or_dispossession_risk_clarified"],
                rc["fraud_forgery_or_mutation_change_clarified"],
                rc["lawyer_police_or_court_trigger_clarified"],
            ]
        ),
        0,
        20,
    )

    for cat in ("issue_understanding", "fact_clarity", "document_clarity", "risk_clarity"):
        r = bd[cat].get("reason")
        bd[cat]["reason"] = _sanitize_text(str(r or ""))
        bd[cat]["max_score"] = int(_empty_sub_scores()[cat]["max_score"])

    total = (
        int(bd["issue_understanding"]["score"])
        + int(bd["fact_clarity"]["score"])
        + int(bd["document_clarity"]["score"])
        + int(bd["risk_clarity"]["score"])
    )
    total = max(0, min(100, total))

    if total <= 39:
        level = "Low Clarity"
    elif total <= 59:
        level = "Basic Clarity"
    elif total <= 79:
        level = "Good Clarity"
    else:
        level = "Strong Clarity"

    strengths = out.get("strengths")
    if not isinstance(strengths, list):
        strengths = []
    strengths = [_sanitize_text(str(x)) for x in strengths if x is not None and str(x).strip()]

    gaps = out.get("remaining_gaps")
    if not isinstance(gaps, list):
        gaps = []
    gaps = [_sanitize_text(str(x)) for x in gaps if x is not None and str(x).strip()]

    summary = _sanitize_text(str(out.get("summary_feedback") or ""))
    teacher = str(out.get("teacher_explanation") or "").strip() or DEFAULT_TEACHER
    teacher = _sanitize_text(teacher)

    return {
        "legal_clarity_score": total,
        "clarity_level": level,
        "score_breakdown": bd,
        "strengths": strengths,
        "remaining_gaps": gaps,
        "summary_feedback": summary,
        "teacher_explanation": teacher,
    }


def _text_has_any(text: str, phrases: list[str]) -> bool:
    t = text.lower()
    return any(p in t for p in phrases)


def fallback_score_session(
    session: dict[str, Any],
    full_report: dict[str, Any],
    chat_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rule-based clarity scoring when Gemini is unavailable or invalid."""
    scenario = str(session.get("original_scenario") or "")
    user_lines = [str(m.get("content") or "") for m in chat_history if m.get("role") == "user"]
    report_summary = str(full_report.get("scenario_summary") or full_report.get("simplified_explanation") or "")
    facts = full_report.get("facts_identified") or []
    missing = full_report.get("missing_facts") or []
    fact_blob = " ".join(str(x) for x in facts if x) if isinstance(facts, list) else ""
    miss_blob = " ".join(str(x) for x in missing if x) if isinstance(missing, list) else ""
    combined = " ".join([scenario, *user_lines, report_summary, fact_blob, miss_blob]).lower()

    issue_type = str(session.get("issue_type") or full_report.get("issue_type") or "").strip()
    if issue_type not in KNOWN_ISSUE_TYPES:
        issue_type = str(session.get("source_pack_used") or full_report.get("source_pack_used") or "").strip()

    # Issue understanding
    issue_cat = 0
    if issue_type in KNOWN_ISSUE_TYPES:
        issue_cat = 15
    elif _text_has_any(
        combined,
        ["partition", "ancestral", "mutation", "sale deed", "rera", "tenant", "landlord", "eviction"],
    ):
        issue_cat = 8

    sub_issue = 0
    if issue_type == "partition_ancestral_property" and _text_has_any(combined, ["uncle", "sold", "ancestral"]):
        sub_issue = 5
    elif issue_type == "mutation_vs_title" and _text_has_any(combined, ["mutation", "name changed", "buyer"]):
        sub_issue = 5
    elif issue_type == "sale_deed_dispute" and _text_has_any(combined, ["sale deed", "title", "dispute"]):
        sub_issue = 5
    elif issue_type == "rera_delay" and _text_has_any(combined, ["builder", "possession", "delay", "rera"]):
        sub_issue = 5
    elif issue_type == "tenant_eviction" and _text_has_any(combined, ["tenant", "landlord", "lease", "vacate"]):
        sub_issue = 5
    elif _text_has_any(combined, ["uncle", "sold", "mutation", "notice", "builder"]):
        sub_issue = 3

    user_refined = 0
    if _text_has_any(
        combined,
        [
            "no will",
            "grandfather",
            "grandmother",
            "confirmed",
            "yes ",
            "mutation",
            "notice",
            "possession",
            "still in possession",
            "delayed",
        ],
    ):
        user_refined = 5
    elif len(" ".join(user_lines).strip()) > 40:
        user_refined = 2

    own = 0
    if _text_has_any(
        combined,
        [
            "grandfather",
            "father",
            "mother",
            "inherited",
            "ancestral",
            "self acquired",
            "original owner",
            "seller",
            "buyer",
            "landlord",
            "tenant",
            "builder",
        ],
    ):
        own = 6 if _text_has_any(combined, ["ancestral", "inherit", "will", "legal heir"]) else 4

    timeline = 0
    if _text_has_any(
        combined,
        ["year", "date", "ago", "before", "after", "delayed", "two years", "possession date", "lease ended"],
    ):
        timeline = 4 if _text_has_any(combined, ["20", "month", "week"]) else 3

    possession = 0
    if _text_has_any(
        combined,
        [
            "possession",
            "occupying",
            "living",
            "using",
            "cultivating",
            "locked",
            "lockout",
            "in possession",
        ],
    ):
        possession = 5

    parties = 0
    if _text_has_any(
        combined,
        [
            "legal heir",
            "family tree",
            "brother",
            "sister",
            "uncle",
            "buyer",
            "seller",
            "landlord",
            "tenant",
            "builder",
        ],
    ):
        parties = 4

    trigger = 0
    if _text_has_any(
        combined,
        [
            "sold without",
            "mutation",
            "delayed possession",
            "forcing",
            "vacate",
            "title",
            "refund",
            "dispute",
        ],
    ):
        trigger = 4

    core_doc = 0
    if _text_has_any(
        combined,
        [
            "sale deed",
            "gift deed",
            "will",
            "agreement",
            "rental agreement",
            "lease deed",
            "builder buyer",
            "allotment letter",
        ],
    ):
        core_doc = 5 if _text_has_any(combined, ["registered", "deed", "agreement"]) else 4

    mut = 0
    if _text_has_any(
        combined,
        ["mutation", "khata", "patta", "rtc", "revenue record", "record of rights", "property records"],
    ):
        mut = 5

    receipt = 0
    if _text_has_any(
        combined,
        ["tax receipt", "rent receipt", "payment receipt", "bank transfer", "payment proof", "emi", "paid"],
    ):
        receipt = 3

    notice = 0
    if _text_has_any(combined, ["notice", "complaint", "court", "fir", "police", "rera complaint"]):
        notice = 3

    miss_docs = 0
    if isinstance(missing, list) and len([x for x in missing if str(x).strip()]) >= 2:
        miss_docs = 4
    elif isinstance(missing, list) and missing:
        miss_docs = 2
    elif "missing" in combined and ("document" in combined or "deed" in combined):
        miss_docs = 2

    urgency = 0
    if _text_has_any(combined, ["urgent", "immediate", "today", "tomorrow", "evict", "lockout", "police"]):
        urgency = 4

    disp = 0
    if _text_has_any(
        combined,
        ["possession", "dispossession", "lockout", "vacate", "still in possession", "not in possession"],
    ):
        disp = 4

    fraud = 0
    if _text_has_any(combined, ["fraud", "forged", "fake", "mutation", "name changed", "signature"]):
        fraud = 4

    legal_trig = 0
    if _text_has_any(combined, ["lawyer", "advocate", "police", "fir", "court", "case", "notice", "complaint"]):
        legal_trig = 4

    raw = {
        "legal_clarity_score": 0,
        "clarity_level": "",
        "score_breakdown": {
            "issue_understanding": {
                "score": 0,
                "max_score": 25,
                "reason": "Fallback: issue signals from scenario, classification, and user replies.",
                "sub_scores": {
                    "issue_category_detected": issue_cat,
                    "specific_sub_issue_detected": sub_issue,
                    "user_confirmed_or_refined_issue": user_refined,
                },
            },
            "fact_clarity": {
                "score": 0,
                "max_score": 30,
                "reason": "Fallback: keyword signals for ownership, timeline, possession, parties, and trigger.",
                "sub_scores": {
                    "ownership_or_history_clarified": own,
                    "timeline_clarified": timeline,
                    "possession_clarified": possession,
                    "parties_or_legal_heirs_clarified": parties,
                    "current_dispute_trigger_clarified": trigger,
                },
            },
            "document_clarity": {
                "score": 0,
                "max_score": 25,
                "reason": "Fallback: document and evidence keywords plus missing-fact hints from the report.",
                "sub_scores": {
                    "core_document_mentioned": core_doc,
                    "mutation_or_revenue_record_mentioned": mut,
                    "receipt_or_payment_proof_mentioned": receipt,
                    "notice_complaint_or_court_papers_mentioned": notice,
                    "missing_documents_identified": miss_docs,
                },
            },
            "risk_clarity": {
                "score": 0,
                "max_score": 20,
                "reason": "Fallback: urgency, possession risk, fraud/mutation, and legal/police triggers.",
                "sub_scores": {
                    "urgency_detected": urgency,
                    "possession_or_dispossession_risk_clarified": disp,
                    "fraud_forgery_or_mutation_change_clarified": fraud,
                    "lawyer_police_or_court_trigger_clarified": legal_trig,
                },
            },
        },
        "strengths": [],
        "remaining_gaps": [],
        "summary_feedback": "",
        "teacher_explanation": DEFAULT_TEACHER,
    }

    norm = normalize_score_response(raw)
    norm = _enforce_fallback_strong_cap(norm)

    # Strengths / gaps narrative
    strengths: list[str] = []
    if issue_cat >= 12:
        strengths.append("Issue category is recognizable from the scenario or classification.")
    if own >= 4:
        strengths.append("Some ownership or background facts appear in the conversation.")
    if core_doc + mut + receipt >= 6:
        strengths.append("Useful documents or record types were mentioned.")
    if possession + disp >= 6:
        strengths.append("Possession or dispossession risk factors were partially clarified.")

    gaps: list[str] = []
    if norm["score_breakdown"]["fact_clarity"]["score"] < 15:
        gaps.append("Key facts (timeline, parties, trigger) could be explained more concretely.")
    if norm["score_breakdown"]["document_clarity"]["score"] < 10:
        gaps.append("Documents and evidence mentioned or missing could be spelled out more clearly.")
    if norm["score_breakdown"]["risk_clarity"]["score"] < 8:
        gaps.append("Urgency and risk-factor context is still thin or generic.")

    norm["strengths"] = strengths[:8]
    norm["remaining_gaps"] = gaps[:8]
    total = norm["legal_clarity_score"]
    norm["summary_feedback"] = (
        "This is a clarity-focused estimate based on keyword signals in your text. "
        "Add short, concrete answers about facts, documents, and what happened next to improve clarity."
        if total < 60
        else "The conversation shows moderate clarity; tightening dates, parties, and documents would help further."
    )
    return norm


def _enforce_fallback_strong_cap(norm: dict[str, Any]) -> dict[str, Any]:
    """
    Fallback-only guard: avoid Strong Clarity when fact + document clarity is still thin.
    Adjusts sub-scores so totals stay consistent after normalize_score_response.
    """
    data = deepcopy(norm)
    bd = data["score_breakdown"]

    def _one_pass() -> dict[str, Any]:
        return normalize_score_response({**data, "score_breakdown": bd})

    for _ in range(40):
        cur = _one_pass()
        total = int(cur["legal_clarity_score"])
        fd = int(cur["score_breakdown"]["fact_clarity"]["score"]) + int(
            cur["score_breakdown"]["document_clarity"]["score"]
        )
        if total < 80 or fd >= 28:
            return cur

        order: list[tuple[str, str]] = [
            ("document_clarity", "receipt_or_payment_proof_mentioned"),
            ("document_clarity", "missing_documents_identified"),
            ("document_clarity", "notice_complaint_or_court_papers_mentioned"),
            ("document_clarity", "mutation_or_revenue_record_mentioned"),
            ("document_clarity", "core_document_mentioned"),
            ("fact_clarity", "timeline_clarified"),
            ("fact_clarity", "current_dispute_trigger_clarified"),
            ("fact_clarity", "parties_or_legal_heirs_clarified"),
            ("fact_clarity", "possession_clarified"),
            ("fact_clarity", "ownership_or_history_clarified"),
        ]
        decremented = False
        for cat, key in order:
            subs = bd[cat]["sub_scores"]
            if int(subs.get(key) or 0) > 0:
                subs[key] = int(subs[key]) - 1
                decremented = True
                break
        if not decremented:
            return cur

    return _one_pass()


def _split_chat(chat_history: list[dict[str, Any]]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    cleaned: list[dict[str, Any]] = []
    user_only: list[str] = []
    asst_only: list[str] = []
    for m in chat_history:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        cleaned.append({"role": role, "content": content})
        if role == "user" and content.strip():
            user_only.append(content.strip())
        if role == "assistant" and content.strip():
            asst_only.append(content.strip())
    return user_only, asst_only, cleaned


def generate_legal_clarity_score(session_id: str) -> dict[str, Any]:
    session = repo.get_session(session_id)
    if session is None:
        raise ValueError("session_not_found")
    report_row = repo.get_report(session_id)
    if report_row is None:
        raise ValueError("report_not_found")
    full_report = dict(report_row.get("full_report") or {})
    chat_history = repo.get_chat_history(session_id, limit=200)

    issue_type = str(session.get("issue_type") or full_report.get("issue_type") or "")
    source_pack = str(session.get("source_pack_used") or full_report.get("source_pack_used") or "")

    user_only, asst_only, cleaned = _split_chat(chat_history)

    system_p = build_scoring_system_prompt()
    user_p = build_scoring_user_prompt(
        original_scenario=str(session.get("original_scenario") or ""),
        issue_type=issue_type,
        source_pack_used=source_pack,
        full_report=full_report,
        chat_history=cleaned,
        user_messages_only=user_only,
        assistant_questions_only=asst_only,
    )

    parsed: dict[str, Any] | None = None
    try:
        raw_text = call_gemini(system_p, user_p, temperature=0.15, max_output_tokens=4096)
        parsed = extract_json_from_text(raw_text)
    except Exception as e:
        logger.warning("Gemini scoring failed, using fallback: %s", e)

    if parsed is None:
        final = fallback_score_session(session, full_report, chat_history)
    else:
        try:
            final = normalize_score_response(parsed)
        except Exception as e:
            logger.warning("Score normalization failed after Gemini, using fallback: %s", e)
            final = fallback_score_session(session, full_report, chat_history)

    to_save = {
        "legal_clarity_score": final["legal_clarity_score"],
        "clarity_level": final["clarity_level"],
        "score_breakdown": final["score_breakdown"],
        "strengths": final["strengths"],
        "remaining_gaps": final["remaining_gaps"],
        "summary_feedback": final["summary_feedback"],
        "teacher_explanation": final["teacher_explanation"],
    }
    repo.save_score(session_id, to_save)
    out = get_existing_legal_clarity_score(session_id)
    if out is None:
        raise RuntimeError("score_save_failed")
    return out


def get_existing_legal_clarity_score(session_id: str) -> dict[str, Any] | None:
    row = repo.get_score(session_id)
    if row is None:
        return None
    return {
        "session_id": row["session_id"],
        "legal_clarity_score": row["legal_clarity_score"],
        "clarity_level": row["clarity_level"],
        "score_breakdown": row["score_breakdown"],
        "strengths": row["strengths"],
        "remaining_gaps": row["remaining_gaps"],
        "summary_feedback": row["summary_feedback"],
        "teacher_explanation": row["teacher_explanation"],
    }
