"""In-memory session store for practice flows."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionService:
    """Simple dict-backed sessions (replace with SQLite/PostgreSQL later)."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def create(self, topic: str, mode: str, premise: str) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = _utc_now_iso()
        session = {
            "session_id": session_id,
            "topic": topic,
            "mode": mode,
            "premise": premise,
            "history": [],
            "created_at": now,
            "updated_at": now,
        }
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> dict[str, Any] | None:
        return self._sessions.get(session_id)

    def add_argument(
        self,
        session_id: str,
        user_argument: str,
        opposing_response: str,
        objection_feedback: dict[str, Any],
    ) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        entry = {
            "user_argument": user_argument,
            "opposing_response": opposing_response,
            "objection_feedback": objection_feedback,
            "recorded_at": _utc_now_iso(),
        }
        session["history"].append(entry)
        session["updated_at"] = _utc_now_iso()
        return session

    def to_dict(self, session: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session["session_id"],
            "topic": session["topic"],
            "mode": session["mode"],
            "premise": session["premise"],
            "history": list(session["history"]),
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
        }


session_service = SessionService()
