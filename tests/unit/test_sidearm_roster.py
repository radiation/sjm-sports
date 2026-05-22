from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup, Tag

from app.importers.sidearm_roster import (
    ParsedRosterPlayer,
    SidearmImportFailure,
    _build_batch_cli_summary,
    build_parser,
    default_failure_report_path,
    fetch_roster_html,
    list_sidearm_school_source_rows,
    main,
    parse_sidearm_roster,
    parse_sidearm_roster_document,
    parsed_players_to_rows,
    run_import_all,
    run_import_school,
    select_sidearm_school_source_rows,
)
from app.models.people import Person, Player
from app.models.positions import Position
from app.models.rosters import PlayerRoster
from app.models.schools import College, HighSchool
from app.schemas.roster_import import (
    RosterImportSummary,
    SidearmBatchImportSummary,
    SidearmBatchSchoolResult,
)
from app.schemas.school_sources import SchoolSourceRow
from app.services.imports import RosterImportService, SidearmRosterImportService

FIXTURE_DIR = Path("tests/fixtures/sidearm")
GEORGETOWN_FIXTURE_PATH = FIXTURE_DIR / "georgetown_2026_baseball_roster.html"
BOSTON_COLLEGE_FIXTURE_PATH = FIXTURE_DIR / "boston_college_2026_baseball_roster.html"
LOUISVILLE_FIXTURE_PATH = FIXTURE_DIR / "louisville_2026_baseball_roster.html"
GEORGETOWN_URL = "https://guhoyas.com/sports/baseball/roster"
BOSTON_COLLEGE_URL = "https://bceagles.com/sports/baseball/roster"
LOUISVILLE_URL = "https://gocards.com/sports/baseball/roster"


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
            id=self.next_id,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
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
            id=self.next_id,
            name=name,
            city=city,
            state=state,
            country=country,
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


def load_fixture(path: Path = GEORGETOWN_FIXTURE_PATH) -> str:
    return path.read_text(encoding="utf-8")


def build_services() -> tuple[
    SidearmRosterImportService, FakeRosterRepository, FakeCollegeRepository
]:
    colleges = FakeCollegeRepository()
    rosters = FakeRosterRepository()
    roster_imports = RosterImportService(
        colleges=colleges,  # type: ignore[arg-type]
        people=FakePersonRepository(),  # type: ignore[arg-type]
        players=FakePlayerRepository(),  # type: ignore[arg-type]
        positions=FakePositionRepository(),  # type: ignore[arg-type]
        high_schools=FakeHighSchoolRepository(),  # type: ignore[arg-type]
        rosters=rosters,  # type: ignore[arg-type]
    )
    service = SidearmRosterImportService(colleges=colleges, roster_imports=roster_imports)
    return service, rosters, colleges


def georgetown_school() -> SchoolSourceRow:
    return SchoolSourceRow(
        school_id="S66",
        ipeds_id="131496",
        school_name="Georgetown University",
        city="Washington",
        state="DC",
        public_private="Private",
        division="NCAA D1",
        conference="Big East Conference",
        roster_url=GEORGETOWN_URL,
        roster_vendor="sidearm",
        is_sidearm=True,
        import_enabled=True,
        notes="vendor_verified_html: sidearm footer link",
    )


