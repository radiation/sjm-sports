# Copilot Instructions — SJM Sports Recruiting Portal

## Project Overview

This project is a small internal web portal for collecting, normalizing, searching, and exporting NCAA Division I baseball roster and coaching data.

The application should support:

- Scraping roster and staff information from D1 school websites.
- Normalizing players, coaches, colleges, high schools, positions, and yearly roster/staff assignments.
- Searching players, coaches, colleges, transfers, positions, and recruiting-relevant fields.
- Exporting filtered results to CSV for use in Excel.
- Keeping the implementation simple, maintainable, and easy to operate for a small non-technical user base.

This is not a high-scale application. Prefer clarity, correctness, and maintainability over premature performance optimization.

## Technology Stack

Use the following stack unless explicitly instructed otherwise:

- Python 3.13+
- FastAPI
- HTMX
- Jinja2 templates
- SQLAlchemy 2.x ORM
- Alembic for database migrations
- PostgreSQL as the primary database
- Pydantic for request/response schemas and validation
- pytest for tests
- Ruff for linting and formatting
- mypy for type checking where practical
- uv for dependency management

Avoid introducing heavy frontend frameworks unless explicitly requested. The default UI should be server-rendered HTML with HTMX enhancements.

## Preferred Project Layout

Use this layout unless explicitly instructed otherwise:

- app/
  - main.py
  - core/
    - config.py
    - database.py
    - logging.py
  - models/
  - schemas/
  - repositories/
  - services/
  - importers/
  - scrapers/
  - web/
    - routes/
    - templates/
    - static/
  - api/
    - routes/
  - utils/
- alembic/
  - versions/
- tests/
  - unit/
  - integration/

## Architectural Principles

Use a layered architecture with clear boundaries.

### Boundary Rules

These rules are important and should be preserved across all changes.

1. No database calls in route handlers.

FastAPI route handlers should call services. Route handlers should handle HTTP concerns only: request parsing, response rendering, redirects, status codes, and dependency injection.

2. No database calls in business logic outside repositories.

Services should not directly use SQLAlchemy queries. Services should depend on repository interfaces/classes.

3. No business logic in repositories.

Repositories should only perform persistence operations. Repositories may encapsulate query construction and database access. Repositories should not decide recruiting logic, scraping normalization rules, transfer logic, or application workflows.

4. Services coordinate application behavior.

Services own business workflows such as importing scraped records, matching players, creating yearly roster assignments, and generating export data. Services may call multiple repositories. Services should be easy to unit test with fake repositories.

5. Scrapers collect raw source data.

Scrapers should fetch and parse website content. Scrapers should return raw or lightly structured scrape records. Scrapers should not directly write to the database.

6. Importers normalize and load data.

Importers should transform raw scrape records or spreadsheet rows into application-level commands/data structures. Importers should call services to persist data. Importers should not directly use SQLAlchemy sessions.

7. Models represent persistence.

SQLAlchemy models belong in app/models. Keep models focused on database structure and relationships. Avoid putting business methods on ORM models unless they are trivial and persistence-focused.

8. Schemas represent data transfer.

Pydantic schemas belong in app/schemas. Use schemas for API input/output, importer records, scraper records, and service command objects.

## Database and Migration Rules

Use Alembic for all schema changes.

- Do not modify existing Alembic migrations after they have been committed unless explicitly asked.
- Create a new migration for each schema change.
- Use clear migration names.
- Prefer additive migrations.
- Keep migration logic deterministic.
- SQLAlchemy models and Alembic migrations must stay in sync.
- Use integer primary keys unless there is a strong reason not to.
- Use explicit indexes for fields used in search, joins, or filtering.

Use timestamps on durable tables:

- created_at
- updated_at

## Domain Model Guidance

The core model should remain simple.

Primary entities:

- people
- players
- coaches
- colleges
- high_schools
- positions
- player_rosters
- coach_assignments
- scrape_runs
- scrape_pages

Use a simple integer year for season/year tracking. Do not introduce a seasons table unless explicitly requested.

College baseball seasons are represented by the year in which the season is played.

Example:

- 2025 season = spring 2025 baseball season

## People

Use people as the shared identity table for humans.

Players and coaches should reference people.

A person may theoretically be both a former player and a coach, so avoid duplicating identity data unnecessarily.

Recommended fields:

- id
- first_name
- last_name
- full_name
- created_at
- updated_at

## Players

Player-specific data may include:

- person_id
- bats
- throws
- height_inches
- weight_lbs
- hometown_city
- hometown_state
- hometown_country
- created_at
- updated_at

Do not store player roster assignment data directly on the players table.

## Player Rosters

Use player_rosters for year-specific player assignment data.

A player roster row represents:

- player + college + year

Roster-specific fields may include:

