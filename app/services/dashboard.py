from __future__ import annotations

from app.repositories.people import PlayerRepository
from app.repositories.rosters import PlayerRosterRepository
from app.repositories.schools import CollegeRepository
from app.schemas.dashboard import DashboardSummary


class DashboardService:
    def __init__(
        self,
        colleges: CollegeRepository,
        players: PlayerRepository,
        rosters: PlayerRosterRepository,
    ) -> None:
        self.colleges = colleges
        self.players = players
        self.rosters = rosters

    def get_summary(self) -> DashboardSummary:
        return DashboardSummary(
            total_colleges=self.colleges.count_all(),
            total_players=self.players.count_all(),
            total_roster_records=self.rosters.count_all(),
            total_transfers=self.rosters.count_transfers(),
            available_years=self.rosters.list_distinct_years(),
        )
