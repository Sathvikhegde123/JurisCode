# Premise adapter packing mapping — partial confirmation

## What could be confirmed

- **`qwen-property-premise-generator-v1-r32`** (and checkpoints under it): the current `qwen25_premise_generator_lora_training.ipynb` in this folder sets `OUTPUT_DIR = "./qwen-property-premise-generator-v1-r32"` and **`packing=False`** in `SFTConfig`. That is **strong evidence** this run corresponds to **packing = False**.

## What could not be confirmed from repo metadata

- **`qwen-property-premise-generator-v2-r32`**: `trainer_state.json` files under this tree do **not** record a `packing` flag. There is **no** second notebook cell or saved config in-repo that clearly states `packing=True` for v2.

## What was done for benchmarking convenience

- A full copy of **v1** was created as `qwen-property-premise-generator-pack-false-r32/` (aligned with notebook `packing=False`).
- A full copy of **v2** was created as `qwen-property-premise-generator-pack-true-r32/` **only as a working default for the dual benchmark script**. This **does not** prove v2 was trained with `packing=True`.

## Action for you

1. Confirm from your training notes or another machine which run used **`packing=True`**.
2. If **v2 is not** the packing-True run, **do not** rely on the folder name `pack-true-r32` for v2. Either re-copy the correct adapter into `qwen-property-premise-generator-pack-true-r32/`, or pass the correct path with:

   `python run_dual_premise_model_json_benchmark.py --pack_true_adapter "<path>" --pack_false_adapter "<path>"`

## Loose files under `premise_model/`

The repo root of `premise_model/` may still contain adapter/tokenizer/checkpoint files (e.g. `adapter_config.json` next to `checkpoint-200/`). Those were **not** deleted. Treat them as an extra export or duplicate; see `MODEL_ADAPTER_MAPPING.md`.
