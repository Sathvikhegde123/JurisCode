"""FastAPI application entrypoint for JurisCode Bharat."""

from __future__ import annotations

from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.model_manager import model_manager
from app.routers import health, objection, opposing, practice, premise


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("=" * 64)
    print("JurisCode Bharat — Legal Reasoning & Trial Practice API")
    print("Starting model load (local Hugging Face + PEFT only)...")
    print("=" * 64)
    if not torch.cuda.is_available():
        print("WARNING: Running without CUDA. Inference will use CPU and may be very slow.")
    model_manager.load()
    if model_manager.loaded:
        print("JurisCode Bharat API is ready.")
    else:
        print("WARNING: JurisCode Bharat API started in degraded mode (model not loaded).")
    yield
    print("JurisCode Bharat API shutting down.")


app = FastAPI(
    title="JurisCode Bharat - Legal Reasoning & Trial Practice API",
    description=(
        "AI-based Indian property litigation training platform backend. "
        "Runs local Qwen2.5-3B-Instruct with switchable LoRA adapters."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(premise.router)
app.include_router(opposing.router)
app.include_router(objection.router)
app.include_router(practice.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "JurisCode Bharat API",
        "docs": "/docs",
        "health": "/health",
    }
