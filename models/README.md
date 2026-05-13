# Models Directory

This directory contains the production-ready LoRA adapters used by the backend application.

## Structure

Each subdirectory corresponds to a specific legal reasoning task:

- `opposing-counsel/`: LoRA adapter for simulating opposing counsel in property litigation.
- `premise_generator_lora/`: (Referenced in config) Adapter for generating legal case premises.
- `objection_evaluator_lora/`: (Referenced in config) Adapter for evaluating legal objections.

## Contents of an Adapter Folder

Each adapter folder typically contains:
- `adapter_config.json`: PEFT configuration.
- `adapter_model.safetensors`: The trained LoRA weights.
- `tokenizer_config.json`: Tokenizer settings.
- `chat_template.jinja`: Template for formatting prompts.
