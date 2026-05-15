# SJM Sports Recruiting Portal

Small internal FastAPI + HTMX portal for NCAA D1 baseball roster, staff, transfer, and recruiting data.

## Local Setup

Install dependencies with uv:

```bash
uv sync --dev
```

Run the development server:

```bash
uv run uvicorn app.main:app --reload
```

The app will be available at <http://127.0.0.1:8000>.

## Configuration

The default database URL points at a local PostgreSQL database:

```bash
SJM_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/sjm_sports
```

Set that environment variable or put it in a local `.env` file before running migrations against a real database.

## Database Migrations

Apply migrations:

```bash
uv run alembic upgrade head
```

Create a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

## Quality Checks

Format code:

```bash
uv run ruff format .
```

Lint code:

```bash
uv run ruff check .
```

Run type checks:

```bash
uv run mypy
```

Run tests:

```bash
uv run pytest
```

The default test run does not require PostgreSQL. Future database-dependent tests should be marked `requires_db` and run explicitly with:

```bash
SJM_RUN_DB_TESTS=1 uv run pytest
```
