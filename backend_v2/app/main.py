from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.compat_routes import router as compat_router
from app.db.base import init_db

app = FastAPI(
    title="JurisCode",
    version="2.0.0",
    description="Structured Procedural Legal Simulation Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000",
        "http://127.0.0.1:5173", "http://localhost:5174",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Initialize the database and create tables if they don't exist
    await init_db()

app.include_router(api_router, prefix="/api/v1")
app.include_router(compat_router)

@app.get("/health")
async def health():
    from app.services.model_manager import ModelManager
    mm = ModelManager()
    return {
        "status": "ok",
        "version": "2.0.0",
        "architecture": "procedural_simulation_engine",
        "active_model": mm.active_model,
    }

@app.get("/models/status")
async def models_status():
    from app.core.config import get_settings
    from app.services.model_manager import ModelManager

    settings = get_settings()
    mm = ModelManager()
    return {
        "backend_status": "ok",
        "version": "2.0.0",
        "architecture": "procedural_simulation_engine",
        "active_model": mm.active_model,
        "models_loaded": mm.active_model is not None,
        "device": "cuda" if settings.MODEL_N_GPU_LAYERS != 0 else "cpu",
    }

@app.get("/")
async def root():
    return {
        "service": "JurisCode v2.0 API",
        "docs": "/docs",
        "health": "/health",
        "v1_base": "/api/v1"
    }
