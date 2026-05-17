from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path

from app.core.database import SessionLocal
from app.repositories.schools import CollegeRepository
from app.schemas.school_sources import SchoolSourceImportSummary, SchoolSourceRow
from app.services.imports import SchoolSourceImportService
from app.utils.school_sources import normalize_school_source_row


def read_school_source_rows(path: Path) -> list[SchoolSourceRow]:
    with path.open("r", encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)
        rows: list[SchoolSourceRow] = []
        for raw_row in reader:
            row = SchoolSourceRow.model_validate(raw_row)
            rows.append(normalize_school_source_row(row, infer_vendor_from_url=False))
        return rows


def run_import(path: Path) -> SchoolSourceImportSummary:
    rows = read_school_source_rows(path)
    session = SessionLocal()
    try:
        service = SchoolSourceImportService(colleges=CollegeRepository(session))
        summary = service.import_rows(rows)
        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import school source seed CSV into colleges.")
    parser.add_argument("path", type=Path, help="Path to the school source CSV file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = run_import(args.path)
    print(json.dumps(summary.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
