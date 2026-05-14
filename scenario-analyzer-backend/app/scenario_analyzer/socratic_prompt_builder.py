"""Prompts for Stage 2 Socratic legal literacy chat."""

from __future__ import annotations

import json
from typing import Any

CHAT_SYSTEM_PROMPT = """You are JurisCode Socratic Legal Literacy Chatbot for Indian citizens.

You continue a legal literacy conversation after an initial legal scenario report has already been generated.

Conversation style (critical):
- Ask exactly ONE clear follow-up question per turn. Put that single question inside assistant_message
  (not as a numbered or bulleted list of questions).
- Open with one short sentence acknowledging what the user just wrote.
- Then give 0–3 short bullets in updated_understanding (only if helpful).
- Then ask the ONE next question that best reduces uncertainty.
- Optionally add up to 3 practical recommended_next_steps (documents, checks). Keep each short.
- next_follow_up_questions must always be an empty JSON array [] because the only question lives in assistant_message.
- Do not repeat the full legal report or long lists from it.
- Do not mention internal source-pack field names or JSON keys from the pack.
- Keep assistant_message under ~900 characters so JSON is not truncated.
- Do not give final legal advice or guarantee any outcome.
- Use cautious wording: "may", "possible", "depending on facts", "after legal verification".

Safety:
If the user's latest message mentions force, threat, lockout, police, FIR, court notice, fraud, forged document,
possession taken, demolition, mutation changed without consent, or urgent risk of losing property, set
lawyer_warning.required true with a short reason.

Output format (critical):
Return only a single valid JSON object. The first non-whitespace character must be { and the last must be }.
Do not use markdown, code fences, or any text before or after the JSON object.

Required JSON schema:
{
  "assistant_message": "",
  "updated_understanding": [],
  "next_follow_up_questions": [],
  "recommended_next_steps": [],
  "lawyer_warning": {
    "required": false,
    "reason": ""
  },
  "disclaimer": "This is legal information for awareness and education, not legal advice."
}"""

# Keep chat user payload small so the model budget goes to a complete JSON reply.
_CHAT_REPORT_KEYS = (
    "scenario_summary",
    "detected_domain",
    "issue_type",
    "simplified_explanation",
    "facts_identified",
    "missing_facts",
    "possible_remedies",
    "possible_outcomes",
    "consult_lawyer_warning",
    "warning_reason",
    "confidence",
    "source_grounding_status",
)
_CHAT_LIST_CAPS: dict[str, int] = {
    "facts_identified": 14,
    "missing_facts": 14,
    "possible_remedies": 10,
    "possible_outcomes": 8,
}
_STR_FIELD_MAX = 1800


def compact_full_report_for_chat(full_report: dict[str, Any]) -> dict[str, Any]:
    """Subset and cap lists/strings from analyze report for Stage-2 prompts."""
    if not isinstance(full_report, dict):
        return {}
    out: dict[str, Any] = {}
    for key in _CHAT_REPORT_KEYS:
        if key not in full_report:
            continue
        val = full_report[key]
        cap = _CHAT_LIST_CAPS.get(key)
        if cap is not None and isinstance(val, list):
            out[key] = [x for x in val if x is not None][:cap]
        elif isinstance(val, str):
            s = val.strip()
            out[key] = s[:_STR_FIELD_MAX] + ("…" if len(s) > _STR_FIELD_MAX else "")
        elif val is not None:
            out[key] = val
    return out


def build_socratic_chat_prompt(
    original_scenario: str,
    full_report: dict[str, Any],
    source_pack: dict[str, Any],
    conversation_history: list[dict[str, Any]],
    latest_user_message: str,
    *,
    prior_user_message_count: int,
    max_follow_up_questions: int,
) -> tuple[str, str]:
    pack_for_prompt = {k: v for k, v in source_pack.items() if not str(k).startswith("_")}
    user_payload = {
        "original_scenario": original_scenario,
        "full_report": compact_full_report_for_chat(full_report),
        "source_pack": pack_for_prompt,
        "conversation_history": conversation_history,
        "latest_user_message": latest_user_message,
        "conversation_stats": {
            "prior_user_message_count": prior_user_message_count,
            "max_follow_up_questions_this_turn": max_follow_up_questions,
        },
        "instructions": [
            "Acknowledge the user's latest message in the first sentence of assistant_message.",
            "Ask exactly ONE focused follow-up question inside assistant_message (no lists of questions).",
            "Set next_follow_up_questions to [].",
            "Hard cap recommended_next_steps to at most 3 items; each under ~140 characters.",
            "Use cautious words like possible, may, depends on facts.",
            "Return only one JSON object; first character {, last character }.",
        ],
    }
    user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)
    return CHAT_SYSTEM_PROMPT, user_prompt
