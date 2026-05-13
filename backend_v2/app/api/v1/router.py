from fastapi import APIRouter
from app.api.v1.endpoints import sessions, premise, argument, judgment

api_router = APIRouter()
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(premise.router, prefix="/sessions", tags=["premise"])
api_router.include_router(argument.router, prefix="/sessions", tags=["arguments"])
api_router.include_router(judgment.router, prefix="/sessions", tags=["judgment"])
