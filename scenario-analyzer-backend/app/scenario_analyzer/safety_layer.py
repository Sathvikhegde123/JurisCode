import re
from typing import Any

SAFETY_KEYWORDS = [
    "force",
    "threat",
    "lockout",
    "police",
    "fir",
    "arrest",
    "court notice",
    "eviction",
    "fraud",
    "forged",
    "fake",
    "demolition",
    "possession taken",
    "illegal possession",
    "builder fraud",
    "refund denied",
    "project abandoned",
    "sold without consent",
    "sealed",
    "threw my goods",
]

_DEFAULT_WARNING_REASON = (
    "The scenario contains urgent/high-risk facts such as force, fraud, court notice, "
    "or risk of losing possession. A qualified local lawyer should be consulted."
)


def _keyword_present(text: str, kw: str) -> bool:
    k = kw.lower().strip()
    if not k:
        return False
    if " " in k:
        return k in text
    return re.search(rf"\b{re.escape(k)}\b", text) is not None


def _normalize(text: str) -> str:
    return text.lower()


def detect_safety_risk(
    scenario: str, source_pack: dict[str, Any] | None = None
) -> dict[str, Any]:
    text = _normalize(scenario)
    matched: list[str] = []

    for kw in SAFETY_KEYWORDS:
        if _keyword_present(text, kw):
            matched.append(kw)

    triggers: list[str] = []
    if source_pack:
        triggers = list(source_pack.get("safety_triggers") or [])
        for t in triggers:
            if isinstance(t, str) and _keyword_present(text, t) and t not in matched:
                matched.append(t)

    consult = len(matched) > 0
    return {
        "consult_lawyer_warning": consult,
        "warning_reason": _DEFAULT_WARNING_REASON if consult else "",
        "matched_safety_keywords": matched,
    }


def apply_safety_override(response: dict[str, Any], safety_result: dict[str, Any]) -> dict[str, Any]:
    out = dict(response)
    if not safety_result.get("consult_lawyer_warning"):
        return out

    out["consult_lawyer_warning"] = True
    out["warning_reason"] = safety_result.get("warning_reason") or _DEFAULT_WARNING_REASON

    trace = list(out.get("reasoning_trace") or [])
    matched = safety_result.get("matched_safety_keywords") or []
    trace.append(
        f"Safety layer: consult_lawyer_warning set due to matched indicators: {', '.join(matched)}"
    )
    out["reasoning_trace"] = trace
    return out
