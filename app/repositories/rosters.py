from __future__ import annotations

from sqlalchemy import select

from app.models.people import Person, Player
from app.models.rosters import CoachAssignment, PlayerRoster
from app.repositories.base import Repository


class PlayerRosterRepository(Repository[PlayerRoster]):
    def get(self, roster_id: int) -> PlayerRoster | None:
        return self.session.get(PlayerRoster, roster_id)

    def add(self, roster: PlayerRoster) -> PlayerRoster:
        self.session.add(roster)
        self.session.flush()
        return roster

    def get_by_player_college_year(
        self, player_id: int, college_id: int, year: int
    ) -> PlayerRoster | None:
        return self.session.scalar(
            select(PlayerRoster).where(
                PlayerRoster.player_id == player_id,
                PlayerRoster.college_id == college_id,
                PlayerRoster.year == year,
            )
        )

    def get_by_college_year_player_name(
        self, college_id: int, year: int, full_name: str
    ) -> PlayerRoster | None:
        return self.session.scalar(
            select(PlayerRoster)
            .join(Player, PlayerRoster.player_id == Player.id)
            .join(Person, Player.person_id == Person.id)
            .where(
                PlayerRoster.college_id == college_id,
                PlayerRoster.year == year,
                Person.full_name == full_name,
            )
        )


class CoachAssignmentRepository(Repository[CoachAssignment]):
    def get(self, assignment_id: int) -> CoachAssignment | None:
        return self.session.get(CoachAssignment, assignment_id)

    def add(self, assignment: CoachAssignment) -> CoachAssignment:
        self.session.add(assignment)
        return assignment
