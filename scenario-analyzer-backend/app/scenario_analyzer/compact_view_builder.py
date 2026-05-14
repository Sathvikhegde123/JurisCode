"""Build user-facing compact summary from full structured report."""

from __future__ import annotations

import re
from typing import Any

from app.scenario_analyzer.schemas import RESPONSE_SCHEMA

_GENERIC = re.compile(
    r"property-related legal issue|your situation may involve property|"
    r"appears to involve a property-related",
    re.IGNORECASE,
)


def _clip_sentences(text: str, max_sentences: int = 4) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    parts = [p.strip() for p in t.replace("?", ".").split(".") if p.strip()]
    if not parts:
        return t[:520]
    out: list[str] = []
    for p in parts[:max_sentences]:
        out.append(p if p.endswith(".") else p + ".")
    return " ".join(out).strip()


def _word_count(s: str) -> int:
    return len([w for w in (s or "").split() if w.strip()])


def _take_list(val: Any, cap: int) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None and str(x).strip()][:cap]
    if isinstance(val, str) and val.strip():
        return [val.strip()][:cap]
    return []


def _awareness_fallback_summary(original_scenario: str, detected_issue_label: str) -> str:
    snippet = (original_scenario or "").strip().replace("\n", " ")
    if len(snippet) > 480:
        snippet = snippet[:480] + "…"
    if not snippet:
        snippet = "the situation you described"
    msg = (
        f"This issue may require more details, but based on your input it appears related to "
        f"{detected_issue_label}. You wrote: {snippet}. "
        "The next step is to clarify key facts through follow-up questions rather than assuming outcomes."
    )
    if _word_count(msg) < 22:
        msg += (
            " JurisCode provides general legal awareness for education only and is not a substitute "
            "for advice from a qualified lawyer."
        )
    return msg


def build_compact_view(
    full_report: dict[str, Any],
    *,
    detected_issue_label: str,
    safety_result: dict[str, Any] | None = None,
    original_scenario: str | None = None,
) -> dict[str, Any]:
    """
    Compact view for UI: no reasoning_trace, sources, or internal fields.
    """
    summary_src = (
        full_report.get("scenario_summary")
        or full_report.get("simplified_explanation")
        or ""
    )
    short_summary = _clip_sentences(str(summary_src), 4)
    if _word_count(short_summary) < 15 or _GENERIC.search(short_summary):
        short_summary = _awareness_fallback_summary(
            str(original_scenario or "").strip(),
            detected_issue_label,
        )

    main_from = (
        _take_list(full_report.get("facts_identified"), 3)
        + _take_list(full_report.get("missing_facts"), 3)
        + _take_list(full_report.get("rights_possibly_involved"), 2)
    )
    main_points: list[str] = []
    for m in main_from:
        if m not in main_points:
            main_points.append(m)
        if len(main_points) >= 5:
            break
    if not main_points:
        expl = str(full_report.get("simplified_explanation") or "").strip()
        if expl and not _GENERIC.search(expl):
            main_points = _take_list([expl], 1)

    remedies = _take_list(full_report.get("possible_remedies"), 6)
    docs_hint = _take_list(full_report.get("missing_facts"), 4)
    next_steps: list[str] = []
    for x in remedies + docs_hint:
        if x not in next_steps:
            next_steps.append(x)
        if len(next_steps) >= 5:
            break

    consult = bool(full_report.get("consult_lawyer_warning"))
    reason = str(full_report.get("warning_reason") or "").strip()
    if safety_result and safety_result.get("consult_lawyer_warning"):
        consult = True
        reason = reason or str(safety_result.get("warning_reason") or "").strip()

    return {
        "detected_issue": detected_issue_label,
        "short_summary": short_summary or _awareness_fallback_summary(
            str(original_scenario or "").strip(),
            detected_issue_label,
        ),
        "main_points": main_points[:5],
        "recommended_next_steps": next_steps[:5],
        "lawyer_warning": {
            "required": consult,
            "reason": reason
            or (
                "Consult a qualified local lawyer if your rights, possession, or records may be affected."
                if consult
                else ""
            ),
        },
        "confidence": str(full_report.get("confidence") or "Medium"),
        "disclaimer": str(full_report.get("disclaimer") or RESPONSE_SCHEMA["disclaimer"]),
    }
