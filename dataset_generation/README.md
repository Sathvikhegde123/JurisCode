# Dataset Generation

This folder contains scripts and source data used to create the training datasets for the JurisCode Bharat LoRA adapters.

## Scripts

- `generate_dataset.py`: Main script for generating synthetic legal data.
- `premise_generation.py`: Specific logic for creating case premises.
- `changing_system_promt_opposing.py`: Utility for adjusting system prompts for dataset diversity.
- `test_objection.jsonl` / `train_objection.jsonl`: Datasets for the objection evaluator model.
- `property_litigation_opposing_counsel_dataset_3000_updated.jsonl`: Large-scale dataset for opposing counsel training.

## Usage

These scripts are typically used during the research and development phase to prepare fine-tuning data for the Qwen base model.
