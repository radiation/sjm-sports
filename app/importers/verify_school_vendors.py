from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path

import httpx

from app.schemas.school_sources import (
    SCHOOL_SOURCE_FIELDNAMES,
    SchoolSourceRow,
    SchoolSourceVendorVerificationSummary,
)
from app.services.school_sources import SchoolSourceVendorVerificationService

DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)


def read_school_source_csv(path: Path) -> tuple[list[str], list[SchoolSourceRow]]:
    with path.open("r", encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)
        fieldnames = list(reader.fieldnames or SCHOOL_SOURCE_FIELDNAMES)
        for fieldname in SCHOOL_SOURCE_FIELDNAMES:
            if fieldname not in fieldnames:
                fieldnames.append(fieldname)

        rows = [SchoolSourceRow.model_validate(raw_row) for raw_row in reader]
    return fieldnames, rows


def write_school_source_csv(
    path: Path, fieldnames: Sequence[str], rows: Sequence[SchoolSourceRow]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            values = row.model_dump()
            writer.writerow({fieldname: values.get(fieldname, "") for fieldname in fieldnames})


def default_verified_output_path(path: Path) -> Path:
    if path.suffix:
        return path.with_name(f"{path.stem}.verified{path.suffix}")
    return path.with_name(f"{path.name}.verified.csv")


def fetch_roster_html(url: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=timeout_seconds,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def run_verification(
    input_path: Path,
    *,
    output_path: Path | None = None,
    in_place: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[Path, SchoolSourceVendorVerificationSummary]:
    fieldnames, rows = read_school_source_csv(input_path)

    def fetch_html(url: str) -> str:
        return fetch_roster_html(url, timeout_seconds=timeout_seconds)

    service = SchoolSourceVendorVerificationService(fetch_html=fetch_html)
    verified_rows, summary = service.verify_rows(rows)
    target_path = (
        input_path if in_place else output_path or default_verified_output_path(input_path)
    )
    write_school_source_csv(target_path, fieldnames, verified_rows)
    return target_path, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify school roster vendors from live roster HTML and write a reviewed CSV."
    )
    parser.add_argument("path", type=Path, help="Path to the school source CSV file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output CSV path. Defaults to <input>.verified.csv unless --in-place is used.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input CSV instead of writing a separate verified file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_path, summary = run_verification(
        args.path,
        output_path=args.output,
        in_place=args.in_place,
        timeout_seconds=args.timeout,
    )
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                **summary.model_dump(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
