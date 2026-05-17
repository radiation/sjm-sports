from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from app.importers.school_source_builder import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_WORKBOOK_PATH,
    build_school_sources_csv,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build data/schools.csv from the roster workbook.")
    parser.add_argument(
        "workbook",
        nargs="?",
        type=Path,
        default=DEFAULT_WORKBOOK_PATH,
        help=f"Workbook path, default: {DEFAULT_WORKBOOK_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output CSV path, default: {DEFAULT_OUTPUT_PATH}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = build_school_sources_csv(args.workbook, args.output)
    print(f"Wrote {summary.rows_written} school sources to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
