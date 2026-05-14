import json
import logging
import re
from copy import deepcopy
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def _is_dev() -> bool:
    return settings.APP_ENV.strip().lower() == "development"


def _extract_balanced_json_object(s: str) -> str | None:
    """Return first top-level {...} substring with balanced braces (string-aware)."""
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _try_raw_decode_first_object(text: str) -> dict[str, Any] | None:
    """
    Parse a JSON object from text, allowing trailing garbage after a valid object.
    Tries raw_decode from successive '{' positions so a stray brace in prose does not block the real JSON.
    """
    s = text.strip()
    dec = json.JSONDecoder()
    start_search = 0
    for _ in range(32):
        i = s.find("{", start_search)
        if i < 0:
            return None
        try:
            obj, _end = dec.raw_decode(s[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            start_search = i + 1
            continue
    return None


def _try_json_loads_candidates(raw: str) -> dict[str, Any]:
    """Try several shapes; return dict or raise ValueError."""
    text = raw.strip()
    if not text:
        raise ValueError("Empty model response; cannot parse JSON.")

    candidates: list[str] = []

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        candidates.append(fence.group(1).strip())

    candidates.append(text)

    balanced = _extract_balanced_json_object(text)
    if balanced:
        candidates.append(balanced)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        if snippet not in candidates:
            candidates.append(snippet)

    seen: set[str] = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    loose = _try_raw_decode_first_object(text)
    if loose is not None:
        return loose

    raise ValueError(
        "Could not parse JSON from model output (no valid object found after fences/brace scan)."
    )


def extract_json_from_text(text: str) -> dict[str, Any]:
    """
    Parse a JSON object from model output: plain JSON, ```json``` fences,
    or first balanced {...} / brace-delimited object with possible surrounding text.
    """
    try:
        return _try_json_loads_candidates(text)
    except ValueError:
        if _is_dev():
            preview = text.strip()[:1000]
            logger.debug("extract_json_from_text failed; first 1000 chars:\n%s", preview)
        raise


def ensure_required_fields(
    response: dict[str, Any], fallback_values: dict[str, Any]
) -> dict[str, Any]:
    out = dict(response)
    for key, default in fallback_values.items():
        if key not in out:
            out[key] = deepcopy(default) if isinstance(default, (dict, list)) else default
    return out


def ensure_chat_required_fields(response: dict[str, Any]) -> dict[str, Any]:
    """Guarantee all chat response keys exist with safe defaults (partial model JSON)."""
    return merge_chat_response_defaults(response)


def merge_chat_response_defaults(parsed: dict[str, Any]) -> dict[str, Any]:
    """
    Merge model output with safe defaults for optional / missing chat keys.
    Does not invent assistant_message text (caller may fill that).
    """
    from app.scenario_analyzer.schemas import CHAT_RESPONSE_SCHEMA

    base = deepcopy(CHAT_RESPONSE_SCHEMA)
    out = dict(parsed)

    if "assistant_message" not in out or out.get("assistant_message") is None:
        out["assistant_message"] = base["assistant_message"]
    else:
        out["assistant_message"] = str(out["assistant_message"])

    for list_key in ("updated_understanding", "next_follow_up_questions", "recommended_next_steps"):
        if list_key not in out or out[list_key] is None:
            out[list_key] = list(base[list_key])
        elif isinstance(out[list_key], list):
            out[list_key] = [str(x) for x in out[list_key] if x is not None]
        elif isinstance(out[list_key], str) and out[list_key].strip():
            out[list_key] = [out[list_key].strip()]
        else:
            out[list_key] = []

    lw = out.get("lawyer_warning")
    if not isinstance(lw, dict):
        out["lawyer_warning"] = deepcopy(base["lawyer_warning"])
    else:
        req = lw.get("required", False)
        out["lawyer_warning"] = {
            "required": bool(req) if isinstance(req, bool) else str(req).lower() in ("true", "1", "yes"),
            "reason": str(lw.get("reason") or ""),
        }

    if "disclaimer" not in out or not str(out.get("disclaimer") or "").strip():
        out["disclaimer"] = base["disclaimer"]
    else:
        out["disclaimer"] = str(out["disclaimer"])

    return out
