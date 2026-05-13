"""Text parsing helpers for model outputs."""

from __future__ import annotations

import re
from typing import Any


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _extract_score(text: str) -> int | None:
    patterns = [
        r"(?:strength\s*score|rating|score)\s*[:=\-]?\s*(\d{1,3})\s*(?:/100|%)?",
        r"(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*%",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                continue
    return None


def _strip_bullet(line: str) -> str:
    cleaned = re.sub(r"^[\-\*\u2022\u25cf\d\.\)\]]+\s*", "", line.strip())
    return cleaned.strip()


def _split_sections(text: str) -> dict[str, list[str]]:
    """Split body into lists keyed by coarse section names."""
    keyword_map: list[tuple[str, str]] = [
        ("objections", r"objections?"),
        ("evidentiary_gaps", r"evidentiary\s+gaps?"),
        ("procedural_issues", r"procedural\s+issues?"),
        ("burden_of_proof_issues", r"(?:burden\s+of\s+proof|onus)[^\n]*"),
        ("contradictions", r"contradictions?"),
        ("improvement_suggestions", r"(?:improvement|suggestions?|recommendations?)"),
    ]

    lines = [ln.rstrip() for ln in text.splitlines()]
    buckets: dict[str, list[str]] = {key: [] for key, _ in keyword_map}
    current: str | None = None

    heading_re = re.compile(r"^\s*(#+)\s*(.+)$|^\s*(.+):\s*$")

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        heading_match = heading_re.match(raw)
        if heading_match:
            title = heading_match.group(2) or heading_match.group(3) or ""
            title_norm = title.strip().lower()
            matched_key: str | None = None
            for key, pat in keyword_map:
                if re.search(pat, title_norm, flags=re.IGNORECASE):
                    matched_key = key
                    break
            if matched_key:
                current = matched_key
                continue

        assigned = False
        lower = line.lower()
        for key, pat in keyword_map:
            if re.match(rf"^\s*{pat}\s*:\s*", lower, flags=re.IGNORECASE):
                current = key
                remainder = re.split(r":", line, maxsplit=1)
                if len(remainder) == 2 and remainder[1].strip():
                    item = _strip_bullet(remainder[1])
                    if item:
                        buckets[key].append(item)
                assigned = True
                break
        if assigned:
            continue

        if current:
            item = _strip_bullet(line)
            if item:
                buckets[current].append(item)

    return buckets


def parse_objection_evaluation(text: str) -> dict[str, Any]:
    """
    Best-effort structured parse of evaluator model output.

    Never raises; always returns the required keys with safe defaults.
    """
    raw = text or ""
    result: dict[str, Any] = {
        "summary": "",
        "objections": [],
        "evidentiary_gaps": [],
        "procedural_issues": [],
        "burden_of_proof_issues": [],
        "contradictions": [],
        "improvement_suggestions": [],
        "argument_strength_score": 50,
        "raw_response": raw,
    }

    try:
        score = _extract_score(raw)
        if score is not None:
            result["argument_strength_score"] = _clamp_score(score)

        sections = _split_sections(raw)
        for key in [
            "objections",
            "evidentiary_gaps",
            "procedural_issues",
            "burden_of_proof_issues",
            "contradictions",
            "improvement_suggestions",
        ]:
            cleaned = [item for item in sections.get(key, []) if item]
            if cleaned:
                result[key] = cleaned

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        if paragraphs:
            first = paragraphs[0].splitlines()
            summary_line = first[0].strip() if first else paragraphs[0]
            result["summary"] = summary_line[:2000]

        if not result["summary"]:
            stripped_lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if stripped_lines:
                result["summary"] = stripped_lines[0][:2000]

        if score is None:
            fallback = _extract_score(result["summary"] or "")
            if fallback is not None:
                result["argument_strength_score"] = _clamp_score(fallback)

    except Exception:  # noqa: BLE001 — parser must never crash
        result["summary"] = (raw.splitlines()[0] if raw.splitlines() else "")[:2000]

    return result
