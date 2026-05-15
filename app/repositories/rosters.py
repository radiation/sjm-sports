from __future__ import annotations

from app.models.rosters import CoachAssignment, PlayerRoster
from app.repositories.base import Repository


class PlayerRosterRepository(Repository[PlayerRoster]):
    def get(self, roster_id: int) -> PlayerRoster | None:
        return self.session.get(PlayerRoster, roster_id)

    def add(self, roster: PlayerRoster) -> PlayerRoster:
        self.session.add(roster)
        return roster


class CoachAssignmentRepository(Repository[CoachAssignment]):
    def get(self, assignment_id: int) -> CoachAssignment | None:
        return self.session.get(CoachAssignment, assignment_id)

    def add(self, assignment: CoachAssignment) -> CoachAssignment:
        self.session.add(assignment)
        return assignment
