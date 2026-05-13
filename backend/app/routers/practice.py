"""Combined practice session routes."""

from __future__ import annotations

import random

from fastapi import APIRouter, HTTPException

from app.schemas.premise import GENERATION_MODES, TOPICS
from app.schemas.practice import (
    PracticeArgumentRequest,
    PracticeArgumentResponse,
    PracticeStartRequest,
    PracticeStartResponse,
    SessionDetailsResponse,
)
from app.services.generation_service import generation_service
from app.services.session_service import session_service
from app.utils.text_utils import parse_objection_evaluation

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/start", response_model=PracticeStartResponse)
def start_practice(payload: PracticeStartRequest) -> PracticeStartResponse:
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
        premise = generation_service.generate_premise(topic=topic, mode=mode)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Practice premise generation failed: {exc}") from exc

    session = session_service.create(topic=topic, mode=mode, premise=premise)
    return PracticeStartResponse(
        session_id=session["session_id"],
        topic=topic,
        mode=mode,
        premise=premise,
    )


@router.post("/argument", response_model=PracticeArgumentResponse)
def submit_practice_argument(payload: PracticeArgumentRequest) -> PracticeArgumentResponse:
    session = session_service.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    premise = session["premise"]
    try:
        opposing = generation_service.generate_opposing(
            user_argument=payload.user_argument,
            premise=premise,
        )
        raw_objection = generation_service.generate_objection(
            user_argument=payload.user_argument,
            premise=premise,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Practice argument processing failed: {exc}") from exc

    objection_feedback = parse_objection_evaluation(raw_objection)
    session_service.add_argument(
        session_id=payload.session_id,
        user_argument=payload.user_argument,
        opposing_response=opposing,
        objection_feedback=objection_feedback,
    )

    return PracticeArgumentResponse(
        session_id=payload.session_id,
        premise=premise,
        user_argument=payload.user_argument,
        opposing_response=opposing,
        objection_feedback=objection_feedback,
    )


@router.get("/session/{session_id}", response_model=SessionDetailsResponse)
def get_session(session_id: str) -> SessionDetailsResponse:
    session = session_service.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    data = session_service.to_dict(session)
    return SessionDetailsResponse(**data)
