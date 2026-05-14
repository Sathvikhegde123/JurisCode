import asyncio
import gc
import os
from typing import Optional, Any
from llama_cpp import Llama
from app.core.config import get_settings

class ModelManager:
    _instance: Optional["ModelManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._llm: Optional[Llama] = None
            cls._instance._active_model: Optional[str] = None
        return cls._instance

    @property
    def active_model(self) -> Optional[str]:
        return self._active_model

    async def load_model(self, model_key: str, gguf_path: str) -> Llama:
        async with self._lock:
            # If same model already loaded, just return it
            if self._active_model == model_key and self._llm is not None:
                return self._llm

            # Unload existing model to free memory
            await self._unload()

            if not os.path.exists(gguf_path):
                raise FileNotFoundError(f"GGUF model not found: {gguf_path}")

            settings = get_settings()
            print(f"[ModelManager] Loading {model_key} model from {gguf_path}...")
            
            def _load():
                return Llama(
                    model_path=gguf_path,
                    n_ctx=settings.MODEL_N_CTX,
                    n_gpu_layers=settings.MODEL_N_GPU_LAYERS,
                    verbose=False,
                )
            
            self._llm = await asyncio.to_thread(_load)
            self._active_model = model_key
            return self._llm

    async def unload_model(self) -> None:
        async with self._lock:
            await self._unload()

    async def _unload(self):
        if self._llm is not None:
            print(f"[ModelManager] Unloading {self._active_model} model...")
            del self._llm
            self._llm = None
            self._active_model = None
            gc.collect()

    async def generate_chat(
        self,
        messages: list,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop: Optional[list] = None,
        **kwargs: Any
    ) -> str:
        if self._llm is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        # Manual prompt formatting for Qwen/Llama3 consistency as per user's preference
        prompt = ""
        for msg in messages:
            prompt += f"<|{msg['role']}|>\n{msg['content']}\n"
        prompt += "<|assistant|>\n"

        async with self._lock:
            if self._llm is None:
                raise RuntimeError("Model was unloaded while generating.")
            
            def _call():
                response = self._llm(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop or ["<|system|>", "<|user|>", "<|assistant|>", "</s>"],
                    **kwargs
                )
                return response["choices"][0]["text"]

            return await asyncio.to_thread(_call)