def write_sources_file(path: Path, rows: list[SchoolSourceRow]) -> None:
    fieldnames = [
        "school_id",
        "ipeds_id",
        "school_name",
        "city",
        "state",
        "public_private",
        "division",
        "conference",
        "roster_url",
        "roster_vendor",
        "is_sidearm",
        "import_enabled",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as source_file:
        import csv

        writer = csv.DictWriter(source_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump())


def test_parse_sidearm_roster_reads_georgetown_fixture() -> None:
    players = parse_sidearm_roster(load_fixture(), GEORGETOWN_URL, 2026)

    assert players
    assert len(players) > 30

    travis = next(player for player in players if player.full_name == "Travis Ilitch")
    assert travis.jersey_number == "1"
    assert travis.first_name == "Travis"
    assert travis.last_name == "Ilitch"
    assert travis.position == "OF"
    assert travis.academic_year == "Sr."
    assert travis.height == "5-9"
    assert travis.weight == "170"
    assert travis.bats == "L"
    assert travis.throws == "L"
    assert travis.hometown == "Bloomfield Hills, Mich."
    assert travis.high_school == "Cranbrook Kingswood"
    assert travis.previous_school is None

    spencer = next(player for player in players if player.full_name == "Spencer Seid")
    assert spencer.previous_school == "UC San Diego"
    assert spencer.profile_url == "https://guhoyas.com/sports/baseball/roster/spencer-seid/17437"


def test_parse_sidearm_roster_skips_coaches_and_support_staff() -> None:
    players = parse_sidearm_roster(load_fixture(), GEORGETOWN_URL, 2026)
    names = {player.full_name for player in players}

    assert "Edwin Thompson" not in names
    assert "George Capen" not in names
    assert "Errol Robinson" not in names


def test_parse_sidearm_roster_reads_boston_college_person_card_fixture() -> None:
    document = parse_sidearm_roster_document(
        load_fixture(BOSTON_COLLEGE_FIXTURE_PATH),
        BOSTON_COLLEGE_URL,
        2026,
    )

    assert not document.diagnostics
    assert len(document.players) > 30

    sean = next(player for player in document.players if player.full_name == "Sean Martinez")
    assert sean.jersey_number == "1"
    assert sean.first_name == "Sean"
    assert sean.last_name == "Martinez"
    assert sean.position == "INF"
    assert sean.academic_year == "So."
    assert sean.height == "5-11"
    assert sean.weight == "175"
    assert sean.bats == "R"
    assert sean.throws == "R"
    assert sean.hometown == "Perkasie, Pa."
    assert sean.high_school == "Lansdale Catholic HS"
    assert sean.previous_school is None
    assert sean.profile_url == "https://bceagles.com/sports/baseball/roster/sean-martinez/26428"

    names = {player.full_name for player in document.players}
    assert "Todd Interdonato" not in names
    assert "Greg Sullivan" not in names


def test_parse_sidearm_roster_reads_louisville_person_card_fixture() -> None:
    document = parse_sidearm_roster_document(
        load_fixture(LOUISVILLE_FIXTURE_PATH),
        LOUISVILLE_URL,
        2026,
    )

    assert not document.diagnostics
    assert len(document.players) > 30

    aj = next(player for player in document.players if player.full_name == "AJ Martin")
    assert aj.jersey_number == "1"
    assert aj.position == "INF"
    assert aj.academic_year == "Sr."
    assert aj.height == "5-10"
    assert aj.weight == "175"
    assert aj.bats == "R"
    assert aj.throws == "R"
    assert aj.hometown == "Olney, Md."
    assert aj.high_school is None
    assert aj.previous_school == "St. John's College"
    assert aj.profile_url == "https://gocards.com/sports/baseball/roster/aj-martin/17921"


def test_parse_person_card_fixture_handles_missing_optional_school_fields() -> None:
    soup = BeautifulSoup(load_fixture(LOUISVILLE_FIXTURE_PATH), "lxml")
    aj_card = next(
        card
        for card in soup.select(".c-rosterpage__players .s-person-card")
        if card.select_one("h3") is not None
        and card.select_one("h3").get_text(" ", strip=True) == "AJ Martin"
    )
    school_item = aj_card.select_one(
        '[data-test-id="s-person-card-list__content-location-person-high-school"]'
    )
    assert school_item is not None
    for content in list(school_item.contents):
        if isinstance(content, Tag) and "sr-only" in content.get("class", []):
            continue
        content.extract()

    document = parse_sidearm_roster_document(str(soup), LOUISVILLE_URL, 2026)

    aj = next(player for player in document.players if player.full_name == "AJ Martin")
    assert aj.high_school is None
    assert aj.previous_school is None


def test_parse_sidearm_roster_records_title_mismatch_without_failing_valid_players() -> None:
    html = load_fixture(BOSTON_COLLEGE_FIXTURE_PATH).replace(
        "2026 Baseball Roster", "Roster Landing Page"
    )

    document = parse_sidearm_roster_document(html, BOSTON_COLLEGE_URL, 2026)

    assert len(document.players) > 30
    assert any(diagnostic.code == "title_mismatch" for diagnostic in document.diagnostics)


def test_parse_sidearm_roster_reports_no_supported_template() -> None:
    html = "<html><head><title>Example</title></head><body><div>no roster here</div></body></html>"

    with pytest.raises(SidearmImportFailure, match="no_supported_sidearm_roster_template_found"):
        parse_sidearm_roster_document(html, "https://example.com/baseball/roster", 2026)


def test_fetch_roster_html_classifies_http_404(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://example.com/baseball/roster")
    response = httpx.Response(404, request=request)

    def fake_get(*args: object, **kwargs: object) -> httpx.Response:
        return response

    monkeypatch.setattr("app.importers.sidearm_roster.httpx.get", fake_get)

    with pytest.raises(SidearmImportFailure, match="http_404"):
        fetch_roster_html("https://example.com/baseball/roster")


def test_sidearm_import_service_is_idempotent_for_same_school_and_season() -> None:
    players = parse_sidearm_roster(load_fixture(), GEORGETOWN_URL, 2026)
    rows = parsed_players_to_rows(players)
    service, rosters, colleges = build_services()
    school = georgetown_school()

    first_summary = service.import_rows(school, rows, year=2026, source_url=GEORGETOWN_URL)
    second_summary = service.import_rows(school, rows, year=2026, source_url=GEORGETOWN_URL)

    assert first_summary.rows_imported == len(players)
    assert first_summary.rosters_created == len(players)
    assert second_summary.rows_imported == len(players)
    assert second_summary.rosters_updated == len(players)
    assert len(rosters.rosters) == len(players)
    assert len(colleges.colleges) == 1
    assert colleges.colleges[0].roster_vendor == "sidearm"
    assert colleges.colleges[0].ncaa_school_id == "S66"

    spencer_roster = next(
        roster for roster in rosters.rosters if roster.player.person.full_name == "Spencer Seid"
    )
    assert spencer_roster.previous_school_raw == "UC San Diego"
    assert spencer_roster.primary_position is not None
    assert spencer_roster.primary_position.code == "LHP"


def test_sidearm_import_service_rejects_non_sidearm_school() -> None:
    players = [
        ParsedRosterPlayer(
            row_number=1,
            full_name="Test Player",
            first_name="Test",
            last_name="Player",
            jersey_number="1",
            position="OF",
            academic_year="Fr.",
            height="6-0",
            weight="180",
            bats="R",
            throws="R",
            hometown="Austin, TX",
            high_school="Example High",
            previous_school=None,
            profile_url="https://example.com/player",
        )
    ]
    rows = parsed_players_to_rows(players)
    service, _rosters, _colleges = build_services()
    school = georgetown_school().model_copy(
        update={"roster_vendor": "unknown", "is_sidearm": False}
    )

    with pytest.raises(ValueError, match="verified Sidearm"):
        service.import_rows(school, rows, year=2026, source_url=GEORGETOWN_URL)


def test_list_sidearm_school_source_rows_filters_to_verified_enabled_sidearm(
    tmp_path: Path,
) -> None:
    path = tmp_path / "schools.verified.csv"
    write_sources_file(
        path,
        [
            georgetown_school(),
            georgetown_school().model_copy(
                update={
                    "school_id": "S67",
                    "school_name": "Disabled Sidearm",
                    "import_enabled": False,
                }
            ),
            georgetown_school().model_copy(
                update={
                    "school_id": "S68",
                    "school_name": "Unknown Vendor",
                    "roster_vendor": "unknown",
                    "is_sidearm": False,
                }
            ),
        ],
    )

    rows = list_sidearm_school_source_rows(path)

    assert [row.school_id for row in rows] == ["S66"]


def test_select_sidearm_school_source_rows_supports_single_school_and_limit(tmp_path: Path) -> None:
    path = tmp_path / "schools.verified.csv"
    write_sources_file(
        path,
        [
            georgetown_school(),
            georgetown_school().model_copy(
                update={
                    "school_id": "S71",
                    "school_name": "Second Sidearm",
                }
            ),
            georgetown_school().model_copy(
                update={
                    "school_id": "S72",
                    "school_name": "Disabled Sidearm",
                    "import_enabled": False,
                }
            ),
        ],
    )

    schools_eligible, selected_school = select_sidearm_school_source_rows(path, school_id="S71")
    limited_eligible, limited_rows = select_sidearm_school_source_rows(path, limit=1)

    assert schools_eligible == 2
    assert [row.school_id for row in selected_school] == ["S71"]
    assert limited_eligible == 2
    assert [row.school_id for row in limited_rows] == ["S66"]


def test_run_import_school_dry_run_rolls_back_without_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False
            self.closed = False

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    class FakeImportService:
        def import_rows(
            self,
            school: SchoolSourceRow,
            rows: list[object],
            year: int,
            source_url: str,
        ) -> object:
            assert school.school_id == "S66"
            assert rows
            assert year == 2026
            assert source_url == GEORGETOWN_URL
            return RosterImportSummary(
                rows_seen=len(rows),
                rows_imported=len(rows),
                rosters_created=len(rows),
            )

    fake_session = FakeSession()

    monkeypatch.setattr("app.importers.sidearm_roster.SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        "app.importers.sidearm_roster.build_sidearm_import_service",
        lambda session: FakeImportService(),
    )

    summary = run_import_school(
        school=georgetown_school(),
        season=2026,
        fetch_html=lambda _url: load_fixture(),
        dry_run=True,
    )

    assert summary.rows_seen > 30
    assert summary.rows_imported == summary.rows_seen
    assert summary.rosters_created == summary.rows_seen
    assert fake_session.committed is False
    assert fake_session.rolled_back is True
    assert fake_session.closed is True


def test_run_import_all_aggregates_successes_and_failures(tmp_path: Path) -> None:
    path = tmp_path / "schools.verified.csv"
    report_path = tmp_path / "import_runs" / "sidearm_roster_failures_2026.json"
    write_sources_file(
        path,
        [
            georgetown_school(),
            georgetown_school().model_copy(
                update={
                    "school_id": "S70",
                    "school_name": "Failing Sidearm",
                    "roster_url": "https://example.com/fail",
                }
            ),
        ],
    )

    def fake_import_school(
        school: SchoolSourceRow,
        season: int,
        url: str | None,
        fetch_html: object,
        dry_run: bool,
    ) -> object:
        assert season == 2026
        assert url is None
        assert dry_run is False
        if school.school_id == "S70":
            raise ValueError("boom")
        return {"rows_seen": 3, "rows_imported": 3, "rosters_created": 3}

    summary = run_import_all(
        season=2026,
        sources_path=path,
        failure_report_path=report_path,
        import_school=fake_import_school,  # type: ignore[arg-type]
    )

    assert summary.schools_seen == 2
    assert summary.schools_eligible == 2
    assert summary.schools_attempted == 2
    assert summary.schools_selected == 2
    assert summary.schools_imported == 1
    assert summary.schools_failed == 1
    assert summary.players_seen == 3
    assert summary.players_imported == 3
    assert summary.roster_rows_created == 3
    assert summary.results[0].school_id == "S66"
    assert summary.results[0].success is True
    assert summary.results[1].school_id == "S70"
    assert summary.results[1].success is False
    assert summary.results[1].failure_reason == "unexpected_error"
    assert summary.results[1].error == "boom"
    assert summary.failures_by_reason == {"unexpected_error": 1}
    assert summary.failure_report_path == str(report_path)


def test_run_import_all_reports_progress(tmp_path: Path) -> None:
    path = tmp_path / "schools.verified.csv"
    write_sources_file(
        path,
        [
            georgetown_school(),
            georgetown_school().model_copy(
                update={
                    "school_id": "S71",
                    "school_name": "Second Sidearm",
                }
            ),
        ],
    )
    progress_messages: list[str] = []

    def fake_import_school(
        school: SchoolSourceRow,
        season: int,
        url: str | None,
        fetch_html: object,
        dry_run: bool,
    ) -> object:
        assert season == 2026
        assert url is None
        assert dry_run is False
        return {"rows_imported": 1}

    def record_progress(index: int, total: int, school: SchoolSourceRow) -> None:
        progress_messages.append(f"{index}/{total}:{school.school_id}")

    run_import_all(
        season=2026,
        sources_path=path,
        import_school=fake_import_school,  # type: ignore[arg-type]
        progress_callback=record_progress,
    )

    assert progress_messages == ["1/2:S66", "2/2:S71"]


def test_run_import_all_applies_batch_limit(tmp_path: Path) -> None:
    path = tmp_path / "schools.verified.csv"
    write_sources_file(
        path,
        [
            georgetown_school(),
            georgetown_school().model_copy(update={"school_id": "S71", "school_name": "Second"}),
            georgetown_school().model_copy(update={"school_id": "S72", "school_name": "Third"}),
        ],
    )
    attempted_ids: list[str] = []

    def fake_import_school(
        school: SchoolSourceRow,
        season: int,
        url: str | None,
        fetch_html: object,
        dry_run: bool,
    ) -> object:
        attempted_ids.append(school.school_id)
        assert season == 2026
        assert url is None
        assert dry_run is False
        return {"rows_seen": 1, "rows_imported": 1, "rosters_created": 1}

    summary = run_import_all(
        season=2026,
        sources_path=path,
        limit=2,
        import_school=fake_import_school,  # type: ignore[arg-type]
    )

    assert summary.schools_eligible == 3
    assert summary.schools_attempted == 2
    assert attempted_ids == ["S66", "S71"]


def test_run_import_all_writes_failure_report_json(tmp_path: Path) -> None:
    path = tmp_path / "schools.verified.csv"
    report_path = tmp_path / "import_runs" / "sidearm_roster_failures_2026.json"
    write_sources_file(
        path,
        [
            georgetown_school(),
            georgetown_school().model_copy(
                update={
                    "school_id": "S70",
                    "school_name": "Missing Roster",
                }
            ),
        ],
    )

    def fake_import_school(
        school: SchoolSourceRow,
        season: int,
        url: str | None,
        fetch_html: object,
        dry_run: bool,
    ) -> object:
        assert season == 2026
        assert url is None
        assert dry_run is True
        if school.school_id == "S70":
            raise SidearmImportFailure("http_404", school.roster_url)
        return {"rows_seen": 2, "rows_imported": 2, "rosters_created": 2}

    summary = run_import_all(
        season=2026,
        sources_path=path,
        dry_run=True,
        failure_report_path=report_path,
        import_school=fake_import_school,  # type: ignore[arg-type]
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert summary.failure_report_path == str(report_path)
    assert summary.failures_by_reason == {"stale_url_or_not_found": 1}
    assert report["dry_run"] is True
    assert report["failures_by_reason"] == {"stale_url_or_not_found": 1}
    assert report["failures"] == [
        {
            "school_id": "S70",
            "school_name": "Missing Roster",
            "source_url": GEORGETOWN_URL,
            "reason": "stale_url_or_not_found",
            "error": f"http_404: {GEORGETOWN_URL}",
        }
    ]


def test_build_batch_cli_summary_omits_per_school_success_details() -> None:
    summary = SidearmBatchImportSummary(
        schools_seen=3,
        schools_eligible=2,
        schools_attempted=2,
        schools_selected=2,
        dry_run=False,
    )
    summary.add_result(
        SidearmBatchSchoolResult(
            school_id="S66",
            school_name="Georgetown University",
            success=True,
            summary={
                "rows_seen": 3,
                "rows_imported": 2,
                "players_updated": 1,
                "rosters_created": 2,
                "rosters_updated": 1,
            },
        )
    )
    summary.add_result(
        SidearmBatchSchoolResult(
            school_id="S70",
            school_name="Failing Sidearm",
            success=False,
            failure_reason="ssl_certificate_verify_failed",
            error="boom",
        )
    )

    output = _build_batch_cli_summary(summary)

    assert output["schools_seen"] == 3
    assert output["schools_eligible"] == 2
    assert output["schools_attempted"] == 2
    assert output["schools_selected"] == 2
    assert output["schools_imported"] == 1
    assert output["schools_failed"] == 1
    assert output["players_seen"] == 3
    assert output["players_imported"] == 2
    assert output["players_updated"] == 1
    assert output["roster_rows_created"] == 2
    assert output["roster_rows_updated"] == 1
    assert output["failures_by_reason"] == {"ssl_certificate_verify_failed": 1}
    assert output["failed_schools"] == [
        {
            "school_id": "S70",
            "school_name": "Failing Sidearm",
            "reason": "ssl_certificate_verify_failed",
            "error": "boom",
        }
    ]
    assert "results" not in output


def test_main_all_schools_prints_summary_and_progress(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = SidearmBatchImportSummary(
        schools_seen=2,
        schools_eligible=2,
        schools_attempted=2,
        schools_selected=2,
        dry_run=True,
        failure_report_path="data/import_runs/sidearm_roster_failures_2026.json",
    )
    summary.add_result(
        SidearmBatchSchoolResult(
            school_id="S66",
            school_name="Georgetown University",
            success=True,
            summary={"rows_seen": 5, "rows_imported": 5, "rosters_created": 5},
        )
    )
    summary.add_result(
        SidearmBatchSchoolResult(
            school_id="S70",
            school_name="Failing Sidearm",
            success=False,
            failure_reason="unexpected_error",
            error="boom",
        )
    )

    def fake_run_import_all(*args: object, **kwargs: object) -> SidearmBatchImportSummary:
        progress_callback = kwargs["progress_callback"]
        assert callable(progress_callback)
        assert kwargs["limit"] == 2
        assert kwargs["dry_run"] is True
        progress_callback(1, 2, georgetown_school())
        progress_callback(
            2,
            2,
            georgetown_school().model_copy(
                update={"school_id": "S70", "school_name": "Failing Sidearm"}
            ),
        )
        return summary

    monkeypatch.setattr("app.importers.sidearm_roster.run_import_all", fake_run_import_all)

    exit_code = main(["--season", "2026", "--limit", "2", "--dry-run"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"dry_run": true' in captured.out
    assert '"schools_imported": 1' in captured.out
    assert (
        '"failure_report_path": "data/import_runs/sidearm_roster_failures_2026.json"'
        in captured.out
    )
    assert '"failed_schools"' in captured.out
    assert '"results"' not in captured.out
    assert "processing school 1 of 2: S66 Georgetown University" in captured.err
    assert "processing school 2 of 2: S70 Failing Sidearm" in captured.err


def test_build_parser_supports_limited_batch_without_school_id() -> None:
    args = build_parser().parse_args(["--limit", "5", "--season", "2026", "--dry-run"])

    assert args.all_schools is False
    assert args.school_id is None
    assert args.limit == 5
    assert args.season == 2026
    assert args.dry_run is True
