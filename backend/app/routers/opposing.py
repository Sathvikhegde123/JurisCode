"""Opposing counsel simulation routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.opposing import OpposingChallengeRequest, OpposingChallengeResponse
from app.services.generation_service import generation_service
from app.services.session_service import session_service

router = APIRouter(prefix="/opposing", tags=["opposing"])


@router.post("/challenge", response_model=OpposingChallengeResponse)
def challenge_argument(payload: OpposingChallengeRequest) -> OpposingChallengeResponse:
    premise = payload.premise
    if payload.session_id:
        session = session_service.get(payload.session_id)
        if session:
            premise = session.get("premise", premise)

    try:
        response_text = generation_service.generate_opposing(
            user_argument=payload.user_argument,
            premise=premise,
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
            top_p=payload.top_p,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Opposing counsel generation failed: {exc}") from exc

    return OpposingChallengeResponse(
        opposing_response=response_text,
        metadata={
            "model": "opposing_counsel",
            "adapter": "opposing",
        },
    )
