"""Format stored full report for API responses (citizen-friendly labels)."""

from __future__ import annotations

import copy
import re
from typing import Any

_TRACE_DENY = re.compile(
    r"fallback response generated|gemini/parse attempts failed|could not be parsed|"
    r"api call failed|debug_error|structured api output",
    re.IGNORECASE,
)

_EXPL_DENY = re.compile(
    r"the system could not fully analyze|could not process|could not fully verify",
    re.IGNORECASE,
)


def _scrub_reasoning_trace(val: Any) -> list[str]:
    if not isinstance(val, list):
        return []
    out: list[str] = []
    for x in val:
        s = str(x).strip()
        if not s or _TRACE_DENY.search(s):
            continue
        out.append(s)
    return out


def _scrub_text(val: Any, deny: re.Pattern[str]) -> str:
    s = str(val or "").strip()
    if not s or deny.search(s):
        return ""
    return s


def format_full_report_for_client(full_report: dict[str, Any]) -> dict[str, Any]:
    """Citizen-safe shaping: refs, reasoning trace, and noisy explanations."""
    out = copy.deepcopy(full_report)
    for k in ("debug_error", "gemini_debug", "classification_debug"):
        out.pop(k, None)

    refs = out.get("official_sources_referenced")
    if isinstance(refs, list):
        new_refs: list[dict[str, Any]] = []
        for item in refs:
            if not isinstance(item, dict):
                continue
            d = dict(item)
            if d.get("verified") is False:
                d["section_verification"] = "Exact section-level verification pending"
                d.pop("verified", None)
            new_refs.append(d)
        out["official_sources_referenced"] = new_refs

    out["reasoning_trace"] = _scrub_reasoning_trace(out.get("reasoning_trace"))

    se = _scrub_text(out.get("simplified_explanation"), _EXPL_DENY)
    if se:
        out["simplified_explanation"] = se
    else:
        out["simplified_explanation"] = ""

    ss = _scrub_text(out.get("scenario_summary"), _EXPL_DENY)
    if ss:
        out["scenario_summary"] = ss
    elif not str(out.get("scenario_summary") or "").strip():
        out["scenario_summary"] = ""

    return out
