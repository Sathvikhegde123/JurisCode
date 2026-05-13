"""Pydantic schemas for objection / weakness evaluation."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ObjectionEvaluateRequest(BaseModel):
    session_id: Optional[str] = None
    premise: Optional[str] = None
    user_argument: str
    max_new_tokens: Optional[int] = Field(default=350, ge=16, le=4096)
    temperature: Optional[float] = Field(default=0.4, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.85, ge=0.0, le=1.0)


class ObjectionEvaluateResponse(BaseModel):
    summary: str
    objections: List[str]
    evidentiary_gaps: List[str]
    procedural_issues: List[str]
    burden_of_proof_issues: List[str]
    contradictions: List[str]
    improvement_suggestions: List[str]
    argument_strength_score: int
    raw_response: str
