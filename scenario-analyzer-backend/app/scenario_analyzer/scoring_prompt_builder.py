"""System and user prompts for Legal Clarity Score (Gemini)."""

from __future__ import annotations

import json
from typing import Any

_SCORING_RUBRIC = """
Issue Understanding: 0–25
- Issue category detected: +15
- Specific sub-issue detected: +5
- User confirmed/refined issue: +5

Fact Clarity: 0–30
- Ownership/history clarified: +8
- Timeline clarified: +6
- Possession clarified: +6
- Parties/legal heirs clarified: +5
- Current dispute trigger clarified: +5

Document Clarity: 0–25
- Sale deed/gift deed/will/agreement mentioned: +7
- Mutation/revenue record mentioned: +6
- Tax/rent/payment receipts mentioned: +4
- Notice/complaint/court papers mentioned: +4
- Missing documents identified: +4

Risk Clarity: 0–20
- Urgency detected: +5
- Possession/risk of dispossession clarified: +5
- Fraud/forgery/mutation change clarified: +5
- Lawyer/police/court notice trigger clarified: +5
"""

_REQUIRED_JSON = """
Required JSON response:
{
  "legal_clarity_score": 0,
  "clarity_level": "",
  "score_breakdown": {
    "issue_understanding": {
      "score": 0,
      "max_score": 25,
      "reason": "",
      "sub_scores": {
        "issue_category_detected": 0,
        "specific_sub_issue_detected": 0,
        "user_confirmed_or_refined_issue": 0
      }
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
        "current_dispute_trigger_clarified": 0
      }
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
        "missing_documents_identified": 0
      }
    },
    "risk_clarity": {
      "score": 0,
      "max_score": 20,
      "reason": "",
      "sub_scores": {
        "urgency_detected": 0,
        "possession_or_dispossession_risk_clarified": 0,
        "fraud_forgery_or_mutation_change_clarified": 0,
        "lawyer_police_or_court_trigger_clarified": 0
      }
    }
  },
  "strengths": [],
  "remaining_gaps": [],
  "summary_feedback": "",
  "teacher_explanation": "This score measures how clearly the scenario was clarified through the conversation. It does not measure legal correctness or predict legal outcome."
}
"""


def build_scoring_system_prompt() -> str:
    return f"""You are evaluating a citizen legal-literacy conversation.

You are not judging legal correctness.
You are not predicting legal outcome.
You are not deciding whether the user is legally right or wrong.

Your job is to assign a Legal Clarity Score based only on how clearly the user's legal scenario was clarified through the Socratic conversation.

Score out of 100 using exactly four categories:
1. Issue Understanding — 25
2. Fact Clarity — 30
3. Document Clarity — 25
4. Risk Clarity — 20

Use the exact sub-score rubric.

Be balanced:
- Do not be too strict.
- Do not be too loose.
- Give partial credit.
- Reward relevant facts, documents, possession/risk clarity, and clear responses.
- Penalize vague, unrelated, or missing information.
- A short conversation can still receive Basic or Good Clarity if the key issue is clear.
- Do not give Strong Clarity unless facts/documents/risk are reasonably clarified.

Never use terms:
- winning chance
- case strength
- legal validity
- legal correctness
- success probability

Use terms:
- clarity
- understanding
- facts
- documents
- risk factors
- remaining gaps

Return only valid JSON.
The first character must be {{ and the last character must be }}.
Do not include markdown.

Include the scoring rubric in your reasoning (scores must follow it exactly):

{_SCORING_RUBRIC}

{_REQUIRED_JSON}
"""


def build_scoring_user_prompt(
    *,
    original_scenario: str,
    issue_type: str,
    source_pack_used: str,
    full_report: dict[str, Any],
    chat_history: list[dict[str, Any]],
    user_messages_only: list[str],
    assistant_questions_only: list[str],
) -> str:
    parts = [
        "Scoring instructions: Assign sub-scores per rubric, then set category scores as the sum of sub-scores.",
        "Provide concise reasons focused on clarity and understanding only.",
        "",
        f"original_scenario:\n{original_scenario.strip()}",
        "",
        f"detected issue_type:\n{issue_type or '(none)'}",
        "",
        f"source_pack_used:\n{source_pack_used or '(none)'}",
        "",
        "full_report (JSON):",
        json.dumps(full_report, ensure_ascii=False, indent=2),
        "",
        "chat_history (role, content):",
        json.dumps(chat_history, ensure_ascii=False, indent=2),
        "",
        "user_messages_only:",
        json.dumps(user_messages_only, ensure_ascii=False, indent=2),
        "",
        "assistant_questions_only:",
        json.dumps(assistant_questions_only, ensure_ascii=False, indent=2),
    ]
    return "\n".join(parts)
