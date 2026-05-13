"""Premise generation routes."""

from __future__ import annotations

import random

from fastapi import APIRouter, HTTPException

from app.schemas.premise import (
    GENERATION_MODES,
    TOPICS,
    ModesResponse,
    PremiseGenerateRequest,
    PremiseGenerateResponse,
    TopicsResponse,
)
from app.services.generation_service import generation_service
from app.services.session_service import session_service

router = APIRouter(prefix="/premise", tags=["premise"])


@router.get("/topics", response_model=TopicsResponse)
def list_topics() -> TopicsResponse:
    return TopicsResponse(topics=TOPICS)


@router.get("/modes", response_model=ModesResponse)
def list_modes() -> ModesResponse:
    return ModesResponse(modes=GENERATION_MODES)


@router.post("/generate", response_model=PremiseGenerateResponse)
def generate_premise_endpoint(payload: PremiseGenerateRequest) -> PremiseGenerateResponse:
    topic = payload.topic
    mode = payload.mode
    if payload.randomize:
        topic = random.choice(TOPICS)
        mode = random.choice(GENERATION_MODES)
    else:
        topic = topic or random.choice(TOPICS)
        mode = mode or random.choice(GENERATION_MODES)
    if topic not in TOPICS:
        topic = random.choice(TOPICS)
    if mode not in GENERATION_MODES:
        mode = random.choice(GENERATION_MODES)

    try:
        premise = generation_service.generate_premise(
            topic=topic,
            mode=mode,
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
            top_p=payload.top_p,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Premise generation failed: {exc}") from exc

    session = session_service.create(topic=topic, mode=mode, premise=premise)
    return PremiseGenerateResponse(
        session_id=session["session_id"],
        topic=topic,
        mode=mode,
        premise=premise,
        metadata={
            "model": "premise_generator",
            "adapter": "premise",
        },
    )
