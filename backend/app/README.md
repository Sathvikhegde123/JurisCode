# Backend Application Structure

This directory contains the core logic of the JurisCode Bharat FastAPI application.

## Directory Structure

- `core/`: Centralized configuration and model management logic.
- `routers/`: API endpoint definitions (Premise, Opposing, Objection, Practice).
- `services/`: Business logic and orchestration between routers and models.
- `schemas/`: Pydantic models for request/response validation.
- `utils/`: Reusable utility functions for text processing.

## Entry Point

- `main.py`: Initializes the FastAPI application, sets up middleware, and includes all routers. It also handles the application lifespan (model loading on startup).
