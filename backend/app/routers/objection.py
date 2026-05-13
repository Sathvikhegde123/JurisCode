"""Objection and weakness evaluation routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.objection import ObjectionEvaluateRequest, ObjectionEvaluateResponse
from app.services.generation_service import generation_service
from app.services.session_service import session_service
from app.utils.text_utils import parse_objection_evaluation

router = APIRouter(prefix="/objection", tags=["objection"])


@router.post("/evaluate", response_model=ObjectionEvaluateResponse)
def evaluate_objections(payload: ObjectionEvaluateRequest) -> ObjectionEvaluateResponse:
    premise = payload.premise
    if payload.session_id:
        session = session_service.get(payload.session_id)
        if session:
            premise = session.get("premise", premise)

    try:
        raw = generation_service.generate_objection(
            user_argument=payload.user_argument,
            premise=premise,
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
            top_p=payload.top_p,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Objection evaluation failed: {exc}") from exc

    parsed = parse_objection_evaluation(raw)
    return ObjectionEvaluateResponse(
        summary=parsed["summary"],
        objections=parsed["objections"],
        evidentiary_gaps=parsed["evidentiary_gaps"],
        procedural_issues=parsed["procedural_issues"],
        burden_of_proof_issues=parsed["burden_of_proof_issues"],
        contradictions=parsed["contradictions"],
        improvement_suggestions=parsed["improvement_suggestions"],
        argument_strength_score=int(parsed["argument_strength_score"]),
        raw_response=parsed["raw_response"],
    )
