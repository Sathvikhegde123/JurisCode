"""SQLite persistence helpers for sessions, reports, and chat."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from app.database import session_scope
from app.db_models import ChatMessage, ScenarioReport, ScenarioSession

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
