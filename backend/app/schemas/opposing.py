"""Pydantic schemas for opposing counsel."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OpposingChallengeRequest(BaseModel):
    session_id: Optional[str] = None
    premise: Optional[str] = None
    user_argument: str
    max_new_tokens: Optional[int] = Field(default=300, ge=16, le=4096)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)


class OpposingChallengeResponse(BaseModel):
    opposing_response: str
    metadata: dict
