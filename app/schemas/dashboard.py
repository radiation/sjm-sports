from __future__ import annotations

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_colleges: int
    total_players: int
    total_roster_records: int
    total_transfers: int
    available_years: list[int]
