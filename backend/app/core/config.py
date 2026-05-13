"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

import torch
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_ROOT / ".env")


def _resolve_path(value: str) -> str:
    p = Path(value.strip())
    if p.is_absolute():
        return str(p.resolve())
    return str((BACKEND_ROOT / p).resolve())


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class Settings:
    """Runtime settings with safe defaults."""

    BASE_MODEL_NAME: str = os.getenv("BASE_MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct")
    PREMISE_ADAPTER_PATH: str = _resolve_path(
        os.getenv("PREMISE_ADAPTER_PATH", "./models/premise_generator_lora")
    )
    OPPOSING_COUNSEL_ADAPTER_PATH: str = _resolve_path(
        os.getenv("OPPOSING_COUNSEL_ADAPTER_PATH", "./models/opposing_counsel_lora")
    )
    OBJECTION_ADAPTER_PATH: str = _resolve_path(
        os.getenv("OBJECTION_ADAPTER_PATH", "./models/objection_evaluator_lora")
    )
    USE_4BIT: bool = _get_bool("USE_4BIT", False)
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    DEFAULT_MAX_NEW_TOKENS: int = _get_int("DEFAULT_MAX_NEW_TOKENS", 300)
    DEFAULT_TEMPERATURE: float = _get_float("DEFAULT_TEMPERATURE", 0.7)
    DEFAULT_TOP_P: float = _get_float("DEFAULT_TOP_P", 0.9)
    DEFAULT_REPETITION_PENALTY: float = _get_float("DEFAULT_REPETITION_PENALTY", 1.1)
    # Hub / network (SSL, offline). See README "Hugging Face Hub and SSL".
    LOCAL_FILES_ONLY: bool = _get_bool("LOCAL_FILES_ONLY", False)
    TRUST_REMOTE_CODE: bool = _get_bool("TRUST_REMOTE_CODE", True)
    HF_DISABLE_SSL_VERIFY: bool = _get_bool("HF_DISABLE_SSL_VERIFY", False)


settings = Settings()
