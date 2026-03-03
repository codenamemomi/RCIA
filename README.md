# RCIA Project

Project structured based on `refond_backend`.

## Project Structure

- `alembic/`: Database migrations.
- `api/`: API endpoints and core logic.
  - `db/`: Database session management.
  - `utils/`: Shared utilities.
  - `v1/`: Version 1 of the API.
- `core/`: Core settings, security, and task queue configuration.
- `scripts/`: Useful scripts.
- `test/`: Unit and integration tests.

## Setup

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and update values.
5. Run the app: `uvicorn main:app --reload`
