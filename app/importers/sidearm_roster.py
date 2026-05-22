from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.importers.school_sources import read_school_source_rows
from app.repositories.people import PersonRepository, PlayerRepository
from app.repositories.positions import PositionRepository
from app.repositories.rosters import PlayerRosterRepository
from app.repositories.schools import CollegeRepository, HighSchoolRepository
from app.schemas.roster_import import (
    RosterImportRow,
    RosterImportSummary,
    SidearmBatchImportSummary,
    SidearmBatchSchoolResult,
)
from app.schemas.school_sources import SchoolSourceRow
from app.services.imports import RosterImportService, SidearmRosterImportService
from app.utils.roster_normalization import clean_text, split_name
from app.utils.school_sources import normalize_vendor_verification_error

DEFAULT_SOURCES_PATH = Path("data/schools.verified.csv")
DEFAULT_FAILURE_REPORT_DIR = Path("data/import_runs")
SIDEARM_VENDOR = "sidearm"
SIDEARM_PARSE_FAILURE_REASONS = {
    "supported_template_found_but_no_player_cards",
    "person_card_template_detected_but_no_cards",
    "legacy_template_detected_but_no_rows",
    "no_supported_sidearm_roster_template_found",
}


@dataclass(frozen=True)
class ParsedRosterPlayer:
    row_number: int
    full_name: str
    first_name: str | None
    last_name: str | None
    jersey_number: str | None
    position: str | None
    academic_year: str | None
    height: str | None
    weight: str | None
    bats: str | None
    throws: str | None
    hometown: str | None
    high_school: str | None
    previous_school: str | None
    profile_url: str | None


@dataclass(frozen=True)
class SidearmParseDiagnostic:
    code: str
    detail: str | None = None

    def as_message(self) -> str:
        if self.detail is None:
            return self.code
        return f"{self.code}: {self.detail}"


@dataclass(frozen=True)
class ParsedRosterDocument:
    players: list[ParsedRosterPlayer]
    diagnostics: list[SidearmParseDiagnostic]


