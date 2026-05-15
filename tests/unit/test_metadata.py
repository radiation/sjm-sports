from __future__ import annotations

import app.models  # noqa: F401
from app.core.database import Base


def test_metadata_contains_initial_domain_tables() -> None:
    expected_tables = {
        "people",
        "players",
        "coaches",
        "colleges",
        "high_schools",
        "positions",
        "player_rosters",
        "coach_assignments",
        "scrape_runs",
        "scrape_pages",
    }

    assert expected_tables <= set(Base.metadata.tables)
