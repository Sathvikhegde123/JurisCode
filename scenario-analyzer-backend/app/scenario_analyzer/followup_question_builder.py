"""Initial Socratic follow-up questions after analyze."""

from __future__ import annotations

import re
from typing import Any

_ISSUE_DEFAULT_QUESTIONS: dict[str, list[str]] = {
    "tenant_eviction": [
        "Is your rental agreement written or oral?",
        "Has the landlord given written notice?",
        "Is there any unpaid rent or alleged breach?",
        "Has there been any force, threat, or lockout?",
    ],
    "mutation_vs_title": [
        "Whose name is currently in the mutation or revenue records?",
        "What title document do you have?",
        "Was mutation changed after notice to affected parties?",
        "Who is currently in possession?",
    ],
    "sale_deed_dispute": [
        "Do you have a registered sale deed?",
        "Did the seller have previous title documents?",
        "Who is currently in possession?",
        "Is there any allegation of fraud, forgery, or prior sale?",
    ],
    "rera_delay": [
        "What was the promised possession date?",
        "Is the project registered under RERA?",
        "How much payment has been made?",
        "Has the builder given any written reason for delay?",
    ],
    "partition_ancestral_property": [
        "Who originally owned the property?",
        "Did that person leave a will?",
        "Did your uncle sell the entire property or only his share?",
        "Has the buyer taken possession or changed mutation records?",
    ],
}


def _fact_to_question(fact: str) -> str:
    s = str(fact).strip()
    if not s:
        return ""
    if s.endswith("?"):
        return s
    if re.match(r"^(is|are|was|were|do|does|did|has|have|can|could|would)\b", s, re.I):
        return s[0].upper() + s[1:] if s else s
    return s[0].upper() + s[1:] + "?" if s else ""


def build_initial_follow_up_questions(
    issue_type: str, full_report: dict[str, Any], source_pack: dict[str, Any]
) -> list[str]:
    """Up to 4 questions: issue-specific, then missing_facts / common_missing_facts."""
    out: list[str] = []

    for q in _ISSUE_DEFAULT_QUESTIONS.get(issue_type, []):
        if q not in out:
            out.append(q)
        if len(out) >= 4:
            return out[:4]

    missing = full_report.get("missing_facts") or []
    if isinstance(missing, list):
        for m in missing:
            qq = _fact_to_question(m)
            if qq and qq not in out:
                out.append(qq)
            if len(out) >= 4:
                return out[:4]

    common = source_pack.get("common_missing_facts") or []
    if isinstance(common, list):
        for c in common:
            qq = _fact_to_question(c)
            if qq and qq not in out:
                out.append(qq)
            if len(out) >= 4:
                return out[:4]

    while len(out) < 4:
        filler = [
            "What documents do you currently have?",
            "Who is currently in possession?",
            "Has any notice, agreement, or court process happened?",
            "Which state is the property located in?",
        ]
        for f in filler:
            if f not in out:
                out.append(f)
            if len(out) >= 4:
                break

    return out[:4]
