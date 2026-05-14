from __future__ import annotations

import json
import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_contradiction_service, get_fact_lock_service, get_model_manager, get_session_service
from app.core.constants import GENERATION_MODES, TOPICS, WorkflowStage
from app.services.contradiction_service import ContradictionService
from app.services.fact_lock_service import FactLockService
from app.services.model_manager import ModelManager
from app.services.opposing_service import OpposingService
from app.services.premise_service import PremiseService
from app.services.session_service import SessionService
from app.services.workflow_service import WorkflowService


class LegacyPracticeStartRequest(BaseModel):
    topic: Optional[str] = None
    mode: Optional[str] = None
    randomize: bool = True


class LegacyPracticeArgumentRequest(BaseModel):
    session_id: str
    user_argument: str


class LegacyOpposingChallengeRequest(BaseModel):
    premise: str
    user_argument: str
    session_id: Optional[str] = None


router = APIRouter()


@router.get("/premise/topics")
async def premise_topics():
    return {"topics": TOPICS}


@router.get("/premise/modes")
async def premise_modes():
    return {"modes": GENERATION_MODES}


@router.post("/practice/start")
async def practice_start(
    payload: LegacyPracticeStartRequest,
    mm: ModelManager = Depends(get_model_manager),
    fls: FactLockService = Depends(get_fact_lock_service),
    ss: SessionService = Depends(get_session_service),
):
    topic = payload.topic or random.choice(TOPICS)
    mode = payload.mode or random.choice(GENERATION_MODES)
    if payload.randomize:
        topic = random.choice(TOPICS)
        mode = random.choice(GENERATION_MODES)

    session = await ss.create(topic, mode)
    premise_service = PremiseService(mm, fls, ss)
    result = await premise_service.generate(session, topic, mode)
    premise = result.get("premise", {})

    return {
        "session_id": result["session_id"],
        "topic": topic,
        "mode": mode,
        "premise": premise.get("scenario_text") if isinstance(premise, dict) else premise,
        "metadata": premise,
    }


@router.post("/practice/argument")
async def practice_argument(
    payload: LegacyPracticeArgumentRequest,
    cds: ContradictionService = Depends(get_contradiction_service),
    mm: ModelManager = Depends(get_model_manager),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.STUDENT_OPENING)

    flags = cds.check_argument(session, payload.user_argument)
    opening = await ss.add_argument(session, "opening", payload.user_argument, flags)

    session.workflow_stage = WorkflowStage.STUDENT_OPENING.value
    session.current_round = 1
    await ss.update(session)

    opposing_service = OpposingService(mm, ss)
    opposing = await opposing_service.generate(session)

    return {
        "session_id": payload.session_id,
        "premise": json.loads(session.premise_json or "{}"),
        "user_argument": payload.user_argument,
        "opposing_response": opposing.get("content", ""),
        "objection_feedback": flags,
        "workflow_stage": opposing.get("workflow_stage", WorkflowStage.OPPOSING_RESPONSE.value),
        "opening_argument_id": opening.id,
    }


@router.get("/practice/session/{session_id}")
async def practice_session(session_id: str, ss: SessionService = Depends(get_session_service)):
    session = await ss.get_detail(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/opposing/challenge")
async def opposing_challenge(
    payload: LegacyOpposingChallengeRequest,
    cds: ContradictionService = Depends(get_contradiction_service),
    mm: ModelManager = Depends(get_model_manager),
    fls: FactLockService = Depends(get_fact_lock_service),
    ss: SessionService = Depends(get_session_service),
):
    session = None
    if payload.session_id:
        session = await ss.get(payload.session_id)

    if session is None:
        session = await ss.create("custom challenge", "adversarial challenge")

    session.premise_json = json.dumps({"scenario_text": payload.premise})
    fls.lock_facts(session, payload.premise, fls.extract_facts(payload.premise))
    # Must advance stage to allow opening argument submission
    session.workflow_stage = WorkflowStage.FACTS_LOCKED.value
    await ss.update(session)

    WorkflowService().validate_transition(session, WorkflowStage.STUDENT_OPENING)
    flags = cds.check_argument(session, payload.user_argument)
    await ss.add_argument(session, "opening", payload.user_argument, flags)
    session.workflow_stage = WorkflowStage.STUDENT_OPENING.value
    await ss.update(session)

    opposing_service = OpposingService(mm, ss)
    opposing = await opposing_service.generate(session)

    return {
        "opposing_response": opposing.get("content", ""),
        "metadata": {
            "session_id": session.id,
            "workflow_stage": opposing.get("workflow_stage", WorkflowStage.OPPOSING_RESPONSE.value),
        },
    }
