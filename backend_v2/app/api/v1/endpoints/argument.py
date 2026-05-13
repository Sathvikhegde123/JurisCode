from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import (
    get_model_manager, get_contradiction_service, get_session_service
)
from app.schemas.argument import (
    OpeningArgumentRequest, RebuttalRequest, ArgumentResponse, OpposingResponseSchema
)
from app.services.model_manager import ModelManager
from app.services.contradiction_service import ContradictionService
from app.services.session_service import SessionService
from app.services.opposing_service import OpposingService
from app.services.workflow_service import WorkflowService
from app.core.constants import WorkflowStage

router = APIRouter()

@router.post("/{session_id}/opening", response_model=ArgumentResponse)
async def submit_opening(
    session_id: str,
    req: OpeningArgumentRequest,
    cds: ContradictionService = Depends(get_contradiction_service),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.STUDENT_OPENING)

    flags = cds.check_argument(session, req.content)
    arg = await ss.add_argument(session, "opening", req.content, flags)

    session.workflow_stage = WorkflowStage.STUDENT_OPENING.value
    session.current_round = 1
    await ss.update(session)

    return {
        "id": arg.id,
        "session_id": session_id,
        "round_number": 1,
        "argument_type": "opening",
        "content": arg.content,
        "hallucination_flags": flags,
        "workflow_stage": session.workflow_stage,
    }

@router.post("/{session_id}/opposing", response_model=OpposingResponseSchema)
async def generate_opposing(
    session_id: str,
    mm: ModelManager = Depends(get_model_manager),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.OPPOSING_RESPONSE)

    osvc = OpposingService(mm, ss)
    result = await osvc.generate(session)

    session.workflow_stage = WorkflowStage.OPPOSING_RESPONSE.value
    await ss.update(session)

    return result

@router.post("/{session_id}/rebuttal", response_model=ArgumentResponse)
async def submit_rebuttal(
    session_id: str,
    req: RebuttalRequest,
    cds: ContradictionService = Depends(get_contradiction_service),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.STUDENT_REBUTTAL)

    flags = cds.check_argument(session, req.content)
    arg = await ss.add_argument(session, "rebuttal", req.content, flags)

    session.workflow_stage = WorkflowStage.STUDENT_REBUTTAL.value
    session.current_round = 2
    await ss.update(session)

    return {
        "id": arg.id,
        "session_id": session_id,
        "round_number": 2,
        "argument_type": "rebuttal",
        "content": arg.content,
        "hallucination_flags": flags,
        "workflow_stage": session.workflow_stage,
    }
