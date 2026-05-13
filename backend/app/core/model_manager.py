"""Singleton llama-cpp-python model manager for GGUF inference."""

from __future__ import annotations

import threading
from typing import Any

from llama_cpp import Llama

from app.core.config import settings


class ModelManager:
    """Loads and manages multiple GGUF models using llama-cpp-python."""

    _instance: ModelManager | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ModelManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._constructed = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_constructed", False):
            return
        self._constructed = True
        self.models: dict[str, Llama] = {}
        self.active_model_name: str | None = None
        self.loaded: bool = False
        self._load_error: str | None = None

    def load(self) -> None:
        """Load GGUF models (idempotent)."""
        if self.loaded:
            return
        try:
            self._load_inner()
            self.loaded = True
            self._load_error = None
        except Exception as exc:
            self._load_error = str(exc)
            self.loaded = False
            self.models = {}
            self.active_model_name = None
            print(f"[ModelManager] Failed to load GGUF models: {exc}")

    def _load_inner(self) -> None:
        print("[ModelManager] Initializing GGUF models...")

        model_specs = [
            ("premise", settings.PREMISE_GGUF_PATH),
            ("opposing", settings.OPPOSING_COUNSEL_GGUF_PATH),
        ]

        for name, path in model_specs:
            print(f"[ModelManager] Loading {name} model from {path}...")
            self.models[name] = Llama(
                model_path=path,
                n_ctx=settings.GGUF_N_CTX,
                n_gpu_layers=settings.GGUF_N_GPU_LAYERS,
                verbose=False
            )

        if "premise" in self.models:
            self.active_model_name = "premise"
        elif self.models:
            self.active_model_name = list(self.models.keys())[0]

        print(f"[ModelManager] Successfully loaded {len(self.models)} models.")

    def set_adapter(self, name: str) -> None:
        """Switch the active GGUF model."""
        if name == "objection":
            # Per user request: do not touch objection evaluator.
            # We'll fallback to "opposing" model if it exists, or just do nothing.
            if "opposing" in self.models:
                # print("[ModelManager] Using 'opposing' model for 'objection' evaluator.")
                self.active_model_name = "opposing"
            return

        if name in self.models:
            self.active_model_name = name
        else:
            print(f"[ModelManager] WARNING: Model '{name}' not loaded. Keeping active: {self.active_model_name}")

    def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        repetition_penalty: float,
    ) -> str:
        if not self.loaded or not self.active_model_name:
            raise RuntimeError(
                self._load_error or "Model is not loaded. Check startup logs and GGUF paths."
            )

        model = self.models[self.active_model_name]

        # Format prompt to match user's test scripts
        prompt = ""
        for msg in messages:
            prompt += f"<|{msg['role']}|>\n{msg['content']}\n"
        prompt += "<|assistant|>\n"

        # Match parameters and stop tokens from user's test scripts
        output = model(
            prompt,
            max_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repetition_penalty,
            stop=["<|system|>", "<|user|>", "<|assistant|>", "</s>"],
            echo=False
        )

        text = output["choices"][0]["text"]
        return text.strip()

    def status(self) -> dict[str, Any]:
        return {
            "loaded_models": list(self.models.keys()),
            "active_model": self.active_model_name,
            "loaded": self.loaded,
            "n_ctx": settings.GGUF_N_CTX,
            "n_gpu_layers": settings.GGUF_N_GPU_LAYERS,
        }


model_manager = ModelManager()
