# Services

This folder contains the business logic services that bridge the gap between API routers and the model inference engine.

## Core Services

### 1. `generation_service.py`
- Orchestrates the text generation process.
- Selects the appropriate system prompt based on the role.
- Coordinates with `ModelManager` to activate the correct LoRA adapter.
- Handles parameter overrides (temperature, max tokens).

### 2. `session_service.py`
- Manages user session state and history during interactive practice sessions.
