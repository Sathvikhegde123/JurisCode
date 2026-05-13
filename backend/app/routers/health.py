"""Health and model status endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.core.model_manager import model_manager

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "device": settings.DEVICE,
        "models_loaded": model_manager.loaded,
    }


@router.get("/models/status")
def models_status() -> dict[str, Any]:
    return model_manager.status()
