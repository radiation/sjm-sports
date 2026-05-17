from __future__ import annotations

from collections.abc import Callable, Sequence

from app.schemas.school_sources import SchoolSourceRow, SchoolSourceVendorVerificationSummary
from app.utils.roster_normalization import clean_text
from app.utils.school_sources import (
    detect_roster_vendor,
    merge_school_source_note,
    normalize_vendor_verification_error,
)


class SchoolSourceVendorVerificationService:
    def __init__(self, fetch_html: Callable[[str], str]) -> None:
        self.fetch_html = fetch_html

    def verify_rows(
        self, rows: Sequence[SchoolSourceRow]
    ) -> tuple[list[SchoolSourceRow], SchoolSourceVendorVerificationSummary]:
        summary = SchoolSourceVendorVerificationSummary(rows_seen=len(rows))
        verified_rows: list[SchoolSourceRow] = []

        for row in rows:
            verified_row = row
            roster_url = clean_text(row.roster_url)
            if roster_url is None:
                summary.rows_without_url += 1
                verified_rows.append(verified_row)
                continue

            summary.rows_checked += 1
            try:
                html = self.fetch_html(roster_url)
            except Exception as exc:  # noqa: BLE001
                error_message = normalize_vendor_verification_error(exc)
                verified_row = row.model_copy(
                    update={
                        "notes": merge_school_source_note(
                            row.notes, f"vendor_verification_failed: {error_message}"
                        )
                    }
                )
                summary.failed_count += 1
                summary.add_error(f"{row.school_id}: {error_message}")
            else:
                detection = detect_roster_vendor(roster_url, html)
                verified_row = row.model_copy(
                    update={
                        "roster_vendor": detection.vendor,
                        "is_sidearm": detection.is_sidearm,
                        "notes": merge_school_source_note(
                            row.notes, f"vendor_verified_html: {detection.note}"
                        ),
                    }
                )
                summary.record_vendor(detection.vendor)

            if verified_row != row:
                summary.rows_updated += 1
            verified_rows.append(verified_row)

        return verified_rows, summary
