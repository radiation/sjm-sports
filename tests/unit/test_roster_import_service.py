from __future__ import annotations

from app.models.people import Person, Player
from app.models.positions import Position
from app.models.rosters import PlayerRoster
from app.models.schools import College, HighSchool
from app.schemas.roster_import import RosterImportRow
from app.services.imports import RosterImportService


class FakeCollegeRepository:
    def __init__(self) -> None:
        self.colleges: list[College] = []
        self.next_id = 1

    def get_by_name(self, name: str) -> College | None:
        return next((college for college in self.colleges if college.name == name), None)

    def get_or_create_by_name(self, name: str) -> tuple[College, bool]:
        college = self.get_by_name(name)
        if college is not None:
            return college, False
        college = College(id=self.next_id, name=name)
        self.next_id += 1
        self.colleges.append(college)
        return college, True


class FakePersonRepository:
    def __init__(self) -> None:
        self.people: list[Person] = []
        self.next_id = 1

    def get_or_create_by_full_name(
        self, full_name: str, first_name: str | None = None, last_name: str | None = None
    ) -> tuple[Person, bool]:
        person = Person(
            id=self.next_id, full_name=full_name, first_name=first_name, last_name=last_name
        )
        self.next_id += 1
        self.people.append(person)
        return person, True


class FakePlayerRepository:
    def __init__(self) -> None:
        self.players: list[Player] = []
        self.next_id = 1

    def create_for_person(
        self,
        person: Person,
        bats: str | None = None,
        throws: str | None = None,
        height_inches: int | None = None,
        weight_lbs: int | None = None,
        hometown_city: str | None = None,
        hometown_state: str | None = None,
        hometown_country: str | None = None,
    ) -> Player:
        player = Player(
            id=self.next_id,
            person=person,
            bats=bats,
            throws=throws,
            height_inches=height_inches,
            weight_lbs=weight_lbs,
            hometown_city=hometown_city,
            hometown_state=hometown_state,
            hometown_country=hometown_country,
        )
        self.next_id += 1
        self.players.append(player)
        return player


class FakePositionRepository:
    def __init__(self) -> None:
        self.positions: list[Position] = []
        self.next_id = 1

    def get_or_create(
        self, code: str, name: str, position_type: str, position_group: str | None
    ) -> tuple[Position, bool]:
        position = next(
            (
                existing_position
                for existing_position in self.positions
                if existing_position.code == code
                and existing_position.position_type == position_type
            ),
            None,
        )
        if position is not None:
            return position, False
        position = Position(
            id=self.next_id,
            code=code,
            name=name,
            position_type=position_type,
            position_group=position_group,
        )
        self.next_id += 1
        self.positions.append(position)
        return position, True


class FakeHighSchoolRepository:
    def __init__(self) -> None:
        self.high_schools: list[HighSchool] = []
        self.next_id = 1

    def get_or_create_by_identity(
        self, name: str, city: str | None, state: str | None, country: str | None
    ) -> tuple[HighSchool, bool]:
        high_school = next(
            (
                existing_high_school
                for existing_high_school in self.high_schools
                if existing_high_school.name == name
                and existing_high_school.city == city
                and existing_high_school.state == state
                and existing_high_school.country == country
            ),
            None,
        )
        if high_school is not None:
            return high_school, False
        high_school = HighSchool(
            id=self.next_id, name=name, city=city, state=state, country=country
        )
        self.next_id += 1
        self.high_schools.append(high_school)
        return high_school, True


class FakeRosterRepository:
    def __init__(self) -> None:
        self.rosters: list[PlayerRoster] = []
        self.next_id = 1

    def get_by_college_year_player_name(
        self, college_id: int, year: int, full_name: str
    ) -> PlayerRoster | None:
        return next(
            (
                roster
                for roster in self.rosters
                if roster.college.id == college_id
                and roster.year == year
                and roster.player.person.full_name == full_name
            ),
            None,
        )

    def add(self, roster: PlayerRoster) -> PlayerRoster:
        roster.id = self.next_id
        self.next_id += 1
        self.rosters.append(roster)
        return roster


def build_service() -> tuple[RosterImportService, FakeRosterRepository, FakeCollegeRepository]:
    colleges = FakeCollegeRepository()
    rosters = FakeRosterRepository()
    service = RosterImportService(
        colleges=colleges,  # type: ignore[arg-type]
        people=FakePersonRepository(),  # type: ignore[arg-type]
        players=FakePlayerRepository(),  # type: ignore[arg-type]
        positions=FakePositionRepository(),  # type: ignore[arg-type]
        high_schools=FakeHighSchoolRepository(),  # type: ignore[arg-type]
        rosters=rosters,  # type: ignore[arg-type]
    )
    return service, rosters, colleges


def test_roster_import_service_creates_domain_records() -> None:
    service, rosters, colleges = build_service()
    rows = [
        RosterImportRow(
            row_number=2,
            college="Example State",
            conference="Example League",
            full_name="Alex Example",
            position="RHP",
            height="6-2",
            weight="205",
            bats_throws="R/R",
            hometown="Austin, TX",
            high_school="Example High",
            roster_year="Jr",
            jersey_number="12",
        )
    ]

    summary = service.import_rows(rows, year=2025)

    assert summary.rows_seen == 1
    assert summary.rows_imported == 1
    assert summary.players_created == 1
    assert summary.colleges_created == 1
    assert summary.positions_created == 1
    assert summary.high_schools_created == 1
    assert summary.rosters_created == 1
    assert len(rosters.rosters) == 1
    assert rosters.rosters[0].player.height_inches == 74
    assert rosters.rosters[0].normalized_roster_year == "junior"
    assert colleges.colleges[0].conference == "Example League"


def test_roster_import_service_updates_existing_roster_conservatively() -> None:
    service, rosters, _colleges = build_service()
    first_row = RosterImportRow(row_number=2, college="Example State", full_name="Alex Example")
    second_row = RosterImportRow(
        row_number=3,
        college="Example State",
        full_name="Alex Example",
        weight="210",
        roster_year="Sr",
    )

    first_summary = service.import_rows([first_row], year=2025)
    second_summary = service.import_rows([second_row], year=2025)

    assert first_summary.rosters_created == 1
    assert second_summary.rosters_updated == 1
    assert second_summary.players_updated == 1
    assert len(rosters.rosters) == 1
    assert rosters.rosters[0].player.weight_lbs == 210
    assert rosters.rosters[0].normalized_roster_year == "senior"


def test_roster_import_service_skips_missing_required_values() -> None:
    service, _rosters, _colleges = build_service()

    summary = service.import_rows(
        [RosterImportRow(row_number=2, full_name="No College")], year=2025
    )

    assert summary.rows_imported == 0
    assert summary.rows_skipped == 1
    assert summary.errors[0].message == "missing college"
