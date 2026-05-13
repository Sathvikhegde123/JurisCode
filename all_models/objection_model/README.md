# Objection Model

This directory contains the LoRA adapter specifically trained to evaluate legal objections in the context of Indian property litigation.

## Components

- `adapter_model.safetensors`: The fine-tuned LoRA weights.
- `adapter_config.json`: Configuration for PEFT.
- `tokenizer_config.json` & `tokenizer.json`: Specialized tokenizer settings for the Qwen base model.
- `chat_template.jinja`: Template used to format objection evaluation prompts.

## Training Info

See `README.md` (if present) or the corresponding training notebooks in `ipynbFiles/` for details on training data and hyperparameters.
