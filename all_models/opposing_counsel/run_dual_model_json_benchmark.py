#!/usr/bin/env python3
"""
Dual LoRA benchmark: run property_opposing_counsel_benchmark.json against
packfalse and packtrue PEFT adapters; save JSON outputs with resume support.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

FALLBACK_SYSTEM_PROMPT = (
    "You are adversarial Indian opposing counsel in a property-litigation training simulation. "
    "Critically challenge the user's argument using title analysis, possession analysis, civil procedure, "
    "evidentiary scrutiny, burden-of-proof evaluation, contradiction exposure, and fact-specific legal reasoning. "
    "Do not invent case citations."
)

CLAUDE_EVALUATOR_PROMPT = """You are evaluating two fine-tuned Indian Property Litigation Opposing Counsel models.

You will receive:
1. benchmark JSON with prompts and rubric
2. packfalse_outputs.json
3. packtrue_outputs.json
or one combined_packfalse_packtrue_outputs.json

Evaluate each test case fairly using this rubric:
- Legal relevance: 2 marks
- Opposing counsel posture: 2 marks
- Property-law accuracy: 2 marks
- Fact-specific attack: 1.5 marks
- Evidence/procedure/burden analysis: 1.5 marks
- Hallucination control/no fake citations: 1 mark

For each test case, return:
- test_id
- category
- packfalse score /10
- packtrue score /10
- winner: packfalse / packtrue / tie
- strengths of packfalse
- weaknesses of packfalse
- strengths of packtrue
- weaknesses of packtrue
- hallucination or fake citation found? yes/no
- notes

Then provide:
- average score for both models
- winner count
- hallucination count
- repeated failure patterns
- final recommendation
- whether prompt tuning, inference parameter tuning, or dataset retraining is needed

