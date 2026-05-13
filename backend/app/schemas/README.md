# Data Schemas

This directory contains Pydantic models used for request validation and response serialization.

## Key Schemas

- `premise.py`: Models for premise generation requests and results.
- `opposing.py`: Models for interacting with the opposing counsel simulator.
- `objection.py`: Models for sending responses for objection evaluation.
- `practice.py`: Generic models for mock trial sessions.

## Purpose

Using Pydantic ensures type safety, automatic documentation (Swagger UI), and consistent data structures across the application.
