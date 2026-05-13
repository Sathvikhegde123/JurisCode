from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "JurisCode"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./juriscode.db"

    # Paths resolved relative to this file's parent's parent's parent (backend_v2 root)
    PREMISE_GGUF_PATH: str = "../models/premise_generator_Q4_K_M.gguf"
    OPPOSING_GGUF_PATH: str = "../models/opposing_counsel_Q4_K_M.gguf"
    MODEL_N_CTX: int = 4096
    MODEL_N_GPU_LAYERS: int = -1

    GROQ_API_KEY: str = ""
    GROQ_JUDGE_MODEL: str = "llama-3.3-70b-versatile"
    MAX_ARGUMENT_ROUNDS: int = 3

    @property
    def resolved_premise_path(self) -> str:
        p = Path(self.PREMISE_GGUF_PATH)
        if p.is_absolute():
            return str(p)
        root = Path(__file__).resolve().parent.parent.parent
        return str((root / p).resolve())

    @property
    def resolved_opposing_path(self) -> str:
        p = Path(self.OPPOSING_GGUF_PATH)
        if p.is_absolute():
            return str(p)
        root = Path(__file__).resolve().parent.parent.parent
        return str((root / p).resolve())

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