class SidearmImportFailure(ValueError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = reason
        self.detail = detail
        if detail is None:
            message = reason
        else:
            message = f"{reason}: {detail}"
        super().__init__(message)


def fetch_roster_html(url: str) -> str:
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise SidearmImportFailure("http_404", url) from exc
        raise SidearmImportFailure(
            "fetch_failed",
            f"status={exc.response.status_code} url={url}",
        ) from exc
    except httpx.HTTPError as exc:
        normalized_error = normalize_vendor_verification_error(exc)
        if normalized_error == "ssl_certificate_verify_failed":
            raise SidearmImportFailure("ssl_certificate_verify_failed", url) from exc
        if normalized_error == "timeout":
            raise SidearmImportFailure("timeout", url) from exc
        raise SidearmImportFailure("fetch_failed", str(exc)) from exc
    return response.text


def parse_sidearm_roster_document(html: str, source_url: str, season: int) -> ParsedRosterDocument:
    soup = BeautifulSoup(html, "lxml")
    diagnostics = _collect_title_diagnostics(soup, season)

    legacy_table_players = _parse_table_players(soup, source_url)
    if legacy_table_players:
        return ParsedRosterDocument(players=legacy_table_players, diagnostics=diagnostics)

    legacy_card_players = _parse_card_players(soup, source_url)
    if legacy_card_players:
        return ParsedRosterDocument(players=legacy_card_players, diagnostics=diagnostics)

    person_card_players = _parse_person_card_players(soup, source_url)
    if person_card_players:
        return ParsedRosterDocument(players=person_card_players, diagnostics=diagnostics)

    raise _build_parse_failure(soup, diagnostics)


def parse_sidearm_roster(html: str, source_url: str, season: int) -> list[ParsedRosterPlayer]:
    return parse_sidearm_roster_document(html, source_url, season).players


def parsed_players_to_rows(players: Sequence[ParsedRosterPlayer]) -> list[RosterImportRow]:
    return [
        RosterImportRow(
            row_number=player.row_number,
            full_name=player.full_name,
            first_name=player.first_name,
            last_name=player.last_name,
            roster_year=player.academic_year,
            position=player.position,
            height=player.height,
            weight=player.weight,
            bats=player.bats,
            throws=player.throws,
            hometown=player.hometown,
            high_school=player.high_school,
            previous_school=player.previous_school,
            jersey_number=player.jersey_number,
            profile_url=player.profile_url,
        )
        for player in players
    ]


def get_school_source_row(path: Path, school_id: str) -> SchoolSourceRow:
    for row in read_school_source_rows(path):
        if row.school_id == school_id:
            return row
    raise ValueError(f"school not found in source file: {school_id}")


def is_sidearm_school_eligible(row: SchoolSourceRow) -> bool:
    return (
        row.roster_vendor == SIDEARM_VENDOR
        and row.is_sidearm
        and row.import_enabled
        and row.roster_url is not None
    )


def list_sidearm_school_source_rows(path: Path) -> list[SchoolSourceRow]:
    rows = read_school_source_rows(path)
    return [row for row in rows if is_sidearm_school_eligible(row)]


def require_sidearm_school_source_row(path: Path, school_id: str) -> SchoolSourceRow:
    school = get_school_source_row(path, school_id)
    if is_sidearm_school_eligible(school):
        return school
    raise ValueError(
        "school is not eligible for Sidearm import: must have roster_vendor=sidearm, "
        "is_sidearm=true, import_enabled=true, and roster_url present"
    )


def select_sidearm_school_source_rows(
    path: Path,
    *,
    school_id: str | None = None,
    limit: int | None = None,
) -> tuple[int, list[SchoolSourceRow]]:
    eligible_rows = list_sidearm_school_source_rows(path)
    if school_id is not None:
        return len(eligible_rows), [require_sidearm_school_source_row(path, school_id)]
    if limit is None:
        return len(eligible_rows), eligible_rows
    return len(eligible_rows), eligible_rows[:limit]


def build_roster_import_service(session: Session) -> RosterImportService:
    return RosterImportService(
        colleges=CollegeRepository(session),
        people=PersonRepository(session),
        players=PlayerRepository(session),
        positions=PositionRepository(session),
        high_schools=HighSchoolRepository(session),
        rosters=PlayerRosterRepository(session),
    )


def build_sidearm_import_service(session: Session) -> SidearmRosterImportService:
    colleges = CollegeRepository(session)
    return SidearmRosterImportService(
        colleges=colleges,
        roster_imports=build_roster_import_service(session),
    )


def run_import_school(
    school: SchoolSourceRow,
    season: int,
    url: str | None = None,
    fetch_html: Callable[[str], str] = fetch_roster_html,
    dry_run: bool = False,
) -> RosterImportSummary:
    source_url = clean_text(url) or school.roster_url
    if source_url is None:
        raise ValueError(f"school is missing a roster URL: {school.school_id}")

    html = fetch_html(source_url)
    parsed_roster = parse_sidearm_roster_document(html, source_url, season)
    rows = parsed_players_to_rows(parsed_roster.players)

    session = SessionLocal()
    try:
        service = build_sidearm_import_service(session)
        summary = service.import_rows(school, rows, year=season, source_url=source_url)
        for diagnostic in parsed_roster.diagnostics:
            summary.add_error(None, diagnostic.as_message())
        if dry_run:
            session.rollback()
        else:
            session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_import(
    school_id: str,
    season: int,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    url: str | None = None,
    fetch_html: Callable[[str], str] = fetch_roster_html,
    dry_run: bool = False,
) -> RosterImportSummary:
    school = require_sidearm_school_source_row(sources_path, school_id)
    return run_import_school(
        school=school,
        season=season,
        url=url,
        fetch_html=fetch_html,
        dry_run=dry_run,
    )


def run_import_all(
    season: int,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    school_id: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    failure_report_path: Path | None = None,
    fetch_html: Callable[[str], str] = fetch_roster_html,
    import_school: Callable[
        [SchoolSourceRow, int, str | None, Callable[[str], str], bool], RosterImportSummary
    ] = run_import_school,
    progress_callback: Callable[[int, int, SchoolSourceRow], None] | None = None,
) -> SidearmBatchImportSummary:
    schools_seen = len(read_school_source_rows(sources_path))
    schools_eligible, schools = select_sidearm_school_source_rows(
        sources_path,
        school_id=school_id,
        limit=limit,
    )
    summary = SidearmBatchImportSummary(
        schools_seen=schools_seen,
        schools_eligible=schools_eligible,
        schools_attempted=len(schools),
        schools_selected=len(schools),
        dry_run=dry_run,
    )

    for index, school in enumerate(schools, start=1):
        if progress_callback is not None:
            progress_callback(index, len(schools), school)
        try:
            school_summary = import_school(school, season, None, fetch_html, dry_run)
        except Exception as exc:  # noqa: BLE001
            failure_reason, failure_detail = _classify_import_exception(exc)
            summary.add_result(
                SidearmBatchSchoolResult(
                    school_id=school.school_id,
                    school_name=school.school_name,
                    source_url=school.roster_url,
                    success=False,
                    failure_reason=failure_reason,
                    error=failure_detail,
                )
            )
            continue

        summary.add_result(
            SidearmBatchSchoolResult(
                school_id=school.school_id,
                school_name=school.school_name,
                source_url=school.roster_url,
                success=True,
                summary=school_summary,
            )
        )

    if summary.schools_failed > 0:
        report_path = failure_report_path or default_failure_report_path(season)
        write_failure_report(summary, report_path, season=season)

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import verified Sidearm baseball rosters for one school or a controlled batch."
        )
    )
    parser.add_argument(
        "--school-id",
        help="School ID from the source CSV, such as S66",
    )
    parser.add_argument(
        "--all-schools",
        action="store_true",
        help="Import all verified, enabled Sidearm schools from the source CSV.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit batch imports to the first N verified, enabled Sidearm schools.",
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Integer season year, such as 2026",
    )
    parser.add_argument(
        "--schools-csv",
        "--sources-file",
        type=Path,
        dest="sources_file",
        default=DEFAULT_SOURCES_PATH,
        help=f"School source CSV path, default: {DEFAULT_SOURCES_PATH}",
    )
    parser.add_argument(
        "--url",
        help="Optional roster URL override. Defaults to the roster_url from the source CSV.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and simulate imports, then roll back database changes.",
    )
    parser.add_argument(
        "--failure-report-path",
        type=Path,
        help="Optional JSON path for batch failure details.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.school_id is None and not args.all_schools and args.limit is None:
        parser.error("choose --school-id, --limit, or --all-schools")
    if args.all_schools and args.url:
        parser.error("--url can only be used with --school-id")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")
    if args.school_id is not None and args.limit is not None:
        parser.error("--limit cannot be used with --school-id")

    if args.school_id is None:
        batch_summary = run_import_all(
            season=args.season,
            sources_path=args.sources_file,
            limit=None if args.all_schools else args.limit,
            dry_run=args.dry_run,
            failure_report_path=args.failure_report_path,
            progress_callback=_print_batch_progress,
        )
        output = _build_batch_cli_summary(batch_summary)
    else:
        summary = run_import(
            school_id=args.school_id,
            season=args.season,
            sources_path=args.sources_file,
            url=args.url,
            dry_run=args.dry_run,
        )
        output = _build_single_cli_summary(summary, dry_run=args.dry_run)
    print(json.dumps(output, indent=2))
    return 0


def _print_batch_progress(index: int, total: int, school: SchoolSourceRow) -> None:
    print(
        f"processing school {index} of {total}: {school.school_id} {school.school_name}",
        file=sys.stderr,
        flush=True,
    )


def _build_batch_cli_summary(summary: SidearmBatchImportSummary) -> dict[str, object]:
    failed_schools = [
        {
            "school_id": result.school_id,
            "school_name": result.school_name,
            "reason": result.failure_reason or "unknown_failure",
            "error": result.error or "unknown error",
        }
        for result in summary.results
        if not result.success
    ]
    return {
        "dry_run": summary.dry_run,
        "schools_seen": summary.schools_seen,
        "schools_eligible": summary.schools_eligible,
        "schools_attempted": summary.schools_attempted,
        "schools_selected": summary.schools_selected,
        "schools_imported": summary.schools_imported,
        "schools_failed": summary.schools_failed,
        "players_seen": summary.players_seen,
        "players_imported": summary.players_imported,
        "players_updated": summary.players_updated,
        "roster_rows_created": summary.roster_rows_created,
        "roster_rows_updated": summary.roster_rows_updated,
        "failures_by_reason": summary.failures_by_reason,
        "failure_report_path": summary.failure_report_path,
        "failed_schools": failed_schools,
    }


def _build_single_cli_summary(summary: RosterImportSummary, *, dry_run: bool) -> dict[str, object]:
    return {
        "dry_run": dry_run,
        "players_seen": summary.rows_seen,
        "players_imported": summary.rows_imported,
        "players_updated": summary.players_updated,
        "roster_rows_created": summary.rosters_created,
        "roster_rows_updated": summary.rosters_updated,
        "errors": [error.model_dump() for error in summary.errors],
    }


def default_failure_report_path(season: int) -> Path:
    return DEFAULT_FAILURE_REPORT_DIR / f"sidearm_roster_failures_{season}.json"


def write_failure_report(
    summary: SidearmBatchImportSummary,
    path: Path,
    *,
    season: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    failures = [
        {
            "school_id": result.school_id,
            "school_name": result.school_name,
            "source_url": result.source_url,
            "reason": result.failure_reason,
            "error": result.error,
        }
        for result in summary.results
        if not result.success
    ]
    path.write_text(
        json.dumps(
            {
                "season": season,
                "dry_run": summary.dry_run,
                "schools_failed": summary.schools_failed,
                "failures_by_reason": summary.failures_by_reason,
                "failures": failures,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    summary.failure_report_path = str(path)


def _classify_import_exception(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, SidearmImportFailure):
        if exc.reason == "http_404":
            return "stale_url_or_not_found", str(exc)
        if exc.reason == "fetch_failed":
            normalized_error = normalize_vendor_verification_error(exc)
            if normalized_error == "ssl_certificate_verify_failed":
                return "ssl_certificate_verify_failed", str(exc)
            if normalized_error == "timeout":
                return "timeout", str(exc)
            return "fetch_failed", str(exc)
        if exc.reason in SIDEARM_PARSE_FAILURE_REASONS:
            return exc.reason, str(exc)
        return exc.reason, str(exc)

    normalized_error = normalize_vendor_verification_error(exc)
    if normalized_error == "ssl_certificate_verify_failed":
        return "ssl_certificate_verify_failed", str(exc)
    if normalized_error == "timeout":
        return "timeout", str(exc)
    return "unexpected_error", str(exc)


def _collect_title_diagnostics(soup: BeautifulSoup, season: int) -> list[SidearmParseDiagnostic]:
    expected = f"{season} Baseball Roster"
    haystacks = _collect_title_haystacks(soup)
    if any(expected in value for value in haystacks):
        return []

    sample = " | ".join(haystacks[:3]) if haystacks else "no title or heading text found"
    return [
        SidearmParseDiagnostic(
            code="title_mismatch",
            detail=f"expected {expected!r}; checked {sample}",
        )
    ]


def _collect_title_haystacks(soup: BeautifulSoup) -> list[str]:
    candidates: list[str] = []

    def add_text(value: str | None) -> None:
        text = clean_text(value)
        if text is not None and text not in candidates:
            candidates.append(text)

    if soup.title is not None:
        add_text(soup.title.get_text(" ", strip=True))
    for selector in ("h1", "h2", ".c-rosterpage__header", ".c-rosterpage__header--tablet"):
        for element in soup.select(selector):
            add_text(element.get_text(" ", strip=True))
    return candidates


def _parse_table_players(soup: BeautifulSoup, source_url: str) -> list[ParsedRosterPlayer]:
    for table in soup.select("table.sidearm-table"):
        if table.select_one("td.sidearm-table-player-name") is None:
            continue
        players: list[ParsedRosterPlayer] = []
        for index, row in enumerate(table.select("tbody tr"), start=1):
            name_cell = row.select_one("td.sidearm-table-player-name")
            if name_cell is None:
                continue
            player = _build_player_from_table_row(row, index, source_url)
            if player is not None:
                players.append(player)
        if players:
            return players
    return []


def _build_player_from_table_row(
    row: Tag, row_number: int, source_url: str
) -> ParsedRosterPlayer | None:
    name_cell = row.select_one("td.sidearm-table-player-name")
    if name_cell is None:
        return None
    full_name = clean_text(name_cell.get_text(" ", strip=True))
    if full_name is None:
        return None

    name_parts = split_name(full_name)
    if name_parts is None:
        return None

    hometown, high_school = _split_hometown_high_school(
        clean_text(_cell_text(row, ".hometownhighschool"))
    )
    bats, throws = _split_bats_throws(_cell_text(row, ".rp_custom2"))
    profile_link = row.select_one("td.sidearm-table-player-name a")

    return ParsedRosterPlayer(
        row_number=row_number,
        full_name=name_parts.full_name,
        first_name=name_parts.first_name,
        last_name=name_parts.last_name,
        jersey_number=_cell_text(row, ".roster_jerseynum"),
        position=_cell_text(row, ".rp_position_short"),
        academic_year=_cell_text(row, ".roster_class"),
        height=_cell_text(row, ".height"),
        weight=_cell_text(row, ".rp_weight"),
        bats=bats,
        throws=throws,
        hometown=hometown,
        high_school=high_school,
        previous_school=_cell_text(row, ".player_previous_school"),
        profile_url=_resolve_href(source_url, profile_link),
    )


def _parse_card_players(soup: BeautifulSoup, source_url: str) -> list[ParsedRosterPlayer]:
    players: list[ParsedRosterPlayer] = []
    for index, item in enumerate(soup.select("li.sidearm-roster-player"), start=1):
        name_link = item.select_one(".sidearm-roster-player-name a")
        full_name = clean_text(name_link.get_text(" ", strip=True) if name_link else None)
        if full_name is None:
            continue
        name_parts = split_name(full_name)
        if name_parts is None:
            continue

        bats, throws = _split_bats_throws(_player_text(item, ".sidearm-roster-player-custom2"))
        players.append(
            ParsedRosterPlayer(
                row_number=index,
                full_name=name_parts.full_name,
                first_name=name_parts.first_name,
                last_name=name_parts.last_name,
                jersey_number=_player_text(item, ".sidearm-roster-player-jersey-number"),
                position=_player_text(item, ".sidearm-roster-player-position .text-bold"),
                academic_year=_player_text(item, ".sidearm-roster-player-academic-year"),
                height=_normalize_card_height(_player_text(item, ".sidearm-roster-player-height")),
                weight=_normalize_card_weight(_player_text(item, ".sidearm-roster-player-weight")),
                bats=bats,
                throws=throws,
                hometown=_player_text(item, ".sidearm-roster-player-hometown"),
                high_school=_player_text(item, ".sidearm-roster-player-highschool"),
                previous_school=_player_text(item, ".sidearm-roster-player-previous-school"),
                profile_url=_resolve_href(source_url, name_link),
            )
        )
    return players


def _parse_person_card_players(soup: BeautifulSoup, source_url: str) -> list[ParsedRosterPlayer]:
    players: list[ParsedRosterPlayer] = []
    seen_keys: set[tuple[str, str | None]] = set()

    for index, card in enumerate(soup.select(".c-rosterpage__players .s-person-card"), start=1):
        player = _build_player_from_person_card(card, index, source_url)
        if player is None:
            continue
        player_key = (player.full_name, player.profile_url)
        if player_key in seen_keys:
            continue
        seen_keys.add(player_key)
        players.append(player)

    return players


def _build_player_from_person_card(
    card: Tag, row_number: int, source_url: str
) -> ParsedRosterPlayer | None:
    name_link = card.select_one(
        '[data-test-id="s-person-details__personal-single-line-person-link"], '
        ".s-person-details__personal a[href]"
    )
    href = clean_text(name_link.get("href") if name_link is not None else None)
    if href is not None and "/coaches/" in href:
        return None

    full_name = clean_text(name_link.get_text(" ", strip=True) if name_link is not None else None)
    if full_name is None:
        return None

    name_parts = split_name(full_name)
    if name_parts is None:
        return None

    labeled_values = _person_card_labeled_values(card)
    if not any(
        labeled_values.get(field_name) is not None
        for field_name in ("Jersey Number", "Position", "Academic Year")
    ):
        return None

    last_school = labeled_values.get("Previous School") or labeled_values.get("Last School")
    high_school, previous_school = _classify_person_card_school(last_school)
    bats, throws = _split_bats_throws(
        labeled_values.get("Custom Field 1") or labeled_values.get("Custom Field 2")
    )

    return ParsedRosterPlayer(
        row_number=row_number,
        full_name=name_parts.full_name,
        first_name=name_parts.first_name,
        last_name=name_parts.last_name,
        jersey_number=labeled_values.get("Jersey Number"),
        position=labeled_values.get("Position"),
        academic_year=labeled_values.get("Academic Year"),
        height=_normalize_card_height(labeled_values.get("Height")),
        weight=_normalize_card_weight(labeled_values.get("Weight")),
        bats=bats,
        throws=throws,
        hometown=labeled_values.get("Hometown"),
        high_school=high_school,
        previous_school=previous_school,
        profile_url=_resolve_href(source_url, name_link),
    )


def _person_card_labeled_values(card: Tag) -> dict[str, str]:
    values: dict[str, str] = {}
    for selector in (
        ".s-stamp__text",
        ".s-person-details__bio-stats-item",
        ".s-person-card__content__location span",
    ):
        for element in card.select(selector):
            labeled_value = _extract_labeled_value(element)
            if labeled_value is None:
                continue
            label, value = labeled_value
            values.setdefault(label, value)
    return values


def _extract_labeled_value(element: Tag) -> tuple[str, str] | None:
    label_element = next(
        (
            child
            for child in element.children
            if isinstance(child, Tag) and _tag_has_class(child, "sr-only")
        ),
        None,
    )
    if label_element is None:
        return None

    label = clean_text(label_element.get_text(" ", strip=True))
    text = clean_text(element.get_text(" ", strip=True))
    if label is None or text is None:
        return None

    if text.startswith(label):
        value = clean_text(text.removeprefix(label))
    else:
        value = clean_text(text.replace(label, "", 1))
    if value is None:
        return None
    return label, value


def _tag_has_class(tag: Tag, class_name: str) -> bool:
    classes = tag.get("class")
    if not isinstance(classes, list):
        return False
    return class_name in classes


def _classify_person_card_school(value: str | None) -> tuple[str | None, str | None]:
    school = clean_text(value)
    if school is None:
        return None, None

    lower_school = school.lower()
    college_markers = (
        "university",
        "college",
        "state",
        "community college",
        "junior college",
        "cc",
    )
    if any(marker in lower_school for marker in college_markers):
        return None, school
    return school, None


def _build_parse_failure(
    soup: BeautifulSoup, diagnostics: list[SidearmParseDiagnostic]
) -> SidearmImportFailure:
    detail_parts = [diagnostic.as_message() for diagnostic in diagnostics]

    if soup.select(".c-rosterpage__players"):
        if soup.select(".c-rosterpage__players .s-person-card"):
            detail_parts.append("found .c-rosterpage__players and .s-person-card")
            return SidearmImportFailure(
                "supported_template_found_but_no_player_cards",
                "; ".join(detail_parts),
            )
        detail_parts.append("found .c-rosterpage__players but no .s-person-card")
        return SidearmImportFailure(
            "person_card_template_detected_but_no_cards",
            "; ".join(detail_parts),
        )

    if soup.select("table.sidearm-table") or soup.select("li.sidearm-roster-player"):
        detail_parts.append("found legacy Sidearm selectors but parsed no players")
        return SidearmImportFailure(
            "legacy_template_detected_but_no_rows",
            "; ".join(detail_parts),
        )

    detail_parts.append("no legacy or person-card Sidearm selectors found")
    return SidearmImportFailure(
        "no_supported_sidearm_roster_template_found",
        "; ".join(detail_parts),
    )


def _cell_text(row: Tag, selector: str) -> str | None:
    cell = row.select_one(selector)
    return clean_text(cell.get_text(" ", strip=True) if cell else None)


def _player_text(item: Tag, selector: str) -> str | None:
    element = item.select_one(selector)
    return clean_text(element.get_text(" ", strip=True) if element else None)


def _split_bats_throws(value: str | None) -> tuple[str | None, str | None]:
    text = clean_text(value)
    if text is None:
        return None, None
    parts = [clean_text(part) for part in text.split("/")]
    bats = parts[0] if parts else None
    throws = parts[1] if len(parts) > 1 else None
    return bats, throws


def _split_hometown_high_school(value: str | None) -> tuple[str | None, str | None]:
    text = clean_text(value)
    if text is None:
        return None, None
    hometown, separator, high_school = text.partition(" / ")
    if not separator:
        return text, None
    return clean_text(hometown), clean_text(high_school)


def _resolve_href(source_url: str, link: Tag | None) -> str | None:
    if link is None:
        return None
    href = clean_text(link.get("href"))
    if href is None:
        return None
    return urljoin(source_url, href)


def _normalize_card_height(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    match = re.fullmatch(r"(?P<feet>\d+)'\s*(?P<inches>\d+)(?:''|\")", text)
    if match is not None:
        return f"{match.group('feet')}-{match.group('inches')}"
    normalized = text.replace("'", "-").replace('"', "")
    return clean_text(normalized.replace(" ", ""))


def _normalize_card_weight(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    return text.replace(" lbs", "")


if __name__ == "__main__":
    raise SystemExit(main())
