"""Singleton Hugging Face + PEFT model manager for local inference."""

from __future__ import annotations

import os
import re
import threading
from typing import Any

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from app.core.config import settings

# Qwen2.x chat templates end each turn with this token (tokenizer_config.json id 151645).
_QWEN_CHAT_TURN_END = "<|" + "im_end" + "|>"


def _maybe_disable_ssl_verification() -> None:
    """Last-resort workaround for corporate proxies / broken cert chains (insecure)."""
    if not settings.HF_DISABLE_SSL_VERIFY:
        return
    import ssl

    print(
        "[ModelManager] WARNING: HF_DISABLE_SSL_VERIFY=true — TLS certificate verification is disabled "
        "for Python HTTPS (including Hugging Face Hub). Use only for local debugging on a trusted network."
    )
    ssl._create_default_https_context = ssl._create_unverified_context


def _hf_from_pretrained_kwargs() -> dict[str, Any]:
    return {
        "local_files_only": settings.LOCAL_FILES_ONLY,
        "trust_remote_code": settings.TRUST_REMOTE_CODE,
    }


def _gather_eos_token_ids(tokenizer: Any) -> list[int]:
    """Stop token ids for Qwen-style chat (eos_token in config + common specials)."""
    ids: list[int] = []
    seen: set[int] = set()

    def add_tid(tid: Any) -> None:
        if not isinstance(tid, int) or tid < 0:
            return
        unk = getattr(tokenizer, "unk_token_id", None)
        if unk is not None and tid == unk:
            return
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)

    add_tid(tokenizer.eos_token_id)
    et = getattr(tokenizer, "eos_token", None)
    if isinstance(et, str):
        try:
            add_tid(tokenizer.convert_tokens_to_ids(et))
        except Exception:  # noqa: BLE001
            pass
    for literal in (_QWEN_CHAT_TURN_END, "<|endoftext|>"):
        try:
            add_tid(tokenizer.convert_tokens_to_ids(literal))
        except Exception:  # noqa: BLE001
            pass
    return ids


def _is_peft_adapter_dir(path: str) -> bool:
    if not path or not os.path.isdir(path):
        return False
    return os.path.isfile(os.path.join(path, "adapter_config.json"))


def _immediate_subdirs(base: str) -> list[str]:
    if not os.path.isdir(base):
        return []
    out: list[str] = []
    for name in os.listdir(base):
        sub = os.path.join(base, name)
        if os.path.isdir(sub):
            out.append(sub)
    return sorted(out)


def _effective_peft_adapter_path(base_path: str) -> str | None:
    """
    Resolve the folder PEFT should load.

    Trainers often save as ``<config_dir>/<run_name>/adapter_config.json`` while
    ``.env`` still points at ``<config_dir>``. If ``base_path`` itself is not a
    PEFT adapter directory, look **one level** deep for the first valid adapter.

    When multiple nested adapters exist (e.g. ``qwen-...`` vs ``checkpoint-*``),
    prefer a non-checkpoint folder; if only checkpoints exist, pick the highest
    checkpoint step number.
    """
    if _is_peft_adapter_dir(base_path):
        return base_path

    candidates = [p for p in _immediate_subdirs(base_path) if _is_peft_adapter_dir(p)]
    if not candidates:
        return None

    def is_trainer_checkpoint(p: str) -> bool:
        return bool(re.fullmatch(r"checkpoint-\d+", os.path.basename(p)))

    non_ckpt = [p for p in candidates if not is_trainer_checkpoint(p)]
    if non_ckpt:
        return non_ckpt[0]

    def ckpt_num(p: str) -> int:
        m = re.fullmatch(r"checkpoint-(\d+)", os.path.basename(p))
        return int(m.group(1)) if m else -1

    return max(candidates, key=ckpt_num)


