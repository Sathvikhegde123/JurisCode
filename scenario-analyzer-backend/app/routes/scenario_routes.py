import logging
import traceback

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.repositories import scenario_repository as repo
from app.scenario_analyzer.report_api_formatter import format_full_report_for_client
from app.scenario_analyzer.schemas import (
    ChatHistoryResponse,
    FullReportResponse,
    LegalClarityScoreResponse,
    ScenarioAnalyzeRequest,
    ScenarioAnalyzeResponse,
    ScenarioChatRequest,
    ScenarioChatResponse,
    SessionsListResponse,
    SourcePacksListResponse,
)
from app.scenario_analyzer.scenario_chat_service import continue_socratic_chat
from app.scenario_analyzer.scenario_service import analyze_scenario
from app.scenario_analyzer.scoring_service import (
    generate_legal_clarity_score,
    get_existing_legal_clarity_score,
)
from app.scenario_analyzer.source_pack_loader import (
    list_available_source_packs,
    source_packs_dir_exists,
)

router = APIRouter(tags=["scenario"])
logger = logging.getLogger(__name__)


def _is_dev() -> bool:
    return settings.APP_ENV.strip().lower() == "development"


@router.get("/debug/config")
def debug_config() -> dict:
    if not _is_dev():
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "gemini_key_loaded": settings.gemini_key_configured(),
        "gemini_model": settings.GEMINI_MODEL,
        "source_packs_path_exists": source_packs_dir_exists(),
        "available_source_packs": list_available_source_packs(),
        "database_url_prefix": (settings.DATABASE_URL or "").split("://")[0],
    }


@router.post(
    "/analyze",
    response_model=ScenarioAnalyzeResponse,
    response_model_exclude_none=True,
)
def analyze(
    body: ScenarioAnalyzeRequest,
    include_full_report_debug: bool = Query(
        default=False,
        description="Development only: include full_report in the response body.",
    ),
):
    try:
        uc = body.user_context.model_dump() if body.user_context is not None else None
        allow_debug = _is_dev() and include_full_report_debug
        result = analyze_scenario(body.scenario, uc, include_full_report_debug=allow_debug)
        return ScenarioAnalyzeResponse.model_validate(result)
    except ValidationError as ve:
        tb = traceback.format_exc()
        logger.error("ScenarioAnalyzeResponse validation failed:\n%s", tb)
        if _is_dev():
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Scenario analysis failed",
                    "details": str(ve),
                    "traceback": tb,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Scenario analysis failed",
            },
        )
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Unhandled error in /analyze:\n%s", tb)
        if _is_dev():
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Scenario analysis failed",
                    "details": f"{type(e).__name__}: {e}",
                    "traceback": tb,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Scenario analysis failed",
            },
        )


@router.get("/report/{session_id}", response_model=FullReportResponse)
def get_full_report(session_id: str):
    try:
        row = repo.get_report(session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Session or report not found")
        fr = format_full_report_for_client(dict(row.get("full_report") or {}))
        return FullReportResponse(session_id=session_id, full_report=fr)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in GET /report: %s", e)
        if _is_dev():
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
        raise HTTPException(status_code=500, detail="Could not load report") from e


@router.post("/chat", response_model=ScenarioChatResponse, response_model_exclude_none=True)
def post_chat(body: ScenarioChatRequest):
    try:
        out = continue_socratic_chat(body.session_id, body.message)
        return ScenarioChatResponse.model_validate(out)
    except ValueError as ve:
        if str(ve) == "session_not_found" or str(ve) == "report_not_found":
            raise HTTPException(status_code=404, detail="Session or report not found") from ve
        logger.warning("Chat validation error: %s", ve)
        raise HTTPException(status_code=400, detail="Invalid request") from ve
    except ValidationError as ve:
        tb = traceback.format_exc()
        logger.error("ScenarioChatResponse validation failed:\n%s", tb)
        if _is_dev():
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Chat failed",
                    "details": str(ve),
                    "traceback": tb,
                },
            )
        return JSONResponse(status_code=500, content={"error": True, "message": "Chat failed"})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Unhandled error in /chat:\n%s", tb)
        if _is_dev():
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Chat failed",
                    "details": f"{type(e).__name__}: {e}",
                    "traceback": tb,
                },
            )
        return JSONResponse(status_code=500, content={"error": True, "message": "Chat failed"})


