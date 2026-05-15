from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.importers.roster_spreadsheet import read_roster_rows


def test_read_csv_roster_rows() -> None:
    path = Path("tests/fixtures/roster_import_sample.csv")

    rows = read_roster_rows(path)

    assert len(rows) == 2
    assert rows[0].college == "Example State"
    assert rows[0].full_name == "Alex Example"
    assert rows[1].previous_school == "Other College"


def test_read_xlsx_roster_rows_defaults_to_cleaned_data(tmp_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Cleaned Data"
    worksheet.append(["College", "Player", "Position", "Height", "Weight", "B/T"])
    worksheet.append(["Example Tech", "Taylor Test", "C", "6-0", "190", "R/R"])
    path = tmp_path / "sample.xlsx"
    workbook.save(path)

    rows = read_roster_rows(path)

    assert len(rows) == 1
    assert rows[0].college == "Example Tech"
    assert rows[0].full_name == "Taylor Test"
    assert rows[0].position == "C"
