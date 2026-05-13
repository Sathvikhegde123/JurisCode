#!/usr/bin/env python3
"""
Dual LoRA benchmark for Indian property-law premise generation.
Loads property_premise_benchmark.json; runs pack_true and pack_false adapters; saves JSON with resume.
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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

SCRIPT_DIR = Path(__file__).resolve().parent

EVALUATOR_PROMPT = """You are evaluating two fine-tuned Indian property-law premise-generation models.

You will receive:
1. property_premise_benchmark.json
2. pack_true_outputs.json
3. pack_false_outputs.json
or one combined_pack_true_pack_false_outputs.json

The task of each model:
Given a property-law topic, generate one realistic Indian property-law factual dispute scenario for legal training.

The model should generate:
- realistic Indian property-law dispute facts
- parties
- timeline
- documents
- possession facts
- ownership conflict
- evidentiary ambiguity
- procedural confusion
- family/property/builder/tenant/revenue disputes where relevant

The model should NOT generate:
- legal analysis
- legal advice
- judgments
- conclusions
- issue statements beginning with "Whether"
- bullet points
- opposing counsel arguments
- fake legal citations
- unrealistic fake document names

Evaluate each test case fairly using the provided benchmark rubric.

For each test case, return:
- test_id
- category
- pack_true score /10
- pack_false score /10
- winner: pack_true / pack_false / tie
- strengths of pack_true
- weaknesses of pack_true
- strengths of pack_false
- weaknesses of pack_false
- hallucination or fake/unrealistic legal fact found? yes/no
- whether output wrongly gives legal analysis/advice/conclusion? yes/no
- notes

Then provide:
- average score for both models
- winner count
- hallucination/unrealistic fact count
- repeated failure patterns
- final recommendation
- which model should be used as the production Premise Generator
- whether prompt tuning, inference parameter tuning, or dataset retraining is needed

Important:
Do not favor longer answers automatically.
Prefer realistic, fact-rich, Indian property-law-specific, role-consistent premises.
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
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def ensure_adapter_dir(adapter_path: str) -> str:
    resolved = resolve_local_path(adapter_path)
    if not os.path.isdir(resolved):
        raise FileNotFoundError(f"Adapter directory not found: {adapter_path!r} -> {resolved!r}")
    cfg = os.path.join(resolved, "adapter_config.json")
    if not os.path.isfile(cfg):
        raise FileNotFoundError("Not a PEFT adapter folder: missing adapter_config.json")
    weights = os.path.join(resolved, "adapter_model.safetensors")
    if not os.path.isfile(weights):
        raise FileNotFoundError(
            "This folder has adapter_config.json but does not contain adapter_model.safetensors, "
            "so it is not a complete PEFT LoRA adapter for inference."
        )
    return resolved


def find_candidate_adapters(project_root: str, max_depth: int = 3) -> List[str]:
    root = Path(resolve_local_path(project_root)).resolve()
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_parts = Path(dirpath).resolve().relative_to(root).parts
        if len(rel_parts) >= max_depth:
            dirnames[:] = []
        if "adapter_config.json" in filenames and "adapter_model.safetensors" in filenames:
            found.append(os.path.normpath(str(dirpath)))
    return sorted(set(found))


def name_slug(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name.strip())
    return s or "model"


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
        device_map = {"": 0}
    else:
        torch_dtype = torch.float32

    kwargs: Dict[str, Any] = {"trust_remote_code": True}
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


def unload_model(model: Optional[torch.nn.Module], tokenizer: Optional[Any]) -> None:
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
        im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
        if im_end_id is None or im_end_id < 0:
            im_end_id = int(tokenizer.eos_token_id)
        elif im_end_id == getattr(tokenizer, "unk_token_id", None):
            im_end_id = int(tokenizer.eos_token_id)
        return int(im_end_id)
    except Exception:
        return int(tokenizer.eos_token_id)


def _clean_assistant_text(text: str) -> str:
    if not text:
        return ""
    for tok in ("<|im_end|>", "<|endoftext|>", "<|im_start|>"):
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
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            **gen_kw,
        )
    new_tokens = outputs[0][input_ids.shape[-1] :]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return _clean_assistant_text(text)


