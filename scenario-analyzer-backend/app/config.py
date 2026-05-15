from functools import lru_cache
import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Project root: Scenario_Analyzer/ (parent of app/)
_APP_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _APP_DIR.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    APP_ENV: str = Field(default="development")
    APP_HOST: str = Field(default="127.0.0.1")
    APP_PORT: int = Field(default=8001)
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:5174",
        description="Comma-separated list of allowed origins",
    )
    DATABASE_URL: str = Field(
        default="sqlite:///./scenario_analyzer.db",
        description="SQLAlchemy database URL (SQLite default)",
    )

    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []
        return [o.strip() for o in raw.split(",") if o.strip()]

    def gemini_key_configured(self) -> bool:
        k = self.GEMINI_API_KEY
        return bool(k and str(k).strip())


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    logger.info(
        "Settings loaded from %s | GEMINI_API_KEY set=%s | GEMINI_MODEL=%s | APP_ENV=%s",
        _ENV_FILE,
        s.gemini_key_configured(),
        s.GEMINI_MODEL,
        s.APP_ENV,
    )
    return s


def project_root() -> Path:
    return _PROJECT_ROOT


settings = get_settings()
