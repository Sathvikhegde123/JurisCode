# Core Module

The `core` module contains the fundamental components that drive the backend application.

## Components

### 1. `config.py`
- Manages environment variables and application settings.
- Handles path resolution for models and adapters.
- Sets default parameters for LLM generation.

### 2. `model_manager.py`
- Implements the **Singleton** `ModelManager`.
- Responsible for loading the base Qwen2.5 model and tokenizer.
- Dynamically switches between PEFT (LoRA) adapters for different roles.
- Provides a unified `generate` method for text inference.
- Handles both CUDA and CPU execution modes.