- player_id
- college_id
- year
- roster_year
- normalized_roster_year
- primary_position_id
- positions_raw
- high_school_id
- previous_college_id
- previous_school_raw
- is_transfer
- jersey_number
- roster_url
- profile_url
- created_at
- updated_at

Use positions_raw for the original scraped position string. Use primary_position_id for normalized searching/filtering.

Do not introduce a player-position join table unless explicitly requested. Multiple positions can be handled later if needed.

Recommended unique constraint:

- player_id + college_id + year

## Coaches

Coach-specific information should live in coaches.

Recommended fields:

- id
- person_id
- created_at
- updated_at

Year-specific coaching assignments should live in coach_assignments.

## Coach Assignments

A coach assignment represents:

- coach + college + year + role/title

Coach titles should use the shared positions table with position_type = coach.

Also preserve the raw scraped title in title_raw.

Recommended fields:

- coach_id
- college_id
- year
- position_id
- title_raw
- bio_url
- staff_url
- created_at
- updated_at

## Colleges

Use colleges for NCAA schools.

Recommended fields:

- id
- name
- state
- division
- conference
- ncaa_school_id
- ipeds_id
- roster_url
- staff_url
- created_at
- updated_at

For now, keep conference as a simple string on colleges. Do not create conference membership history unless explicitly requested.

## High Schools

Use a separate high_schools table.

Recommended fields:

- id
- name
- city
- state
- country
- created_at
- updated_at

Do not use a generic schools abstraction unless explicitly requested. The distinction between colleges and high schools should remain obvious.

## Positions

Use one shared positions table for both player positions and coach roles.

Recommended fields:

- id
- code
- name
- position_type
- position_group
- created_at
- updated_at

Examples:

- RHP | Right-Handed Pitcher | player | pitcher
- LHP | Left-Handed Pitcher | player | pitcher
- C | Catcher | player | catcher
- INF | Infielder | player | infield
- OF | Outfielder | player | outfield
- Head Coach | Head Coach | coach | staff
- Pitching Coach | Pitching Coach | coach | staff
- Recruiting Coordinator | Recruiting Coordinator | coach | staff

## Scraping Rules

Scraping should be repeatable and observable.

For each scrape run, record:

- year
- source
- started_at
- finished_at
- status
- notes

For each scraped page, record:

- scrape_run_id
- college_id when known
- url
- page_type
- status_code
- fetched_at
- content_hash
- error_message when applicable

Scrapers should be defensive because college athletics websites vary widely.

When scraping:

- Preserve raw source values where useful.
- Normalize only when confidence is high.
- Avoid throwing away ambiguous data.
- Prefer partial success over failing an entire scrape run.
- Capture errors in a structured way.

## Import Rules

Importers should handle data from scraped pages, CSV files, spreadsheets, or future sources.

Importers should:

- Accept structured input records.
- Normalize obvious values such as position names, roster year, height, weight, and handedness.
- Preserve raw values when normalization is uncertain.
- Call service-layer methods to persist data.
- Avoid direct SQLAlchemy usage.
- Return useful summaries of created, updated, skipped, and failed records.

## CSV Export Rules

CSV export is a first-class workflow.

Exports should be generated from service-layer methods, not directly from route handlers or repositories.

Exports should support common filters such as:

- year
- college
- conference
- state
- position
- roster year
- transfer status
- previous college
- high school
- hometown state

Keep exported column names human-readable and Excel-friendly.

## Testing Expectations

Add or update tests for meaningful behavior.

Prefer unit tests for:

- services
- normalization logic
- importers
- scraper parsers
- CSV export generation

Use integration tests for:

- repository behavior
- database constraints
- FastAPI route behavior where useful

Tests should not require live external websites. Scraper tests should use saved HTML fixtures or mocked responses.

## Style Preferences

- Prefer simple, explicit code.
- Avoid clever abstractions.
- Use type hints.
- Keep functions small and focused.
- Favor readable names over terse names.
- Do not introduce unnecessary dependencies.
- Avoid premature async complexity unless FastAPI or the HTTP client makes it clearly useful.
- Prefer dependency injection patterns that make tests straightforward.

## Error Handling

Use explicit domain-level exceptions where helpful.

Do not swallow errors silently.

For scraping/importing workflows, capture row-level or page-level failures while allowing the overall run to continue when possible.

## What Not To Do

Do not:

- Put SQLAlchemy queries in FastAPI route handlers.
- Put SQLAlchemy queries in services.
- Put business rules in repositories.
- Add Celery, Redis, Kafka, or background worker infrastructure unless explicitly requested.
- Add React, Next.js, or a SPA frontend unless explicitly requested.
- Over-normalize the schema prematurely.
- Add a seasons table.
- Add conference history tables.
- Add a generic schools table.
- Add player-position many-to-many tables unless explicitly requested.
- Build live website scraping into tests.