def load_existing_output_json(path: str, model_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
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
    return any(o.get("test_id") == test_id for o in data.get("outputs", []))


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
    pack_true_data: Dict[str, Any],
    pack_false_data: Dict[str, Any],
    base_model: str,
    system_prompt: str,
    generation_config: Dict[str, Any],
    pack_true_name: str,
    pack_false_name: str,
) -> Dict[str, Any]:
    paired: List[Dict[str, Any]] = []
    for tc in benchmark.get("test_cases", []):
        tid = tc.get("test_id")
        pt = _get_output_for_test(pack_true_data, tid) if tid else None
        pf = _get_output_for_test(pack_false_data, tid) if tid else None
        paired.append(
            {
                "test_id": tid,
                "category": tc.get("category"),
                "user_prompt": tc.get("user_prompt"),
                "ideal_premise_should_include": tc.get("ideal_premise_should_include"),
                "scoring_focus": tc.get("scoring_focus"),
                "failure_flags": tc.get("failure_flags"),
                "pack_true_name": pack_true_name,
                "pack_false_name": pack_false_name,
                "pack_true_output": (pt or {}).get("model_output") or "",
                "pack_false_output": (pf or {}).get("model_output") or "",
                "pack_true_error": (pt or {}).get("error"),
                "pack_false_error": (pf or {}).get("error"),
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


def count_errors(data: Dict[str, Any]) -> int:
    return sum(1 for o in data.get("outputs", []) if o.get("error"))


def write_run_summary(
    path: str,
    total: int,
    pack_true_name: str,
    pack_false_name: str,
    pack_true_data: Dict[str, Any],
    pack_false_data: Dict[str, Any],
) -> None:
    summary = {
        "total_test_cases": total,
        "pack_true_name": pack_true_name,
        "pack_false_name": pack_false_name,
        "pack_true_completed": len(pack_true_data.get("outputs", [])),
        "pack_false_completed": len(pack_false_data.get("outputs", [])),
        "pack_true_errors": count_errors(pack_true_data),
        "pack_false_errors": count_errors(pack_false_data),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_output_json(path, summary)


def write_evaluator_prompt(output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    p = os.path.join(output_dir, "evaluator_prompt.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(EVALUATOR_PROMPT)


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_output_item(tc: Dict[str, Any], model_output: str, error: Optional[str]) -> Dict[str, Any]:
    return {
        "test_id": tc.get("test_id"),
        "category": tc.get("category"),
        "user_prompt": tc.get("user_prompt"),
        "ideal_premise_should_include": tc.get("ideal_premise_should_include"),
        "scoring_focus": tc.get("scoring_focus"),
        "failure_flags": tc.get("failure_flags"),
        "model_output": model_output if not error else "",
        "timestamp": now_ts(),
        "error": error,
    }


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


def resolve_benchmark_path(benchmark_json: str) -> str:
    p = resolve_local_path(benchmark_json)
    if os.path.isfile(p):
        return p
    alt = SCRIPT_DIR / benchmark_json
    if alt.is_file():
        return str(alt.resolve())
    return p


def resolve_device(arg_device: str) -> str:
    if arg_device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if arg_device == "cuda" and not torch.cuda.is_available():
        print("Warning: --device cuda requested but CUDA not available; using cpu.", file=sys.stderr)
        return "cpu"
    return arg_device


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dual premise-generator LoRA JSON benchmark (pack_true vs pack_false).")
    p.add_argument("--benchmark_json", default="property_premise_benchmark.json")
    p.add_argument("--base_model", default="Qwen/Qwen2.5-3B-Instruct")
    p.add_argument("--pack_true_adapter", default="./qwen-property-premise-generator-pack-true-r32")
    p.add_argument("--pack_false_adapter", default="./qwen-property-premise-generator-pack-false-r32")
    p.add_argument("--pack_true_name", default="pack_true")
    p.add_argument("--pack_false_name", default="pack_false")
    p.add_argument("--output_dir", default="./premise_benchmark_outputs")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--load_in_4bit", type=str2bool, default=True)
    p.add_argument("--force", type=str2bool, default=False)
    p.add_argument("--run_order", default="by_model", choices=["by_model", "per_test"])
    p.add_argument("--max_new_tokens", type=int, default=260)
    p.add_argument("--temperature", type=float, default=0.75)
    p.add_argument("--top_p", type=float, default=0.9)
    p.add_argument("--repetition_penalty", type=float, default=1.12)
    p.add_argument("--do_sample", type=str2bool, default=True)
    p.add_argument("--list_adapters", type=str2bool, default=False)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = str(SCRIPT_DIR)

    if args.list_adapters:
        cands = find_candidate_adapters(project_root, max_depth=3)
        print("Valid PEFT adapter folders (adapter_config.json + adapter_model.safetensors), depth <= 3:")
        for c in cands:
            print(f"  {c}")
        sys.exit(0)

    device = resolve_device(args.device)
    load_4bit = bool(args.load_in_4bit) and device == "cuda"

    gen_cfg = {
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "repetition_penalty": args.repetition_penalty,
        "do_sample": args.do_sample,
    }

    slug_true = name_slug(args.pack_true_name)
    slug_false = name_slug(args.pack_false_name)
    combined_name = f"combined_{slug_true}_{slug_false}_outputs.json"
    if slug_true == "pack_true" and slug_false == "pack_false":
        combined_name = "combined_pack_true_pack_false_outputs.json"

    try:
        args.pack_true_adapter = ensure_adapter_dir(args.pack_true_adapter)
        args.pack_false_adapter = ensure_adapter_dir(args.pack_false_adapter)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

    bench_path = resolve_benchmark_path(args.benchmark_json)
    if not os.path.isfile(bench_path):
        print(f"Benchmark file not found: {args.benchmark_json!r} (resolved: {bench_path!r})", file=sys.stderr)
        sys.exit(2)

    with open(bench_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    system_prompt = (benchmark.get("system_prompt") or "").strip()
    test_cases: List[Dict[str, Any]] = benchmark.get("test_cases", [])
    total = len(test_cases)

    out_dir = resolve_local_path(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    write_evaluator_prompt(out_dir)

    out_true = os.path.join(out_dir, f"{slug_true}_outputs.json")
    out_false = os.path.join(out_dir, f"{slug_false}_outputs.json")
    out_combined = os.path.join(out_dir, combined_name)
    out_summary = os.path.join(out_dir, "run_summary.json")

    meta_true = {
        "base_model": args.base_model,
        "adapter_path": args.pack_true_adapter,
        "benchmark_file": os.path.basename(bench_path),
        "system_prompt": system_prompt,
        "generation_config": gen_cfg,
    }
    meta_false = {
        "base_model": args.base_model,
        "adapter_path": args.pack_false_adapter,
        "benchmark_file": os.path.basename(bench_path),
        "system_prompt": system_prompt,
        "generation_config": gen_cfg,
    }

    pack_true_data = load_existing_output_json(out_true, args.pack_true_name, meta_true)
    pack_false_data = load_existing_output_json(out_false, args.pack_false_name, meta_false)
    pack_true_data["generation_config"] = dict(gen_cfg)
    pack_false_data["generation_config"] = dict(gen_cfg)
    pack_true_data["system_prompt"] = system_prompt
    pack_false_data["system_prompt"] = system_prompt
    pack_true_data["model_name"] = args.pack_true_name
    pack_false_data["model_name"] = args.pack_false_name

    def persist_all() -> None:
        save_output_json(out_true, pack_true_data)
        save_output_json(out_false, pack_false_data)
        combined = rebuild_combined(
            benchmark,
            pack_true_data,
            pack_false_data,
            args.base_model,
            system_prompt,
            gen_cfg,
            args.pack_true_name,
            args.pack_false_name,
        )
        save_output_json(out_combined, combined)
        write_run_summary(
            out_summary, total, args.pack_true_name, args.pack_false_name, pack_true_data, pack_false_data
        )

    def run_adapter_block(
        adapter_path: str,
        label: str,
        slug: str,
        data: Dict[str, Any],
        out_path: str,
        tests: List[Dict[str, Any]],
    ) -> None:
        print(f"\nLoading {label}...")
        model, tokenizer = load_model_with_adapter(args.base_model, adapter_path, device, load_4bit)
        try:
            print(f"Running all test cases on {label}...")
            for tc in tests:
                tid = tc.get("test_id", "")
                cat = tc.get("category", "")
                up = str(tc.get("user_prompt", ""))
                print(f"\n{'=' * 60}")
                print(f"TEST {tid} | {cat}")
                print(f"{'=' * 60}")
                print("USER PROMPT:")
                print(up)
                print("-" * 60)
                if not args.force and has_test_output(data, tid):
                    print(f"Skipping {tid} for {label} because output already exists.")
                    continue
                print(f"Running {label}...")
                mo, err = run_one_generation(model, tokenizer, system_prompt, tc, gen_cfg)
                item = build_output_item(tc, mo, err)
                upsert_test_output(data, item, args.force)
                save_output_json(out_path, data)
                combined = rebuild_combined(
                    benchmark,
                    pack_true_data,
                    pack_false_data,
                    args.base_model,
                    system_prompt,
                    gen_cfg,
                    args.pack_true_name,
                    args.pack_false_name,
                )
                save_output_json(out_combined, combined)
                write_run_summary(
                    out_summary, total, args.pack_true_name, args.pack_false_name, pack_true_data, pack_false_data
                )
                print(f"{label.upper()} OUTPUT:")
                print(mo if not err else f"[error] {err}")
                print(f"Saved to {os.path.basename(out_path)}")
                print("-" * 60)
        finally:
            print(f"Unloading {label}...")
            unload_model(model, tokenizer)

    if args.run_order == "by_model":
        run_adapter_block(
            args.pack_true_adapter, args.pack_true_name, slug_true, pack_true_data, out_true, test_cases
        )
        run_adapter_block(
            args.pack_false_adapter, args.pack_false_name, slug_false, pack_false_data, out_false, test_cases
        )
    else:
        for tc in test_cases:
            tid = tc.get("test_id", "")
            cat = tc.get("category", "")
            up = str(tc.get("user_prompt", ""))
            print(f"\n{'=' * 60}")
            print(f"TEST {tid} | {cat}")
            print(f"{'=' * 60}")
            print("USER PROMPT:")
            print(up)
            print("-" * 60)
            for adapter_path, label, slug, data, out_path in (
                (args.pack_true_adapter, args.pack_true_name, slug_true, pack_true_data, out_true),
                (args.pack_false_adapter, args.pack_false_name, slug_false, pack_false_data, out_false),
            ):
                if not args.force and has_test_output(data, tid):
                    print(f"Skipping {tid} for {label} because output already exists.")
                    print("-" * 60)
                    continue
                print(f"Running {label}...")
                model, tokenizer = load_model_with_adapter(args.base_model, adapter_path, device, load_4bit)
                try:
                    mo, err = run_one_generation(model, tokenizer, system_prompt, tc, gen_cfg)
                    item = build_output_item(tc, mo, err)
                    upsert_test_output(data, item, args.force)
                    save_output_json(out_path, data)
                    combined = rebuild_combined(
                        benchmark,
                        pack_true_data,
                        pack_false_data,
                        args.base_model,
                        system_prompt,
                        gen_cfg,
                        args.pack_true_name,
                        args.pack_false_name,
                    )
                    save_output_json(out_combined, combined)
                    write_run_summary(
                        out_summary,
                        total,
                        args.pack_true_name,
                        args.pack_false_name,
                        pack_true_data,
                        pack_false_data,
                    )
                finally:
                    unload_model(model, tokenizer)
                print(f"{label.upper()} OUTPUT:")
                print(mo if not err else f"[error] {err}")
                print(f"Saved to {os.path.basename(out_path)}")
                print("-" * 60)
            print(f"{'=' * 60}\n")

    persist_all()

    print("\nExample commands:\n")
    print("List valid adapters:\n")
    print("python run_dual_premise_model_json_benchmark.py --list_adapters true\n")
    print("Run benchmark on CUDA 4-bit:\n")
    print(
        "python run_dual_premise_model_json_benchmark.py --benchmark_json property_premise_benchmark.json "
        "--base_model Qwen/Qwen2.5-3B-Instruct --pack_true_adapter ./qwen-property-premise-generator-pack-true-r32 "
        "--pack_false_adapter ./qwen-property-premise-generator-pack-false-r32 --pack_true_name pack_true "
        "--pack_false_name pack_false --device cuda --load_in_4bit true --run_order by_model\n"
    )
    print("Run benchmark on CUDA fp16:\n")
    print(
        "python run_dual_premise_model_json_benchmark.py --benchmark_json property_premise_benchmark.json "
        "--base_model Qwen/Qwen2.5-3B-Instruct --pack_true_adapter ./qwen-property-premise-generator-pack-true-r32 "
        "--pack_false_adapter ./qwen-property-premise-generator-pack-false-r32 --pack_true_name pack_true "
        "--pack_false_name pack_false --device cuda --load_in_4bit false --run_order by_model\n"
    )
    print("Run benchmark on CPU:\n")
    print(
        "python run_dual_premise_model_json_benchmark.py --benchmark_json property_premise_benchmark.json "
        "--base_model Qwen/Qwen2.5-3B-Instruct --pack_true_adapter ./qwen-property-premise-generator-pack-true-r32 "
        "--pack_false_adapter ./qwen-property-premise-generator-pack-false-r32 --pack_true_name pack_true "
        "--pack_false_name pack_false --device cpu --load_in_4bit false --run_order by_model\n"
    )
    print("Force regenerate:\n")
    print("python run_dual_premise_model_json_benchmark.py --force true\n")
    print("Use per-test order:\n")
    print("python run_dual_premise_model_json_benchmark.py --run_order per_test\n")


if __name__ == "__main__":
    main()
