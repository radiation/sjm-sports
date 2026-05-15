from __future__ import annotations

from app.utils.roster_normalization import (
    normalize_position,
    normalize_roster_year,
    parse_bats_throws,
    parse_height_inches,
    parse_hometown,
    parse_transfer_flag,
    parse_weight_lbs,
    split_name,
)


def test_parse_height_inches() -> None:
    assert parse_height_inches("6-2") == 74
    assert parse_height_inches("5'11\"") == 71
    assert parse_height_inches("74") == 74
    assert parse_height_inches("unknown") is None


def test_parse_weight_lbs() -> None:
    assert parse_weight_lbs("205 lbs") == 205
    assert parse_weight_lbs("180") == 180
    assert parse_weight_lbs("n/a") is None


def test_parse_bats_throws() -> None:
    assert parse_bats_throws("R/R") == ("R", "R")
    assert parse_bats_throws("S/L") == ("S", "L")
    assert parse_bats_throws(bats="Left", throws="Right") == ("L", "R")


def test_normalize_roster_year() -> None:
    assert normalize_roster_year("Jr.") == "junior"
    assert normalize_roster_year("RS Fr") == "redshirt freshman"
    assert normalize_roster_year("Graduate") == "graduate"


def test_parse_transfer_flag() -> None:
    assert parse_transfer_flag("Yes") is True
    assert parse_transfer_flag("Transfer") is True
    assert parse_transfer_flag("No") is False


def test_parse_hometown() -> None:
    hometown = parse_hometown("Austin, TX")

    assert hometown.city == "Austin"
    assert hometown.state == "TX"
    assert hometown.country is None


def test_split_name() -> None:
    name = split_name("Example, Alex")

    assert name is not None
    assert name.full_name == "Alex Example"
    assert name.first_name == "Alex"
    assert name.last_name == "Example"


def test_normalize_position() -> None:
    position = normalize_position("RHP/INF")

    assert position is not None
    assert position.code == "RHP"
    assert position.group == "pitcher"
