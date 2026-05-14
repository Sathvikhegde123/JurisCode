import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.database import init_db
from app.routes.scenario_routes import router as scenario_router

_LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def _configure_logging() -> None:
    level = logging.DEBUG if settings.APP_ENV.strip().lower() == "development" else logging.INFO
    logging.basicConfig(level=level, format=_LOG_FORMAT, stream=sys.stdout, force=True)


_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("Database tables initialized (create_all if missing).")
    yield


app = FastAPI(title="JurisCode Scenario Analyzer API", lifespan=lifespan)


class _DisableDocsCacheMiddleware(BaseHTTPMiddleware):
    """Avoid stale Swagger/OpenAPI in browsers during local development."""

    _NO_CACHE_PATHS = frozenset({"/openapi.json", "/docs", "/redoc"})

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path in self._NO_CACHE_PATHS:
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(_DisableDocsCacheMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenario_router, prefix="/api/scenario")


@app.get("/health")
def health() -> dict:
    """Liveness; includes which routes this process registered (debugging mismatched Swagger)."""
    import app.routes.scenario_routes as scenario_routes_mod

    scenario_paths = sorted(
        {
            r.path
            for r in app.routes
            if getattr(r, "path", None) and str(r.path).startswith("/api/scenario")
        }
    )
    return {
        "status": "ok",
        "component": "Citizen Legal Scenario Analyzer",
        "mode": "standalone",
        "database": "sqlite",
        "gemini_model": settings.GEMINI_MODEL,
        "scenario_routes_loaded_from": scenario_routes_mod.__file__,
        "scenario_api_paths": scenario_paths,
    }
