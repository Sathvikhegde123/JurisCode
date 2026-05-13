from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_model_manager, get_fact_lock_service, get_session_service
from app.schemas.premise import PremiseRequest, PremiseResponse
from app.services.model_manager import ModelManager
from app.services.fact_lock_service import FactLockService
from app.services.session_service import SessionService
from app.services.premise_service import PremiseService
from app.services.workflow_service import WorkflowService
from app.core.constants import WorkflowStage

router = APIRouter()

@router.post("/{session_id}/premise", response_model=PremiseResponse)
async def generate_premise(
    session_id: str,
    req: PremiseRequest,
    mm: ModelManager = Depends(get_model_manager),
    fls: FactLockService = Depends(get_fact_lock_service),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    wf = WorkflowService()
    wf.validate_transition(session, WorkflowStage.PREMISE_GENERATED)

    ps = PremiseService(mm, fls, ss)
    return await ps.generate(session, req.topic, req.mode)
