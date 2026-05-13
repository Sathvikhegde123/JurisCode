# Opposing Counsel Production Model

This folder contains the production-ready LoRA adapter for the Opposing Counsel simulator.

## Files

- `adapter_model.safetensors`: The trained LoRA weights.
- `adapter_config.json`: PEFT configuration.
- `tokenizer_config.json` / `tokenizer.json`: Tokenizer settings.
- `chat_template.jinja`: Template for formatting interactions with the opposing counsel.

## Deployment

This model is loaded by the `ModelManager` when the `OPPOSING_COUNSEL_ADAPTER_PATH` is set to this directory in the backend `.env` file.