Important:
Do not favor longer answers automatically.
Prefer legally accurate, adversarial, fact-specific, concise responses.
Do not recommend retraining unless repeated failures appear across many prompts.
"""


def str2bool(v: str) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).lower().strip()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(f"Expected true/false, got {v!r}")


def get_model_device(model: torch.nn.Module) -> torch.device:
    return next(model.parameters()).device


def resolve_local_path(path: str) -> str:
    """Normalize to absolute local path so PEFT/HF do not treat './...' as a Hub repo id."""
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def ensure_adapter_dir(adapter_path: str) -> str:
    resolved = resolve_local_path(adapter_path)
    if not os.path.isdir(resolved):
        raise FileNotFoundError(
            f"Adapter directory not found: {adapter_path!r} -> {resolved!r}. "
            "Create the folder or pass --packfalse_adapter / --packtrue_adapter to an existing PEFT save "
            "(must contain adapter_config.json)."
        )
    cfg = os.path.join(resolved, "adapter_config.json")
    if not os.path.isfile(cfg):
        raise FileNotFoundError(
            f"Not a PEFT adapter folder (missing adapter_config.json): {resolved!r}"
        )
    weights = os.path.join(resolved, "adapter_model.safetensors")
    if not os.path.isfile(weights):
        raise FileNotFoundError(
            "This folder has adapter_config.json but does not contain adapter_model.safetensors, "
            "so it is not a complete PEFT LoRA adapter for inference."
        )
    return resolved


def load_tokenizer(adapter_path: str, base_model_name: str) -> AutoTokenizer:
    try:
        tok = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
    except Exception:
        tok = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    if getattr(tok, "pad_token", None) is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    return tok


def load_model_with_adapter(
    base_model_name: str,
    adapter_path: str,
    device: str,
    load_in_4bit: bool,
) -> Tuple[torch.nn.Module, AutoTokenizer]:
    adapter_path = ensure_adapter_dir(adapter_path)
    print(f"Loading {adapter_path} on device={device}, load_in_4bit={load_in_4bit}")
    tokenizer = load_tokenizer(adapter_path, base_model_name)

    use_cuda = torch.cuda.is_available() and device == "cuda"
    quantization_config = None
    device_map: Optional[Union[str, Dict[str, int]]] = None
    torch_dtype: Optional[torch.dtype] = None

    if load_in_4bit:
        if not use_cuda:
            print(
                "Warning: --load_in_4bit true but CUDA unavailable; loading in fp32 on CPU.",
                file=sys.stderr,
            )
            torch_dtype = torch.float32
        else:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            device_map = {"": 0}
    elif use_cuda:
        torch_dtype = torch.float16
        device_map = "auto"
    else:
        torch_dtype = torch.float32

    kwargs: Dict[str, Any] = {
        "trust_remote_code": True,
    }
    if quantization_config is not None:
        kwargs["quantization_config"] = quantization_config
        kwargs["device_map"] = device_map
    else:
        kwargs["torch_dtype"] = torch_dtype
        if device_map is not None:
            kwargs["device_map"] = device_map

    model = AutoModelForCausalLM.from_pretrained(base_model_name, **kwargs)
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()

    if not use_cuda and quantization_config is None and device_map is None:
        model = model.to("cpu")

    return model, tokenizer


def unload_model(model: Optional[torch.nn.Module], tokenizer: Optional[AutoTokenizer]) -> None:
    try:
        if model is not None:
            model.to("cpu")
    except Exception:
        pass

    del model
    del tokenizer

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    time.sleep(2)


def _eos_token_id(tokenizer: AutoTokenizer) -> int:
    try:
        tid = tokenizer.convert_tokens_to_ids("<|im_end|>")
        if tid is not None and tid != tokenizer.unk_token_id:
            return int(tid)
    except Exception:
        pass
    return int(tokenizer.eos_token_id)


def _clean_assistant_text(text: str) -> str:
    if not text:
        return ""
    for tok in (
        "<|im_end|>",
        "<|endoftext|>",
        "<|im_start|>",
    ):
        text = text.replace(tok, " ")
    text = re.sub(r"(?im)^\s*(assistant|user|system)\s*:\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def generate_response(
    model: torch.nn.Module,
    tokenizer: AutoTokenizer,
    system_prompt: str,
    user_prompt: str,
    generation_config: Dict[str, Any],
) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
    dev = get_model_device(model)
    input_ids = inputs["input_ids"].to(dev)
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(dev)

    gen_kw = {
        "max_new_tokens": int(generation_config["max_new_tokens"]),
        "temperature": float(generation_config["temperature"]),
        "top_p": float(generation_config["top_p"]),
        "repetition_penalty": float(generation_config["repetition_penalty"]),
        "do_sample": bool(generation_config["do_sample"]),
        "pad_token_id": tokenizer.eos_token_id,
        "eos_token_id": _eos_token_id(tokenizer),
    }
    with torch.inference_mode():
        out = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            **gen_kw,
        )
    full = tokenizer.decode(out[0], skip_special_tokens=False)
    prompt_decoded = tokenizer.decode(input_ids[0], skip_special_tokens=False)
    if full.startswith(prompt_decoded):
        gen_part = full[len(prompt_decoded) :]
    else:
        gen_part = tokenizer.decode(out[0][input_ids.shape[1] :], skip_special_tokens=False)
    return _clean_assistant_text(gen_part)


def load_existing_output_json(
    path: str,
    model_name: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "model_name": model_name,
        "base_model": metadata["base_model"],
        "adapter_path": metadata["adapter_path"],
        "benchmark_file": metadata["benchmark_file"],
        "system_prompt": metadata["system_prompt"],
        "generation_config": dict(metadata["generation_config"]),
        "outputs": [],
    }


def save_output_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def has_test_output(data: Dict[str, Any], test_id: str) -> bool:
    for item in data.get("outputs", []):
        if item.get("test_id") == test_id:
            return True
    return False


def upsert_test_output(data: Dict[str, Any], output_item: Dict[str, Any], force: bool) -> None:
    tid = output_item.get("test_id")
    outputs: List[Dict[str, Any]] = data.setdefault("outputs", [])
    for i, o in enumerate(outputs):
        if o.get("test_id") == tid:
            if force:
                outputs[i] = output_item
            return
    outputs.append(output_item)


def _get_output_for_test(data: Dict[str, Any], test_id: str) -> Optional[Dict[str, Any]]:
    for o in data.get("outputs", []):
        if o.get("test_id") == test_id:
            return o
    return None


def rebuild_combined(
    benchmark: Dict[str, Any],
    packfalse_data: Dict[str, Any],
    packtrue_data: Dict[str, Any],
    base_model: str,
    system_prompt: str,
    generation_config: Dict[str, Any],
) -> Dict[str, Any]:
    paired: List[Dict[str, Any]] = []
    for tc in benchmark.get("test_cases", []):
        tid = tc.get("test_id")
        pf = _get_output_for_test(packfalse_data, tid) if tid else None
        pt = _get_output_for_test(packtrue_data, tid) if tid else None
        paired.append(
            {
                "test_id": tid,
                "category": tc.get("category"),
                "user_prompt": tc.get("user_prompt"),
                "ideal_challenge_should_cover": tc.get("ideal_challenge_should_cover"),
                "scoring_focus": tc.get("scoring_focus"),
                "packing_false_output": (pf or {}).get("model_output") or "",
                "packing_true_output": (pt or {}).get("model_output") or "",
                "packing_false_error": (pf or {}).get("error"),
                "packing_true_error": (pt or {}).get("error"),
            }
        )
    return {
        "benchmark_name": benchmark.get("benchmark_name"),
        "base_model": base_model,
        "system_prompt": system_prompt,
        "generation_config": dict(generation_config),
        "paired_outputs": paired,
        "scoring_rubric_out_of_10": benchmark.get("scoring_rubric_out_of_10", []),
    }


def count_completed(data: Dict[str, Any]) -> int:
    n = 0
    for o in data.get("outputs", []):
        if o.get("error") is None and o.get("model_output") not in (None, ""):
            n += 1
        elif o.get("error"):
            n += 1
    return n


def count_errors(data: Dict[str, Any]) -> int:
    return sum(1 for o in data.get("outputs", []) if o.get("error"))


def write_run_summary(
    path: str,
    total: int,
    packfalse_data: Dict[str, Any],
    packtrue_data: Dict[str, Any],
) -> None:
    summary = {
        "total_test_cases": total,
        "packing_false_completed": len(packfalse_data.get("outputs", [])),
        "packing_true_completed": len(packtrue_data.get("outputs", [])),
        "packing_false_errors": count_errors(packfalse_data),
        "packing_true_errors": count_errors(packtrue_data),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_output_json(path, summary)


def write_evaluator_prompt(output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    p = os.path.join(output_dir, "claude_evaluator_prompt.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(CLAUDE_EVALUATOR_PROMPT)


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_one_generation(
    model: torch.nn.Module,
    tokenizer: AutoTokenizer,
    system_prompt: str,
    tc: Dict[str, Any],
    gen_cfg: Dict[str, Any],
) -> Tuple[str, Optional[str]]:
    try:
        out = generate_response(
            model,
            tokenizer,
            system_prompt,
            str(tc.get("user_prompt", "")),
            gen_cfg,
        )
        return out, None
    except Exception as e:
        return "", str(e)


def build_output_item(
    tc: Dict[str, Any],
    model_output: str,
    error: Optional[str],
) -> Dict[str, Any]:
    return {
        "test_id": tc.get("test_id"),
        "category": tc.get("category"),
        "user_prompt": tc.get("user_prompt"),
        "ideal_challenge_should_cover": tc.get("ideal_challenge_should_cover"),
        "scoring_focus": tc.get("scoring_focus"),
        "model_output": model_output if not error else "",
        "timestamp": now_ts(),
        "error": error,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dual LoRA JSON benchmark for opposing counsel adapters.")
    p.add_argument("--benchmark_json", default="property_opposing_counsel_benchmark.json")
    p.add_argument("--base_model", default="Qwen/Qwen2.5-3B-Instruct")
    p.add_argument("--packfalse_adapter", default="./qwen-opposing-counsel-v1-r32-512-packfalse")
    p.add_argument("--packtrue_adapter", default="./qwen-opposing-counsel-v1-r32-512-packtrue")
    p.add_argument("--output_dir", default="./benchmark_outputs")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--load_in_4bit", type=str2bool, default=True)
    p.add_argument("--force", type=str2bool, default=False)
    p.add_argument("--run_order", default="by_model", choices=["per_test", "by_model"])
    p.add_argument("--max_new_tokens", type=int, default=280)
    p.add_argument("--temperature", type=float, default=0.45)
    p.add_argument("--top_p", type=float, default=0.85)
    p.add_argument("--repetition_penalty", type=float, default=1.12)
    p.add_argument("--do_sample", type=str2bool, default=True)
    return p.parse_args()


def resolve_device(arg_device: str) -> str:
    if arg_device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if arg_device == "cuda" and not torch.cuda.is_available():
        print("Warning: --device cuda requested but CUDA not available; using cpu.", file=sys.stderr)
        return "cpu"
    return arg_device


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    load_4bit = bool(args.load_in_4bit) and device == "cuda"

    try:
        args.packfalse_adapter = ensure_adapter_dir(args.packfalse_adapter)
        args.packtrue_adapter = ensure_adapter_dir(args.packtrue_adapter)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

    gen_cfg = {
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "repetition_penalty": args.repetition_penalty,
        "do_sample": args.do_sample,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    write_evaluator_prompt(args.output_dir)

    bench_path = args.benchmark_json
    with open(bench_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    system_prompt = (benchmark.get("system_prompt") or "").strip() or FALLBACK_SYSTEM_PROMPT
    test_cases: List[Dict[str, Any]] = benchmark.get("test_cases", [])
    total = len(test_cases)

    out_false = os.path.join(args.output_dir, "packfalse_outputs.json")
    out_true = os.path.join(args.output_dir, "packtrue_outputs.json")
    out_combined = os.path.join(args.output_dir, "combined_packfalse_packtrue_outputs.json")
    out_summary = os.path.join(args.output_dir, "run_summary.json")

    meta_false = {
        "base_model": args.base_model,
        "adapter_path": args.packfalse_adapter,
        "benchmark_file": os.path.basename(bench_path),
        "system_prompt": system_prompt,
        "generation_config": gen_cfg,
    }
    meta_true = {
        "base_model": args.base_model,
        "adapter_path": args.packtrue_adapter,
        "benchmark_file": os.path.basename(bench_path),
        "system_prompt": system_prompt,
        "generation_config": gen_cfg,
    }

    packfalse_data = load_existing_output_json(out_false, "packing_false", meta_false)
    packtrue_data = load_existing_output_json(out_true, "packing_true", meta_true)
    packfalse_data["generation_config"] = dict(gen_cfg)
    packtrue_data["generation_config"] = dict(gen_cfg)
    packfalse_data["system_prompt"] = system_prompt
    packtrue_data["system_prompt"] = system_prompt

    def save_all() -> None:
        save_output_json(out_false, packfalse_data)
        save_output_json(out_true, packtrue_data)
        combined = rebuild_combined(
            benchmark, packfalse_data, packtrue_data, args.base_model, system_prompt, gen_cfg
        )
        save_output_json(out_combined, combined)
        write_run_summary(out_summary, total, packfalse_data, packtrue_data)

    def process_adapter(
        adapter_path: str,
        model_label: str,
        data: Dict[str, Any],
        out_path: str,
        tests: List[Dict[str, Any]],
    ) -> None:
        nonlocal_pack = {"model": None, "tokenizer": None}

        def run_tests() -> None:
            model, tokenizer = load_model_with_adapter(
                args.base_model, adapter_path, device, load_4bit
            )
            nonlocal_pack["model"] = model
            nonlocal_pack["tokenizer"] = tokenizer
            try:
                for tc in tests:
                    tid = tc.get("test_id", "")
                    cat = tc.get("category", "")
                    user_prompt = str(tc.get("user_prompt", ""))

                    print(f"\n{'=' * 60}")
                    print(f"TEST {tid} | {cat}")
                    print(f"{'=' * 60}")
                    print("USER PROMPT:")
                    print(user_prompt)
                    print("-" * 60)

                    key = "packing_false" if model_label == "packfalse" else "packing_true"
                    label_upper = "PACKING_FALSE" if key == "packing_false" else "PACKING_TRUE"

                    if not args.force and has_test_output(data, tid):
                        print(f"Skipping {tid} for {key} because output already exists.")
                        continue

                    print(f"Running {key}...")
                    mo, err = run_one_generation(model, tokenizer, system_prompt, tc, gen_cfg)
                    item = build_output_item(tc, mo, err)
                    upsert_test_output(data, item, args.force)
                    save_output_json(out_path, data)
                    combined = rebuild_combined(
                        benchmark, packfalse_data, packtrue_data, args.base_model, system_prompt, gen_cfg
                    )
                    save_output_json(out_combined, combined)
                    write_run_summary(out_summary, total, packfalse_data, packtrue_data)

                    print(f"{label_upper} OUTPUT:")
                    print(mo if not err else f"[error] {err}")
                    print(f"Saved to {os.path.basename(out_path)}")
                    print("-" * 60)
                print(f"{'=' * 60}\n")
            finally:
                unload_model(nonlocal_pack["model"], nonlocal_pack["tokenizer"])
                nonlocal_pack["model"] = None
                nonlocal_pack["tokenizer"] = None

        run_tests()

    if args.run_order == "per_test":
        for tc in test_cases:
            tid = tc.get("test_id", "")
            cat = tc.get("category", "")
            user_prompt = str(tc.get("user_prompt", ""))

            print(f"\n{'=' * 60}")
            print(f"TEST {tid} | {cat}")
            print(f"{'=' * 60}")
            print("USER PROMPT:")
            print(user_prompt)
            print("-" * 60)

            for adapter_path, model_label, data, out_path, key, label_upper in (
                (
                    args.packfalse_adapter,
                    "packfalse",
                    packfalse_data,
                    out_false,
                    "packing_false",
                    "PACKING_FALSE",
                ),
                (
                    args.packtrue_adapter,
                    "packtrue",
                    packtrue_data,
                    out_true,
                    "packing_true",
                    "PACKING_TRUE",
                ),
            ):
                if not args.force and has_test_output(data, tid):
                    print(f"Skipping {tid} for {key} because output already exists.")
                    print("-" * 60)
                    continue

                print(f"Running {key}...")
                model, tokenizer = load_model_with_adapter(
                    args.base_model, adapter_path, device, load_4bit
                )
                try:
                    mo, err = run_one_generation(model, tokenizer, system_prompt, tc, gen_cfg)
                    item = build_output_item(tc, mo, err)
                    upsert_test_output(data, item, args.force)
                    save_output_json(out_path, data)
                    combined = rebuild_combined(
                        benchmark, packfalse_data, packtrue_data, args.base_model, system_prompt, gen_cfg
                    )
                    save_output_json(out_combined, combined)
                    write_run_summary(out_summary, total, packfalse_data, packtrue_data)
                finally:
                    unload_model(model, tokenizer)

                print(f"{label_upper} OUTPUT:")
                print(mo if not err else f"[error] {err}")
                print(f"Saved to {os.path.basename(out_path)}")
                print("-" * 60)

            print(f"{'=' * 60}\n")

    else:
        print("\n>>> run_order=by_model: running all test cases on packing_false, then packing_true.\n")
        process_adapter(
            args.packfalse_adapter, "packfalse", packfalse_data, out_false, test_cases
        )
        process_adapter(args.packtrue_adapter, "packtrue", packtrue_data, out_true, test_cases)

    save_all()

    print("\nExample commands:\n")
    print(
        "CUDA 4-bit command:\n"
        "python run_dual_model_json_benchmark.py --benchmark_json property_opposing_counsel_benchmark.json "
        "--base_model Qwen/Qwen2.5-3B-Instruct --packfalse_adapter ./qwen-opposing-counsel-v1-r32-512-packfalse "
        "--packtrue_adapter ./qwen-opposing-counsel-v1-r32-512-packtrue --output_dir ./benchmark_outputs "
        "--device cuda --load_in_4bit true\n"
    )
    print(
        "CUDA normal fp16 command:\n"
        "python run_dual_model_json_benchmark.py --benchmark_json property_opposing_counsel_benchmark.json "
        "--base_model Qwen/Qwen2.5-3B-Instruct --packfalse_adapter ./qwen-opposing-counsel-v1-r32-512-packfalse "
        "--packtrue_adapter ./qwen-opposing-counsel-v1-r32-512-packtrue --output_dir ./benchmark_outputs "
        "--device cuda --load_in_4bit false\n"
    )
    print(
        "CPU command:\n"
        "python run_dual_model_json_benchmark.py --benchmark_json property_opposing_counsel_benchmark.json "
        "--base_model Qwen/Qwen2.5-3B-Instruct --packfalse_adapter ./qwen-opposing-counsel-v1-r32-512-packfalse "
        "--packtrue_adapter ./qwen-opposing-counsel-v1-r32-512-packtrue --output_dir ./benchmark_outputs "
        "--device cpu --load_in_4bit false\n"
    )
    print(
        "Force regenerate:\n"
        "python run_dual_model_json_benchmark.py --force true\n"
    )
    print(
        "Fast by-model order:\n"
        "python run_dual_model_json_benchmark.py --run_order by_model\n"
    )


if __name__ == "__main__":
    main()
