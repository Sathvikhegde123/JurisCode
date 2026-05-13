from fastapi import HTTPException
from app.core.constants import WorkflowStage

class WorkflowService:
    _transitions = {
        WorkflowStage.INIT: [WorkflowStage.PREMISE_GENERATED],
        WorkflowStage.PREMISE_GENERATED: [WorkflowStage.FACTS_LOCKED],
        WorkflowStage.FACTS_LOCKED: [WorkflowStage.STUDENT_OPENING],
        WorkflowStage.STUDENT_OPENING: [WorkflowStage.OPPOSING_RESPONSE],
        WorkflowStage.OPPOSING_RESPONSE: [WorkflowStage.STUDENT_REBUTTAL],
        WorkflowStage.STUDENT_REBUTTAL: [WorkflowStage.JUDGE_EVALUATION],
        WorkflowStage.JUDGE_EVALUATION: [WorkflowStage.COMPLETED],
        WorkflowStage.COMPLETED: [],
    }

    def validate_transition(self, session, target: WorkflowStage):
        current = WorkflowStage(session.workflow_stage)
        if current == WorkflowStage.COMPLETED:
            raise HTTPException(status_code=400, detail="Proceedings have already terminated.")
        allowed = self._transitions.get(current, [])
        if target not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow transition: {current.value} -> {target.value}"
            )

    def validate_proceeding_active(self, session):
        if session.workflow_stage == WorkflowStage.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Proceedings are terminated. No further submissions allowed.")
