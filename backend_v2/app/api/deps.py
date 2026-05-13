from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.model_manager import ModelManager
from app.services.workflow_service import WorkflowService
from app.services.fact_lock_service import FactLockService
from app.services.contradiction_service import ContradictionService
from app.services.session_service import SessionService

def get_model_manager():
    return ModelManager()

def get_workflow_service():
    return WorkflowService()

def get_fact_lock_service():
    return FactLockService()

def get_contradiction_service(fls: FactLockService = Depends(get_fact_lock_service)):
    return ContradictionService(fls)

def get_session_service(db: AsyncSession = Depends(get_db)):
    return SessionService(db)
