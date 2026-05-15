from __future__ import annotations

from collections.abc import Sequence

from app.models.people import Person, Player
from app.models.positions import Position
from app.models.rosters import PlayerRoster
from app.models.schools import College, HighSchool
from app.repositories.people import PersonRepository, PlayerRepository
from app.repositories.positions import PositionRepository
from app.repositories.rosters import PlayerRosterRepository
from app.repositories.schools import CollegeRepository, HighSchoolRepository
from app.schemas.roster_import import RosterImportRow, RosterImportSummary
from app.utils.roster_normalization import (
    NameParts,
    clean_text,
    normalize_position,
    normalize_roster_year,
    parse_bats_throws,
    parse_height_inches,
    parse_hometown,
    parse_transfer_flag,
    parse_weight_lbs,
    split_name,
)


class ImportService:
    """Future importer-facing workflow service.

    Importers should normalize source records and call service methods here instead of using
    SQLAlchemy sessions or repositories directly.
    """


class RosterImportService:
    def __init__(
        self,
        colleges: CollegeRepository,
        people: PersonRepository,
        players: PlayerRepository,
        positions: PositionRepository,
        high_schools: HighSchoolRepository,
        rosters: PlayerRosterRepository,
    ) -> None:
        self.colleges = colleges
        self.people = people
        self.players = players
        self.positions = positions
        self.high_schools = high_schools
        self.rosters = rosters

    def import_rows(self, rows: Sequence[RosterImportRow], year: int) -> RosterImportSummary:
        summary = RosterImportSummary(rows_seen=len(rows))
        for row in rows:
            try:
                imported = self._import_row(row, year, summary)
            except Exception as exc:  # noqa: BLE001
                summary.rows_skipped += 1
                summary.add_error(row.row_number, str(exc))
                continue

            if imported:
                summary.rows_imported += 1
            else:
                summary.rows_skipped += 1

        return summary

    def _import_row(self, row: RosterImportRow, year: int, summary: RosterImportSummary) -> bool:
        college_name = clean_text(row.college)
        name_parts = split_name(row.full_name, row.first_name, row.last_name)
        if college_name is None:
            summary.add_error(row.row_number, "missing college")
            return False
        if name_parts is None:
            summary.add_error(row.row_number, "missing player name")
            return False

        college, college_created = self.colleges.get_or_create_by_name(college_name)
        if college_created:
            summary.colleges_created += 1
        self._update_college(college, row)

        position = self._get_position(row, summary)
        high_school = self._get_high_school(row, summary)
        previous_school_raw = clean_text(row.previous_school)
        previous_college = (
            self.colleges.get_by_name(previous_school_raw) if previous_school_raw else None
        )

        roster = None
        if not college_created and college.id is not None:
            roster = self.rosters.get_by_college_year_player_name(
                college.id, year, name_parts.full_name
            )

        bats, throws = parse_bats_throws(row.bats_throws, row.bats, row.throws)
        hometown = parse_hometown(row.hometown)
        hometown_city = clean_text(row.hometown_city) or hometown.city
        hometown_state = clean_text(row.hometown_state) or hometown.state
        hometown_country = clean_text(row.hometown_country) or hometown.country

        if roster is None:
            person, _person_created = self.people.get_or_create_by_full_name(
                name_parts.full_name, name_parts.first_name, name_parts.last_name
            )
            player = self.players.create_for_person(
                person=person,
                bats=bats,
                throws=throws,
                height_inches=parse_height_inches(row.height),
                weight_lbs=parse_weight_lbs(row.weight),
                hometown_city=hometown_city,
                hometown_state=hometown_state,
                hometown_country=hometown_country,
            )
            summary.players_created += 1
            roster = PlayerRoster(player=player, college=college, year=year)
            self.rosters.add(roster)
            summary.rosters_created += 1
        else:
            if self._update_player(
                roster.player, bats, throws, row, hometown_city, hometown_state, hometown_country
            ):
                summary.players_updated += 1
            summary.rosters_updated += 1

        self._update_person(roster.player.person, name_parts)
        self._update_roster(
            roster=roster,
            row=row,
            year=year,
            position=position,
            high_school=high_school,
            previous_college=previous_college,
            previous_school_raw=previous_school_raw,
        )
        return True

    def _get_position(self, row: RosterImportRow, summary: RosterImportSummary) -> Position | None:
        position_parts = normalize_position(row.position)
        if position_parts is None:
            return None
        position, created = self.positions.get_or_create(
            code=position_parts.code,
            name=position_parts.name,
            position_type="player",
            position_group=position_parts.group,
        )
        if created:
            summary.positions_created += 1
        return position

    def _get_high_school(
        self, row: RosterImportRow, summary: RosterImportSummary
    ) -> HighSchool | None:
        high_school_name = clean_text(row.high_school)
        if high_school_name is None:
            return None
        high_school, created = self.high_schools.get_or_create_by_identity(
            name=high_school_name,
            city=None,
            state=None,
            country=None,
        )
        if created:
            summary.high_schools_created += 1
        return high_school

    def _update_college(self, college: College, row: RosterImportRow) -> None:
        self._set_if_present(college, "state", clean_text(row.college_state))
        self._set_if_present(college, "division", clean_text(row.college_division))
        self._set_if_present(college, "conference", clean_text(row.conference))
        self._set_if_present(college, "roster_url", clean_text(row.roster_url))

    def _update_person(self, person: Person, name_parts: NameParts) -> None:
        self._set_if_present(person, "first_name", name_parts.first_name)
        self._set_if_present(person, "last_name", name_parts.last_name)
        self._set_if_present(person, "full_name", name_parts.full_name)

    def _update_player(
        self,
        player: Player,
        bats: str | None,
        throws: str | None,
        row: RosterImportRow,
        hometown_city: str | None,
        hometown_state: str | None,
        hometown_country: str | None,
    ) -> bool:
        changed = False
        changed |= self._set_if_changed(player, "bats", bats)
        changed |= self._set_if_changed(player, "throws", throws)
        changed |= self._set_if_changed(player, "height_inches", parse_height_inches(row.height))
        changed |= self._set_if_changed(player, "weight_lbs", parse_weight_lbs(row.weight))
        changed |= self._set_if_changed(player, "hometown_city", hometown_city)
        changed |= self._set_if_changed(player, "hometown_state", hometown_state)
        changed |= self._set_if_changed(player, "hometown_country", hometown_country)
        return changed

    def _update_roster(
        self,
        roster: PlayerRoster,
        row: RosterImportRow,
        year: int,
        position: Position | None,
        high_school: HighSchool | None,
        previous_college: College | None,
        previous_school_raw: str | None,
    ) -> None:
        roster.year = year
        roster.roster_year = clean_text(row.roster_year)
        roster.normalized_roster_year = normalize_roster_year(row.roster_year)
        roster.primary_position = position
        roster.positions_raw = clean_text(row.position)
        roster.high_school = high_school
        roster.previous_college = previous_college
        roster.previous_school_raw = previous_school_raw
        roster.is_transfer = parse_transfer_flag(row.is_transfer) or previous_school_raw is not None
        roster.jersey_number = clean_text(row.jersey_number)
        roster.roster_url = clean_text(row.roster_url)
        roster.profile_url = clean_text(row.profile_url)

    def _set_if_present(self, target: object, attribute: str, value: object) -> None:
        if value is not None:
            setattr(target, attribute, value)

    def _set_if_changed(self, target: object, attribute: str, value: object) -> bool:
        if value is None or getattr(target, attribute) == value:
            return False
        setattr(target, attribute, value)
        return True