class ModelManager:
    """Loads one shared causal LM and optional multiple LoRA adapters."""

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
        self.tokenizer: AutoTokenizer | None = None
        self.model: Any = None
        self.loaded: bool = False
        self._load_error: str | None = None
        self._loaded_adapter_names: set[str] = set()
        self._current_adapter: str | None = None
        self._dtype_str: str = "unknown"

    def load(self) -> None:
        """Load tokenizer and model once (idempotent)."""
        if self.loaded:
            return
        try:
            self._load_inner()
            self.loaded = True
            self._load_error = None
        except Exception as exc:  # noqa: BLE001 — surface any load failure without crashing the import path
            self._load_error = str(exc)
            self.loaded = False
            self.tokenizer = None
            self.model = None
            self._loaded_adapter_names = set()
            self._current_adapter = None
            print(f"[ModelManager] Failed to load model: {exc}")

    def _load_inner(self) -> None:
        _maybe_disable_ssl_verification()
        if settings.LOCAL_FILES_ONLY:
            print(
                "[ModelManager] LOCAL_FILES_ONLY=true — Hub downloads are disabled; "
                "all model files must already exist in the Hugging Face cache or under BASE_MODEL_NAME."
            )

        hf_kw = _hf_from_pretrained_kwargs()
        print(f"[ModelManager] Loading tokenizer: {settings.BASE_MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            settings.BASE_MODEL_NAME,
            **hf_kw,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        use_cuda = torch.cuda.is_available()
        if not use_cuda:
            print("[ModelManager] WARNING: CUDA not available. Running on CPU (inference will be slow).")

        quantization_config = None
        if settings.USE_4BIT and use_cuda:
            try:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                print("[ModelManager] 4-bit quantization enabled (bitsandbytes).")
            except Exception as exc:  # noqa: BLE001
                print(f"[ModelManager] WARNING: 4-bit config failed ({exc}); falling back to non-quantized load.")
                quantization_config = None
        elif settings.USE_4BIT and not use_cuda:
            print("[ModelManager] WARNING: USE_4BIT=true but CUDA unavailable; loading without 4-bit quantization.")

        if use_cuda:
            torch_dtype = torch.float16
            model_kwargs: dict[str, Any] = {
                "torch_dtype": torch_dtype,
                "device_map": "auto",
                **hf_kw,
            }
            if quantization_config is not None:
                model_kwargs["quantization_config"] = quantization_config
        else:
            torch_dtype = torch.float32
            model_kwargs = {
                "torch_dtype": torch_dtype,
                "device_map": None,
                **hf_kw,
            }

        print(f"[ModelManager] Loading base model: {settings.BASE_MODEL_NAME}")
        base_model = AutoModelForCausalLM.from_pretrained(
            settings.BASE_MODEL_NAME,
            low_cpu_mem_usage=False,
            **model_kwargs,
        )
        if not use_cuda:
            base_model = base_model.to(torch.device("cpu"))

        self._dtype_str = str(torch_dtype)

        adapter_specs = [
            ("premise", settings.PREMISE_ADAPTER_PATH),
            ("opposing", settings.OPPOSING_COUNSEL_ADAPTER_PATH),
            ("objection", settings.OBJECTION_ADAPTER_PATH),
        ]

        adapter_effective: dict[str, str] = {}
        print(
            "[ModelManager] LoRA path check (adapter_config.json on path, or one subfolder below it):"
        )
        for name, path in adapter_specs:
            eff = _effective_peft_adapter_path(path)
            if eff is not None:
                adapter_effective[name] = eff
                nested = os.path.normpath(eff) != os.path.normpath(path)
                hint = f" -> OK (nested: {eff})" if nested else " -> OK"
                print(f"  - {name}: {path}{hint}")
            else:
                print(f"  - {name}: {path} -> missing or incomplete")

        first_path: str | None = None
        first_name: str | None = None
        for name, path in adapter_specs:
            eff = adapter_effective.get(name)
            if eff is None:
                print(
                    f"[ModelManager] WARNING: LoRA adapter '{name}' missing or incomplete at '{path}'. "
                    "Continuing with base weights for this role."
                )
            else:
                if first_path is None:
                    first_path, first_name = eff, name
                self._loaded_adapter_names.add(name)

        if first_path is not None and first_name is not None:
            print(f"[ModelManager] Wrapping base model with first LoRA adapter '{first_name}'.")
            self.model = PeftModel.from_pretrained(
                base_model,
                first_path,
                adapter_name=first_name,
                local_files_only=settings.LOCAL_FILES_ONLY,
            )
            self._current_adapter = first_name
            for name, path in adapter_specs:
                if name == first_name:
                    continue
                eff = adapter_effective.get(name)
                if eff is not None:
                    print(f"[ModelManager] Loading additional LoRA adapter '{name}'.")
                    try:
                        self.model.load_adapter(
                            eff,
                            adapter_name=name,
                            local_files_only=settings.LOCAL_FILES_ONLY,
                        )
                    except TypeError:
                        self.model.load_adapter(eff, adapter_name=name)
        else:
            self.model = base_model
            self._current_adapter = None
            print("[ModelManager] No LoRA adapters found; using base model only.")

    def set_adapter(self, name: str) -> None:
        """Activate a named LoRA adapter if available."""
        if not self.loaded or self.model is None:
            print(f"[ModelManager] WARNING: Model not loaded; cannot set adapter '{name}'.")
            return
        if not isinstance(self.model, PeftModel):
            print(
                f"[ModelManager] WARNING: No LoRA adapters loaded; cannot set adapter '{name}'. "
                "Using base model behavior."
            )
            return
        peft_keys = set(getattr(self.model, "peft_config", {}).keys())
        if name in self._loaded_adapter_names and name in peft_keys:
            self.model.set_adapter(name)
            self._current_adapter = name
        else:
            print(
                f"[ModelManager] WARNING: Adapter '{name}' is not available. "
                "Keeping current adapter / base behavior."
            )

    def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        repetition_penalty: float,
    ) -> str:
        if not self.loaded or self.tokenizer is None or self.model is None:
            raise RuntimeError(
                self._load_error or "Model is not loaded. Check startup logs and Hugging Face cache connectivity."
            )

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        pad_id = self.tokenizer.pad_token_id
        if pad_id is None:
            pad_id = self.tokenizer.eos_token_id

        do_sample = temperature is not None and temperature > 0
        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "repetition_penalty": repetition_penalty,
            "pad_token_id": pad_id,
        }
        if do_sample:
            gen_kwargs["temperature"] = max(float(temperature), 1e-5)
            gen_kwargs["top_p"] = top_p

        eos_ids = _gather_eos_token_ids(self.tokenizer)
        if eos_ids:
            gen_kwargs["eos_token_id"] = eos_ids[0] if len(eos_ids) == 1 else eos_ids

        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **gen_kwargs)

        new_tokens = output_ids[0][inputs["input_ids"].shape[-1] :]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return self._clean_output(text)

    def _clean_output(self, text: str) -> str:
        cleaned = text.strip()
        patterns = [
            r"<\|im_start\|>assistant\s*",
            re.escape(_QWEN_CHAT_TURN_END),
            r"<\|im_end\|>",
            r"<\|endoftext\|>",
        ]
        for pat in patterns:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def status(self) -> dict[str, Any]:
        hub = {
            "local_files_only": settings.LOCAL_FILES_ONLY,
            "trust_remote_code": settings.TRUST_REMOTE_CODE,
            "hf_disable_ssl_verify": settings.HF_DISABLE_SSL_VERIFY,
        }
        if not self.loaded or self.model is None:
            return {
                "base_model": settings.BASE_MODEL_NAME,
                "premise_adapter_loaded": False,
                "opposing_adapter_loaded": False,
                "objection_adapter_loaded": False,
                "device": settings.DEVICE,
                "dtype": "unknown",
                "current_adapter": None,
                "loaded": False,
                **hub,
            }
        try:
            actual_device = str(next(self.model.parameters()).device)
        except StopIteration:
            actual_device = settings.DEVICE
        return {
            "base_model": settings.BASE_MODEL_NAME,
            "premise_adapter_loaded": "premise" in self._loaded_adapter_names,
            "opposing_adapter_loaded": "opposing" in self._loaded_adapter_names,
            "objection_adapter_loaded": "objection" in self._loaded_adapter_names,
            "device": actual_device,
            "dtype": self._dtype_str,
            "current_adapter": self._current_adapter,
            "loaded": True,
            **hub,
        }


model_manager = ModelManager()
