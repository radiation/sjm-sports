from __future__ import annotations

from pydantic import BaseModel, Field


class RosterImportRow(BaseModel):
    row_number: int
    college: str | None = None
    college_state: str | None = None
    college_division: str | None = None
    conference: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    roster_year: str | None = None
    position: str | None = None
    height: str | None = None
    weight: str | None = None
    bats_throws: str | None = None
    bats: str | None = None
    throws: str | None = None
    hometown: str | None = None
    hometown_city: str | None = None
    hometown_state: str | None = None
    hometown_country: str | None = None
    high_school: str | None = None
    previous_school: str | None = None
    is_transfer: str | None = None
    jersey_number: str | None = None
    roster_url: str | None = None
    profile_url: str | None = None


class RosterImportError(BaseModel):
    row_number: int | None = None
    message: str


class RosterImportSummary(BaseModel):
    rows_seen: int = 0
    rows_imported: int = 0
    rows_skipped: int = 0
    players_created: int = 0
    players_updated: int = 0
    colleges_created: int = 0
    positions_created: int = 0
    high_schools_created: int = 0
    rosters_created: int = 0
    rosters_updated: int = 0
    errors: list[RosterImportError] = Field(default_factory=list)

    def add_error(self, row_number: int | None, message: str) -> None:
        self.errors.append(RosterImportError(row_number=row_number, message=message))


class SidearmBatchSchoolResult(BaseModel):
    school_id: str
    school_name: str
    source_url: str | None = None
    success: bool
    summary: RosterImportSummary | None = None
    error: str | None = None


class SidearmBatchImportSummary(BaseModel):
    schools_seen: int = 0
    schools_selected: int = 0
    schools_imported: int = 0
    schools_failed: int = 0
    results: list[SidearmBatchSchoolResult] = Field(default_factory=list)

    def add_result(self, result: SidearmBatchSchoolResult) -> None:
        self.results.append(result)
        if result.success:
            self.schools_imported += 1
        else:
            self.schools_failed += 1
