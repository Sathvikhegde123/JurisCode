# Opposing Counsel Models

This directory contains different versions and experiments for the Opposing Counsel simulator.

## Subdirectories

- `qwen-opposing-counsel-v1-r32-512-packfalse/`: Version 1 trained without sequence packing.
- `qwen-opposing-counsel-v1-r32-512-packtrue/`: Version 1 trained with sequence packing.

## Data

- `property_litigation_opposing_counsel_dataset_3000_updated.jsonl`: The dataset used for training these variants.
- `property_opposing_counsel_benchmark.json`: Benchmark configuration for this role.

## Scripts

- `run_dual_model_json_benchmark.py`: Utility to compare two variants of the opposing counsel model.
