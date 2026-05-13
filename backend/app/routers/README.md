# API Routers

This folder contains the modular route definitions for the JurisCode Bharat API.

## Available Routers

- `premise.py`: Case premise generation endpoints.
- `opposing.py`: Opposing counsel simulation endpoints.
- `objection.py`: Objection evaluation and feedback endpoints.
- `practice.py`: Integrated practice session logic.
- `health.py`: Basic health check and model status monitoring.

## Common Pattern

Each router typically:
1. Defines its own `APIRouter`.
2. Uses Pydantic schemas from `app.schemas`.
3. Calls business logic from `app.services`.
4. Handles HTTP error responses.
