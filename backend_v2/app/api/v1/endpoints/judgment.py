from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_model_manager, get_session_service
from app.schemas.judgment import JudgmentResponse
from app.services.session_service import SessionService
from app.services.judge_service import JudgeService
from app.services.scoring_service import ScoringService
from app.services.workflow_service import WorkflowService
from app.services.model_manager import ModelManager
from app.core.config import get_settings
from app.core.constants import WorkflowStage

router = APIRouter()

@router.post("/{session_id}/judge", response_model=JudgmentResponse)
async def judge_evaluation(
    session_id: str,
    mm: ModelManager = Depends(get_model_manager),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.JUDGE_EVALUATION)

    # Reload session with all details for the judge
    session = await ss.get_detail(session_id)

    js = JudgeService()
    jresult = await js.evaluate(session)
    
    scs = ScoringService()
    final_score = scs.compute_final_score(session, jresult)

    await ss.add_judgment(session, jresult, final_score)

    session.workflow_stage = WorkflowStage.COMPLETED.value
    session.status = "completed"
    session.final_score = final_score
    await ss.update(session)

    # Pre-emptively load premise model for the next session (as per v2 spec)
    settings = get_settings()
    await mm.load_model("premise", settings.resolved_premise_path)

    return {
        "session_id": session_id,
        **jresult,
        "final_score": final_score,
        "workflow_stage": WorkflowStage.COMPLETED.value,
    }
