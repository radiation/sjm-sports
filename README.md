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
DATABASE_URL=postgresql+psycopg://sjm:sjm@localhost:5432/sjm_sports
```

Set that environment variable or put it in a local `.env` file before running migrations against a real database. See `.env.example` for local development defaults.

## Docker Compose Harness

Start the app, PostgreSQL, and migrations:

```bash
docker compose up --build app
```

The containerized app will be available at <http://127.0.0.1:8000>.

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Run Alembic migrations through Docker Compose:

```bash
docker compose run --rm migrate
```

Build the web app image:

```bash
docker compose build app
```

Run the FastAPI app locally against the Compose database:

```bash
DATABASE_URL=postgresql+psycopg://sjm:sjm@localhost:5432/sjm_sports uv run uvicorn app.main:app --reload
```

Stop the harness:

```bash
docker compose down
```

Remove the database volume:

```bash
docker compose down -v
```

## Database Migrations

Apply migrations:

```bash
uv run alembic upgrade head
```

Create a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

## Roster Import

Import a cleaned roster workbook. XLSX files read the `Cleaned Data` worksheet by default:

```bash
uv run python -m app.importers.roster_spreadsheet data/raw/rosters.xlsx --year 2025
```

Override the worksheet name:

```bash
uv run python -m app.importers.roster_spreadsheet data/raw/rosters.xlsx --year 2025 --sheet "Cleaned Data"
```

CSV files with the same normalized columns are also supported:

```bash
uv run python -m app.importers.roster_spreadsheet data/raw/rosters.csv --year 2025
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
