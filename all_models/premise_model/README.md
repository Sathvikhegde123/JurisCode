# Premise Models

This directory contains various iterations of the Premise Generator model, which creates realistic legal case foundations for property litigation.

## Model Variants

- `v1-r32`, `v2-r32`: Progressive versions of the premise generator.
- `pack-true-r32`, `pack-false-r32`: Experiments testing the impact of sequence packing during fine-tuning.

## Documentation

- `MODEL_ADAPTER_MAPPING.md`: Documentation of which adapter corresponds to which version.
- `MODEL_MAPPING_NEEDED.md`: Pending mapping tasks.

## Data & Benchmarks

- `property_premise_dataset.jsonl` / `property_premise_dataset_train_ready.jsonl`: Training datasets.
- `property_premise_benchmark.json`: Evaluation benchmark for premise generation.
- `run_dual_premise_model_json_benchmark.py`: Comparative benchmarking script.
