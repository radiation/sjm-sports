from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, or_, select

from app.models.people import Person, Player
from app.models.positions import Position
from app.models.rosters import CoachAssignment, PlayerRoster
from app.models.schools import College, HighSchool
from app.repositories.base import Repository
from app.schemas.players import PlayerSearchFilters, PlayerSearchResult


class PlayerRosterRepository(Repository[PlayerRoster]):
    def get(self, roster_id: int) -> PlayerRoster | None:
        return self.session.get(PlayerRoster, roster_id)

    def add(self, roster: PlayerRoster) -> PlayerRoster:
        self.session.add(roster)
        self.session.flush()
        return roster

    def count_all(self) -> int:
        return self.session.scalar(select(func.count(PlayerRoster.id))) or 0

    def count_transfers(self) -> int:
        return (
            self.session.scalar(
                select(func.count(PlayerRoster.id)).where(PlayerRoster.is_transfer.is_(True))
            )
            or 0
        )

    def list_distinct_years(self) -> list[int]:
        years = self.session.scalars(
            select(PlayerRoster.year).distinct().order_by(PlayerRoster.year.desc())
        ).all()
        return list(years)

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

    def count_search_results(self, filters: PlayerSearchFilters) -> int:
        statement = self._apply_search_filters(
            select(func.count(PlayerRoster.id))
            .select_from(PlayerRoster)
            .join(Player, PlayerRoster.player_id == Player.id)
            .join(Person, Player.person_id == Person.id)
            .join(College, PlayerRoster.college_id == College.id)
            .outerjoin(Position, PlayerRoster.primary_position_id == Position.id)
            .outerjoin(HighSchool, PlayerRoster.high_school_id == HighSchool.id),
            filters,
        )
        return self.session.scalar(statement) or 0

    def search(
        self, filters: PlayerSearchFilters, limit: int, offset: int
    ) -> list[PlayerSearchResult]:
        statement = (
            select(
                Person.full_name.label("player_name"),
                College.name.label("college"),
                College.conference.label("conference"),
                PlayerRoster.year.label("year"),
                Position.code.label("position"),
                PlayerRoster.positions_raw.label("positions_raw"),
                PlayerRoster.roster_year.label("roster_year"),
                PlayerRoster.normalized_roster_year.label("normalized_roster_year"),
                Player.height_inches.label("height_inches"),
                Player.weight_lbs.label("weight_lbs"),
                Player.bats.label("bats"),
                Player.throws.label("throws"),
                Player.hometown_city.label("hometown_city"),
                Player.hometown_state.label("hometown_state"),
                Player.hometown_country.label("hometown_country"),
                HighSchool.name.label("high_school"),
                PlayerRoster.is_transfer.label("is_transfer"),
                PlayerRoster.roster_url.label("roster_url"),
                PlayerRoster.profile_url.label("profile_url"),
            )
            .select_from(PlayerRoster)
            .join(Player, PlayerRoster.player_id == Player.id)
            .join(Person, Player.person_id == Person.id)
            .join(College, PlayerRoster.college_id == College.id)
            .outerjoin(Position, PlayerRoster.primary_position_id == Position.id)
            .outerjoin(HighSchool, PlayerRoster.high_school_id == HighSchool.id)
        )
        statement = self._apply_search_filters(statement, filters)
        statement = statement.order_by(College.name, Person.full_name).limit(limit).offset(offset)
        rows = self.session.execute(statement).mappings().all()
        return [PlayerSearchResult.model_validate(dict(row)) for row in rows]

    def _apply_search_filters(
        self, statement: Select[Any], filters: PlayerSearchFilters
    ) -> Select[Any]:
        if filters.year is not None:
            statement = statement.where(PlayerRoster.year == filters.year)
        if filters.college:
            statement = statement.where(College.name.ilike(f"%{filters.college}%"))
        if filters.conference:
            statement = statement.where(College.conference.ilike(f"%{filters.conference}%"))
        if filters.position:
            statement = statement.where(
                or_(
                    Position.code.ilike(f"%{filters.position}%"),
                    Position.name.ilike(f"%{filters.position}%"),
                    PlayerRoster.positions_raw.ilike(f"%{filters.position}%"),
                )
            )
        if filters.roster_year:
            statement = statement.where(
                or_(
                    PlayerRoster.normalized_roster_year == filters.roster_year,
                    PlayerRoster.roster_year.ilike(f"%{filters.roster_year}%"),
                )
            )
        if filters.is_transfer is not None:
            statement = statement.where(PlayerRoster.is_transfer.is_(filters.is_transfer))
        if filters.hometown_state:
            statement = statement.where(Player.hometown_state.ilike(f"%{filters.hometown_state}%"))
        return statement


class CoachAssignmentRepository(Repository[CoachAssignment]):
    def get(self, assignment_id: int) -> CoachAssignment | None:
        return self.session.get(CoachAssignment, assignment_id)

    def add(self, assignment: CoachAssignment) -> CoachAssignment:
        self.session.add(assignment)
        return assignment
