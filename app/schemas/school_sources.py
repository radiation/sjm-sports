from __future__ import annotations

from pydantic import BaseModel, Field

SCHOOL_SOURCE_FIELDNAMES = [
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


class SchoolSourceRow(BaseModel):
    school_id: str
    ipeds_id: str | None = None
    school_name: str
    city: str | None = None
    state: str | None = None
    public_private: str | None = None
    division: str | None = None
    conference: str | None = None
    roster_url: str | None = None
    roster_vendor: str = "unknown"
    is_sidearm: bool = False
    import_enabled: bool = False
    notes: str | None = None


class SchoolSourceBuildSummary(BaseModel):
    workbook_path: str
    rows_written: int


class SchoolSourceImportSummary(BaseModel):
    rows_seen: int = 0
    rows_imported: int = 0
    rows_skipped: int = 0
    colleges_created: int = 0
    colleges_updated: int = 0
    errors: list[str] = Field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)


class SchoolSourceVendorVerificationSummary(BaseModel):
    rows_seen: int = 0
    rows_without_url: int = 0
    rows_checked: int = 0
    rows_verified: int = 0
    rows_updated: int = 0
    sidearm_count: int = 0
    presto_count: int = 0
    unknown_count: int = 0
    failed_count: int = 0
    vendor_counts: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def record_vendor(self, vendor: str) -> None:
        self.rows_verified += 1
        self.vendor_counts[vendor] = self.vendor_counts.get(vendor, 0) + 1
        if vendor == "sidearm":
            self.sidearm_count += 1
        elif vendor == "presto":
            self.presto_count += 1
        elif vendor == "unknown":
            self.unknown_count += 1
