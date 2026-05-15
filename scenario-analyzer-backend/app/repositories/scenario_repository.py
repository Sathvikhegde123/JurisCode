"""SQLite persistence helpers for sessions, reports, and chat."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from app.database import session_scope
from app.db_models import ChatMessage, ScenarioReport, ScenarioScore, ScenarioSession

logger = logging.getLogger(__name__)


def create_session(
    session_id: str,
    original_scenario: str,
    user_context: dict[str, Any],
    issue_type: str,
    detected_domain: str,
    source_pack_used: str,
    confidence: str,
    consult_lawyer_warning: bool,
    warning_reason: str,
    source_grounding_status: str,
    classification_debug: dict[str, Any] | None,
) -> None:
    uc = user_context or {}
    state = str(uc.get("state") or "Unknown")
    language = str(uc.get("language") or "English")
    debug_json = (
        json.dumps(classification_debug, ensure_ascii=False)
        if classification_debug is not None
        else None
    )

    with session_scope() as db:
        row = ScenarioSession(
            session_id=session_id,
            original_scenario=original_scenario,
            user_state=state,
            user_language=language,
            detected_domain=detected_domain or "",
            issue_type=issue_type or "",
            source_pack_used=source_pack_used or "",
            confidence=confidence or "",
            consult_lawyer_warning=bool(consult_lawyer_warning),
            warning_reason=warning_reason or None,
            source_grounding_status=source_grounding_status or None,
            classification_debug_json=debug_json,
        )
        db.add(row)


def save_report(
    session_id: str,
    compact_view: dict[str, Any],
    full_report: dict[str, Any],
    suggested_follow_up_questions: list[str],
    official_sources: list[Any],
) -> None:
    with session_scope() as db:
        row = ScenarioReport(
            session_id=session_id,
            compact_view_json=json.dumps(compact_view, ensure_ascii=False),
            full_report_json=json.dumps(full_report, ensure_ascii=False),
            suggested_follow_up_questions_json=json.dumps(
                suggested_follow_up_questions, ensure_ascii=False
            ),
            official_sources_json=json.dumps(official_sources, ensure_ascii=False),
        )
        db.add(row)


def get_session(session_id: str) -> dict[str, Any] | None:
    with session_scope() as db:
        r = db.execute(select(ScenarioSession).where(ScenarioSession.session_id == session_id))
        obj = r.scalar_one_or_none()
        if obj is None:
            return None
        debug = None
        if obj.classification_debug_json:
            try:
                debug = json.loads(obj.classification_debug_json)
            except json.JSONDecodeError:
                debug = None
        return {
            "session_id": obj.session_id,
            "original_scenario": obj.original_scenario,
            "user_state": obj.user_state,
            "user_language": obj.user_language,
            "detected_domain": obj.detected_domain,
            "issue_type": obj.issue_type,
            "source_pack_used": obj.source_pack_used,
            "confidence": obj.confidence,
            "consult_lawyer_warning": obj.consult_lawyer_warning,
            "warning_reason": obj.warning_reason or "",
            "source_grounding_status": obj.source_grounding_status or "",
            "classification_debug": debug,
            "created_at": obj.created_at.isoformat() if obj.created_at else "",
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else "",
        }


def get_report(session_id: str) -> dict[str, Any] | None:
    with session_scope() as db:
        r = db.execute(
            select(ScenarioReport)
            .where(ScenarioReport.session_id == session_id)
            .order_by(ScenarioReport.id.desc())
            .limit(1)
        )
        obj = r.scalar_one_or_none()
        if obj is None:
            return None
        return {
            "session_id": session_id,
            "compact_view": json.loads(obj.compact_view_json or "{}"),
            "full_report": json.loads(obj.full_report_json or "{}"),
            "suggested_follow_up_questions": json.loads(
                obj.suggested_follow_up_questions_json or "[]"
            ),
            "official_sources": json.loads(obj.official_sources_json or "[]"),
        }


def add_chat_message(
    session_id: str,
    role: str,
    content: str,
    message_json: dict[str, Any] | None = None,
) -> None:
    if role not in ("user", "assistant", "system"):
        raise ValueError(f"Invalid chat role: {role}")
    extra = json.dumps(message_json, ensure_ascii=False) if message_json is not None else None
    with session_scope() as db:
        db.add(
            ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                message_json=extra,
            )
        )


def get_chat_history(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with session_scope() as db:
        r = db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .limit(max(1, min(limit, 200)))
        )
        rows = r.scalars().all()
        out: list[dict[str, Any]] = []
        for m in rows:
            out.append(
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
            )
        return out


def save_score(session_id: str, score_data: dict[str, Any]) -> dict[str, Any]:
    """
    Insert or update Legal Clarity Score for a session.
    score_data keys: legal_clarity_score, clarity_level, score_breakdown,
    strengths, remaining_gaps, summary_feedback, teacher_explanation
    """
    total = int(score_data.get("legal_clarity_score") or score_data.get("total_score") or 0)
    clarity = str(score_data.get("clarity_level") or "")
    breakdown = score_data.get("score_breakdown") or {}
    strengths = score_data.get("strengths") or []
    gaps = score_data.get("remaining_gaps") or []
    summary = str(score_data.get("summary_feedback") or "")
    teacher = str(
        score_data.get("teacher_explanation")
        or "This score measures how clearly the scenario was clarified through the conversation. "
        "It does not measure legal correctness or predict legal outcome."
    )

    with session_scope() as db:
        r = db.execute(select(ScenarioScore).where(ScenarioScore.session_id == session_id))
        row = r.scalar_one_or_none()
        if row is None:
            row = ScenarioScore(
                session_id=session_id,
                total_score=total,
                clarity_level=clarity,
                score_breakdown_json=json.dumps(breakdown, ensure_ascii=False),
                strengths_json=json.dumps(strengths, ensure_ascii=False),
                remaining_gaps_json=json.dumps(gaps, ensure_ascii=False),
                summary_feedback=summary,
                teacher_explanation=teacher,
            )
            db.add(row)
        else:
            row.total_score = total
            row.clarity_level = clarity
            row.score_breakdown_json = json.dumps(breakdown, ensure_ascii=False)
            row.strengths_json = json.dumps(strengths, ensure_ascii=False)
            row.remaining_gaps_json = json.dumps(gaps, ensure_ascii=False)
            row.summary_feedback = summary
            row.teacher_explanation = teacher

    return get_score(session_id) or {}


def get_score(session_id: str) -> dict[str, Any] | None:
    with session_scope() as db:
        r = db.execute(select(ScenarioScore).where(ScenarioScore.session_id == session_id))
        obj = r.scalar_one_or_none()
        if obj is None:
            return None
        try:
            breakdown = json.loads(obj.score_breakdown_json or "{}")
        except json.JSONDecodeError:
            breakdown = {}
        try:
            strengths = json.loads(obj.strengths_json or "[]")
        except json.JSONDecodeError:
            strengths = []
        try:
            gaps = json.loads(obj.remaining_gaps_json or "[]")
        except json.JSONDecodeError:
            gaps = []
        if not isinstance(strengths, list):
            strengths = []
        if not isinstance(gaps, list):
            gaps = []
        return {
            "session_id": session_id,
            "legal_clarity_score": int(obj.total_score),
            "clarity_level": obj.clarity_level or "",
            "score_breakdown": breakdown if isinstance(breakdown, dict) else {},
            "strengths": [str(x) for x in strengths if x is not None],
            "remaining_gaps": [str(x) for x in gaps if x is not None],
            "summary_feedback": obj.summary_feedback or "",
            "teacher_explanation": obj.teacher_explanation or "",
            "created_at": obj.created_at.isoformat() if obj.created_at else "",
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else "",
        }


def list_recent_sessions(limit: int = 20) -> list[dict[str, Any]]:
    with session_scope() as db:
        r = db.execute(
            select(ScenarioSession)
            .order_by(ScenarioSession.created_at.desc())
            .limit(max(1, min(limit, 100)))
        )
        rows = r.scalars().all()
        return [
            {
                "session_id": s.session_id,
                "original_scenario": s.original_scenario,
                "issue_type": s.issue_type,
                "source_pack_used": s.source_pack_used,
                "created_at": s.created_at.isoformat() if s.created_at else "",
            }
            for s in rows
        ]