@router.get("/chat/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str):
    try:
        if repo.get_session(session_id) is None:
            raise HTTPException(status_code=404, detail="Session not found")
        msgs = repo.get_chat_history(session_id, limit=100)
        return ChatHistoryResponse(session_id=session_id, messages=msgs)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in GET /chat: %s", e)
        if _is_dev():
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
        raise HTTPException(status_code=500, detail="Could not load chat history") from e


@router.post(
    "/score/{session_id}",
    response_model=LegalClarityScoreResponse,
    response_model_exclude_none=True,
)
def post_generate_legal_clarity_score(session_id: str):
    """Generate and persist Legal Clarity Score for a session (on demand)."""
    try:
        out = generate_legal_clarity_score(session_id)
        return LegalClarityScoreResponse.model_validate(out)
    except ValueError as ve:
        if str(ve) == "session_not_found":
            raise HTTPException(status_code=404, detail="Session not found") from ve
        if str(ve) == "report_not_found":
            raise HTTPException(status_code=404, detail="Session or report not found") from ve
        raise HTTPException(status_code=400, detail="Invalid request") from ve
    except ValidationError as ve:
        tb = traceback.format_exc()
        logger.error("LegalClarityScoreResponse validation failed:\n%s", tb)
        if _is_dev():
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Score generation failed",
                    "details": str(ve),
                    "traceback": tb,
                },
            )
        return JSONResponse(status_code=500, content={"error": True, "message": "Score generation failed"})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Unhandled error in POST /score:\n%s", tb)
        if _is_dev():
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Score generation failed",
                    "details": f"{type(e).__name__}: {e}",
                    "traceback": tb,
                },
            )
        return JSONResponse(status_code=500, content={"error": True, "message": "Score generation failed"})


@router.get("/score/{session_id}", response_model=None)
def get_legal_clarity_score(session_id: str):
    """Return stored Legal Clarity Score, or 404 with score_available=false if not generated yet."""
    try:
        if repo.get_session(session_id) is None:
            raise HTTPException(status_code=404, detail="Session not found")
        row = get_existing_legal_clarity_score(session_id)
        if row is None:
            return JSONResponse(
                status_code=404,
                content={
                    "score_available": False,
                    "message": "Score has not been generated for this session yet.",
                },
            )
        return LegalClarityScoreResponse.model_validate(row)
    except HTTPException:
        raise
    except ValidationError as ve:
        logger.error("LegalClarityScoreResponse validation failed on GET /score: %s", ve)
        raise HTTPException(status_code=500, detail="Stored score is invalid") from ve
    except Exception as e:
        logger.exception("Error in GET /score: %s", e)
        if _is_dev():
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
        raise HTTPException(status_code=500, detail="Could not load score") from e


@router.get("/sessions", response_model=SessionsListResponse)
def list_sessions(limit: int = Query(default=20, ge=1, le=100)):
    if not _is_dev():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        sessions = repo.list_recent_sessions(limit=limit)
        return SessionsListResponse(sessions=sessions)
    except Exception as e:
        logger.exception("Error in GET /sessions: %s", e)
        raise HTTPException(status_code=500, detail="Could not list sessions") from e


@router.get("/source-packs", response_model=SourcePacksListResponse)
def source_packs() -> dict:
    return {
        "available_source_packs": [
            "tenant_eviction",
            "mutation_vs_title",
            "sale_deed_dispute",
            "rera_delay",
            "partition_ancestral_property",
        ]
    }
