"""Pydantic schemas for practice sessions."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PracticeStartRequest(BaseModel):
    topic: Optional[str] = None
    mode: Optional[str] = None
    randomize: bool = True


class PracticeStartResponse(BaseModel):
    session_id: str
    topic: str
    mode: str
    premise: str


class PracticeArgumentRequest(BaseModel):
    session_id: str
    user_argument: str


class PracticeArgumentResponse(BaseModel):
    session_id: str
    premise: str
    user_argument: str
    opposing_response: str
    objection_feedback: dict


class SessionDetailsResponse(BaseModel):
    session_id: str
    topic: str
    mode: str
    premise: str
    history: List[Any]
    created_at: str
    updated_at: str
