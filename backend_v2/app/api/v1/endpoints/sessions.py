from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_session_service
from app.schemas.session import SessionCreate, SessionResponse, SessionDetail
from app.services.session_service import SessionService

router = APIRouter()

@router.post("", response_model=SessionResponse)
async def create_session(
    req: SessionCreate,
    svc: SessionService = Depends(get_session_service),
):
    session = await svc.create(req.topic, req.mode)
    return session

@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
):
    session = await svc.get_detail(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
