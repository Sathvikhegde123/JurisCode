"""Pydantic schemas for premise generation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

TOPICS: list[str] = [
    "title dispute",
    "adverse possession",
    "partition suit",
    "coparcenary dispute",
    "forged sale deed",
    "mutation dispute",
    "boundary dispute",
    "encroachment",
    "inheritance dispute",
    "family settlement",
    "gift deed challenge",
    "tenant eviction",
    "builder possession delay",
    "RERA complaint",
    "specific performance",
    "injunction dispute",
    "landlord tenant conflict",
    "revenue record dispute",
    "fraudulent transfer",
    "easement rights",
]

GENERATION_MODES: list[str] = [
    "clean law-school style hypotheticals",
    "messy real-world property disputes",
    "highly ambiguous ownership conflicts",
    "document-heavy evidentiary disputes",
    "family inheritance conflicts",
    "emotionally tense family property fights",
    "oral agreement disputes",
    "weak documentation cases",
    "contradictory timeline disputes",
    "tenant possession ambiguity disputes",
]


class TopicsResponse(BaseModel):
    topics: list[str]


class ModesResponse(BaseModel):
    modes: list[str]


class PremiseGenerateRequest(BaseModel):
    topic: Optional[str] = None
    mode: Optional[str] = None
    randomize: bool = False
    max_new_tokens: Optional[int] = Field(default=300, ge=16, le=4096)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)


class PremiseGenerateResponse(BaseModel):
    session_id: str
    topic: str
    mode: str
    premise: str
    metadata: dict
