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

## School Source Seed

The source workbook lives locally at `data/raw/NCAA Roster Data Cleaned.xlsx` and is not committed. The checked-in seed file is `data/schools.csv`.

Regenerate the seed CSV from the workbook:

```bash
uv run python scripts/build_school_sources.py
```

`scripts/build_school_sources.py` is deterministic and offline-friendly. It only reads the local workbook and does not make network requests.

Import the deterministic offline seed CSV into the database:

```bash
uv run python -m app.importers.school_sources data/schools.csv
```

Optionally verify roster vendors from live roster HTML and write a reviewed CSV:

```bash
uv run python -m app.importers.verify_school_vendors data/schools.csv
```

By default that writes `data/schools.verified.csv`. Use `--in-place` to overwrite the input CSV.

The recommended reviewed import source is `data/schools.verified.csv` after you run vendor verification and review any failures or unknowns:

```bash
uv run python -m app.importers.school_sources data/schools.verified.csv
```

The importer accepts either CSV explicitly, so you can still import the deterministic offline seed when needed:

```bash
uv run python -m app.importers.school_sources data/schools.csv
```

`is_sidearm` in the seed builder output is a deterministic first-pass URL heuristic. After the optional verifier runs, `is_sidearm` reflects the stronger HTML/content-based vendor check for rows that were successfully fetched.

TLS certificate verification remains enabled during vendor verification. SSL failures are recorded in the reviewed CSV notes, for example `vendor_verification_failed: ssl_certificate_verify_failed`.

## Sidearm Roster Import

Use `data/schools.verified.csv` to choose one verified Sidearm school where `roster_vendor=sidearm`, `is_sidearm=True`, and `import_enabled=True`.

Example Georgetown row in the reviewed CSV:

```bash
rg '^S66,' data/schools.verified.csv
```

Import one Sidearm baseball roster for one school and one season:

```bash
uv run python -m app.importers.sidearm_roster --schools-csv data/schools.verified.csv --school-id S66 --season 2026
```

Override the source CSV or roster URL if needed:

```bash
uv run python -m app.importers.sidearm_roster --school-id S66 --season 2026 --schools-csv data/schools.verified.csv
uv run python -m app.importers.sidearm_roster --school-id S66 --season 2026 --url https://guhoyas.com/sports/baseball/roster
```

Run a small controlled batch instead of importing all verified Sidearm schools by default:

```bash
uv run python -m app.importers.sidearm_roster --schools-csv data/schools.verified.csv --season 2026 --limit 5
```

Dry-run the same batch without committing database changes:

```bash
uv run python -m app.importers.sidearm_roster --schools-csv data/schools.verified.csv --season 2026 --limit 5 --dry-run
```

When you are ready for a larger run, scale up deliberately:

```bash
uv run python -m app.importers.sidearm_roster --schools-csv data/schools.verified.csv --season 2026 --limit 25
uv run python -m app.importers.sidearm_roster --schools-csv data/schools.verified.csv --season 2026 --all-schools
```

Batch mode reads `data/schools.verified.csv`, filters to rows with `roster_vendor=sidearm`, `is_sidearm=True`, `import_enabled=True`, and a non-empty `roster_url`, then processes each school independently so one failure does not abort the whole run.

The recommended rollout is:

```text
1. Georgetown or another known-good single school
2. A 5-school batch
3. A 25-school batch
4. Review failures
5. Only then run --all-schools
```

Batch summaries report:

```text
schools_seen
schools_eligible
schools_attempted
schools_imported
schools_failed
players_seen
players_imported
players_updated
roster_rows_created
roster_rows_updated
failures_by_reason
failure_report_path
```

`schools_seen` is the total CSV row count. `schools_eligible` is the count that passed the Sidearm filters. `schools_attempted` is the number actually processed after `--limit` or `--school-id` selection. `failure_report_path` is present when a JSON failure report is written.

Batch failures are grouped by reason and written to JSON when any school fails. The default path is:

```text
data/import_runs/sidearm_roster_failures_2026.json
```

Review the JSON report after each controlled batch to separate stale URLs, SSL issues, and parser-template failures before increasing batch size.

The current Sidearm parser supports two template families:

```text
legacy Sidearm table/list template
newer Sidearm c-rosterpage / s-person-card template
```

The current Sidearm slice imports:

```text
first_name
last_name
jersey_number
position
academic_year
height
weight
bats
throws
hometown
high_school
previous_school
roster year / season
roster_url
profile_url
```

Idempotency for this first slice is conservative and scoped to `school + season + player full_name`. Re-running the same import updates the existing roster rows instead of creating duplicates.

Parser fixtures live under `tests/fixtures/sidearm/`. Capture fixtures from live Sidearm pages once, save the HTML locally, then keep parser tests offline against those saved files. Current fixture coverage includes the Georgetown legacy template plus newer `s-person-card` pages such as Boston College and Louisville.

Use these commands to rerun imports while debugging parser changes:

```bash
uv run python -m app.importers.sidearm_roster --school-id S66 --season 2026
uv run python -m app.importers.sidearm_roster --season 2026 --limit 5
```

Common failure reasons in batch output:

```text
stale_url_or_not_found: the reviewed roster URL is stale, the domain changed, or the page returned HTTP 404
ssl_certificate_verify_failed: TLS verification failed and was not bypassed
timeout: the roster page did not respond before the importer timeout
fetch_failed: another HTTP transport or non-404 status failure occurred
no_supported_sidearm_roster_template_found: the page does not match either supported Sidearm template family
person_card_template_detected_but_no_cards: the newer Sidearm roster container was present but no player cards were found
legacy_template_detected_but_no_rows: the legacy Sidearm template was detected but no player rows parsed
supported_template_found_but_no_player_cards: a supported template was present but no player entries could be extracted
title_mismatch: recorded as a diagnostic warning when expected season text is missing from the checked headings; it does not fail a successful parse by itself
```

Current provenance is stored through existing fields and timestamps: school source metadata on `colleges`, plus `roster_url`, `profile_url`, and model timestamps on imported roster rows.

Out of scope for this slice: scheduling, all-vendor ingestion, PrestoSports parsing, stale URL repair or discovery, unknown-vendor parsing, and broader cross-school identity matching.

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
