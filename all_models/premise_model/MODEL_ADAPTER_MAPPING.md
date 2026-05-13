# Premise LoRA adapter mapping and copies

## Valid complete adapters found (both `adapter_config.json` + `adapter_model.safetensors`)

| Path | adapter_config | adapter_model.safetensors | tokenizer files |
|------|----------------|---------------------------|-----------------|
| `premise_model/qwen-property-premise-generator-v1-r32` (root) | yes | yes | yes |
| `premise_model/qwen-property-premise-generator-v1-r32/checkpoint-600` | yes | yes | yes |
| `premise_model/qwen-property-premise-generator-v1-r32/checkpoint-1014` | yes | yes | yes |
| `premise_model/qwen-property-premise-generator-v2-r32` (root) | yes | yes | yes |
| `premise_model/qwen-property-premise-generator-v2-r32/checkpoint-200` | yes | yes | yes |
| `premise_model/qwen-property-premise-generator-v2-r32/checkpoint-255` | yes | yes | yes |
| `premise_model/` (loose root) | yes | yes | yes |
| `premise_model/checkpoint-200` | yes | yes | yes |
| `premise_model/checkpoint-255` | yes | yes | yes |

Checkpoints are valid PEFT saves but are **intermediate** exports; prefer **run root** folders for inference unless you intentionally want a specific step.

## Canonical benchmark folders (full tree copies; originals preserved)

| Role | New folder | Copied from | Packing evidence |
|------|------------|-------------|-------------------|
| **pack_false** | `qwen-property-premise-generator-pack-false-r32/` | `qwen-property-premise-generator-v1-r32/` | Notebook: `OUTPUT_DIR` targets v1 and `packing=False`. |
| **pack_true** (provisional) | `qwen-property-premise-generator-pack-true-r32/` | `qwen-property-premise-generator-v2-r32/` | **Not verified** in `trainer_state.json` / README. Copied so defaults exist; **confirm or replace** (see `MODEL_MAPPING_NEEDED.md`). |

Copy method: PowerShell `Copy-Item -Recurse` (no originals deleted). Targets did not exist before copy.

## Files copied per tree

Each canonical folder includes (where present in source): `adapter_config.json`, `adapter_model.safetensors`, `tokenizer.json`, `tokenizer_config.json`, `chat_template.jinja`, `README.md`, checkpoint subfolders, and `special_tokens_map.json` if it existed in the source.

## Loose `premise_model/` root adapter files

Not removed. Likely a duplicate export aligned with v2 checkpoints (`checkpoint-200`, `checkpoint-255`). Safe to ignore for the dual script if you use the canonical `pack-*` folders or explicit `--pack_true_adapter` / `--pack_false_adapter`.
