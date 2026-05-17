from __future__ import annotations

import csv
from pathlib import Path

from app.importers.verify_school_vendors import read_school_source_csv, write_school_source_csv
from app.schemas.school_sources import SchoolSourceRow
from app.services.school_sources import SchoolSourceVendorVerificationService
from app.utils.school_sources import classify_roster_vendor_from_html


def test_classify_roster_vendor_from_html_detects_sidearm_footer_links() -> None:
    vendor, is_sidearm = classify_roster_vendor_from_html(
        """
        <html>
          <footer>
            <a href=\"https://www.sidearmsports.com/terms-of-service\">Terms of Service</a>
          </footer>
        </html>
        """
    )

    assert vendor == "sidearm"
    assert is_sidearm is True


def test_classify_roster_vendor_from_html_detects_sidearm_visible_text() -> None:
    vendor, is_sidearm = classify_roster_vendor_from_html(
        "<html><body><footer>Site by Sidearm Sports</footer></body></html>"
    )

    assert vendor == "sidearm"
    assert is_sidearm is True


def test_classify_roster_vendor_from_html_detects_powered_by_sidearm_text() -> None:
    vendor, is_sidearm = classify_roster_vendor_from_html(
        "<html><body><footer>Powered by SIDEARM</footer></body></html>"
    )

    assert vendor == "sidearm"
    assert is_sidearm is True


def test_classify_roster_vendor_from_html_detects_sidearm_image_alt_text() -> None:
    vendor, is_sidearm = classify_roster_vendor_from_html(
        '<html><body><img src="logo.png" alt="Sidearm Sports logo"></body></html>'
    )

    assert vendor == "sidearm"
    assert is_sidearm is True


def test_classify_roster_vendor_from_html_returns_unknown_without_marker() -> None:
    vendor, is_sidearm = classify_roster_vendor_from_html(
        "<html><body><main>Example baseball roster page.</main></body></html>"
    )

    assert vendor == "unknown"
    assert is_sidearm is False


def test_vendor_verification_service_downgrades_heuristic_sidearm_without_html_marker() -> None:
    row = SchoolSourceRow(
        school_id="S1",
        school_name="Example State",
        roster_url="https://example.edu/sports/baseball/roster",
        roster_vendor="sidearm",
        is_sidearm=True,
        import_enabled=True,
    )
    service = SchoolSourceVendorVerificationService(
        fetch_html=lambda _url: "<html><body><main>No vendor markers here.</main></body></html>"
    )

    verified_rows, summary = service.verify_rows([row])

    assert verified_rows[0].roster_vendor == "unknown"
    assert verified_rows[0].is_sidearm is False
    assert verified_rows[0].notes == "vendor_verified_html: no known vendor marker"
    assert summary.rows_checked == 1
    assert summary.unknown_count == 1


def test_vendor_verification_service_handles_fetch_failures() -> None:
    row = SchoolSourceRow(
        school_id="S1",
        school_name="Example State",
        roster_url="https://example.edu/sports/baseball/roster",
        roster_vendor="sidearm",
        is_sidearm=True,
        import_enabled=True,
    )

    def fetch_html(_url: str) -> str:
        raise TimeoutError("timeout")

    service = SchoolSourceVendorVerificationService(fetch_html=fetch_html)

    verified_rows, summary = service.verify_rows([row])

    assert verified_rows[0].roster_vendor == "sidearm"
    assert verified_rows[0].is_sidearm is True
    assert verified_rows[0].notes == "vendor_verification_failed: timeout"
    assert summary.failed_count == 1
    assert summary.errors == ["S1: timeout"]


def test_write_school_source_csv_preserves_columns_and_row_count(tmp_path: Path) -> None:
    input_path = tmp_path / "schools.csv"
    with input_path.open("w", encoding="utf-8", newline="") as source_file:
        writer = csv.DictWriter(
            source_file,
            fieldnames=[
                "school_id",
                "school_name",
                "roster_url",
                "roster_vendor",
                "is_sidearm",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "school_id": "S1",
                "school_name": "Example State",
                "roster_url": "https://example.edu/sports/baseball/roster",
                "roster_vendor": "sidearm",
                "is_sidearm": "True",
                "notes": "vendor_verified_html: sidearm visible text",
            }
        )
        writer.writerow(
            {
                "school_id": "S2",
                "school_name": "Other State",
                "roster_url": "",
                "roster_vendor": "unknown",
                "is_sidearm": "False",
                "notes": "",
            }
        )

    fieldnames, rows = read_school_source_csv(input_path)
    output_path = tmp_path / "schools.verified.csv"
    write_school_source_csv(output_path, fieldnames, rows)

    with output_path.open("r", encoding="utf-8", newline="") as verified_file:
        reader = csv.DictReader(verified_file)
        verified_rows = list(reader)

    assert reader.fieldnames == fieldnames
    assert len(verified_rows) == 2
    assert verified_rows[0]["school_id"] == "S1"
    assert verified_rows[1]["school_id"] == "S2"
