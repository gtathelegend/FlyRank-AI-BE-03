# Task Manager API - AI Version

An alternative implementation of the Task Management backend using a **Repository Pattern** to separate data access concerns from API routing.

## Architecture

This version introduces the following architectural design choices:
1. **Repository Abstraction (`TaskRepository`)**: All PostgreSQL operations are encapsulated inside a single class, separating raw parameterized SQL queries from the FastAPI route logic.
2. **Modular Architecture**: Uses clear, separated modules for database initialization (`database.py`), data repository (`repository.py`), seeding (`seed.py`), and routes (`main.py`).

## Quick Start

Start the stack:
```bash
docker compose up --build
```
The API is available at `http://127.0.0.1:8001` and Swagger UI is at `http://127.0.0.1:8001/docs`.
