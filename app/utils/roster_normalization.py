from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NameParts:
    first_name: str | None
    last_name: str | None
    full_name: str


@dataclass(frozen=True)
class HometownParts:
    city: str | None
    state: str | None
    country: str | None


@dataclass(frozen=True)
class PositionParts:
    code: str
    name: str
    group: str


POSITION_ALIASES: dict[str, PositionParts] = {
    "P": PositionParts(code="P", name="Pitcher", group="pitcher"),
    "PITCHER": PositionParts(code="P", name="Pitcher", group="pitcher"),
    "RHP": PositionParts(code="RHP", name="Right-Handed Pitcher", group="pitcher"),
    "RIGHTHANDEDPITCHER": PositionParts(code="RHP", name="Right-Handed Pitcher", group="pitcher"),
    "LHP": PositionParts(code="LHP", name="Left-Handed Pitcher", group="pitcher"),
    "LEFTHANDEDPITCHER": PositionParts(code="LHP", name="Left-Handed Pitcher", group="pitcher"),
    "C": PositionParts(code="C", name="Catcher", group="catcher"),
    "CATCHER": PositionParts(code="C", name="Catcher", group="catcher"),
    "1B": PositionParts(code="1B", name="First Base", group="infield"),
    "FIRSTBASE": PositionParts(code="1B", name="First Base", group="infield"),
    "2B": PositionParts(code="2B", name="Second Base", group="infield"),
    "SECONDBASE": PositionParts(code="2B", name="Second Base", group="infield"),
    "3B": PositionParts(code="3B", name="Third Base", group="infield"),
    "THIRDBASE": PositionParts(code="3B", name="Third Base", group="infield"),
    "SS": PositionParts(code="SS", name="Shortstop", group="infield"),
    "SHORTSTOP": PositionParts(code="SS", name="Shortstop", group="infield"),
    "INF": PositionParts(code="INF", name="Infielder", group="infield"),
    "INFIELD": PositionParts(code="INF", name="Infielder", group="infield"),
    "INFIELDER": PositionParts(code="INF", name="Infielder", group="infield"),
    "OF": PositionParts(code="OF", name="Outfielder", group="outfield"),
    "OUTFIELD": PositionParts(code="OF", name="Outfielder", group="outfield"),
    "OUTFIELDER": PositionParts(code="OF", name="Outfielder", group="outfield"),
    "DH": PositionParts(code="DH", name="Designated Hitter", group="hitter"),
    "DESIGNATEDHITTER": PositionParts(code="DH", name="Designated Hitter", group="hitter"),
    "UTIL": PositionParts(code="UTIL", name="Utility", group="utility"),
    "UTL": PositionParts(code="UTIL", name="Utility", group="utility"),
    "UTILITY": PositionParts(code="UTIL", name="Utility", group="utility"),
}


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def normalize_key(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    return text.casefold()


def parse_height_inches(value: object) -> int | None:
    text = clean_text(value)
    if text is None:
        return None

    if text.isdigit():
        inches = int(text)
        return inches if 48 <= inches <= 96 else None

    numbers = [int(part) for part in re.findall(r"\d+", text)]
    if len(numbers) < 2:
        return None

    feet = numbers[0]
    inches = numbers[1]
    if 4 <= feet <= 7 and 0 <= inches <= 11:
        return feet * 12 + inches
    return None


def parse_weight_lbs(value: object) -> int | None:
    text = clean_text(value)
    if text is None:
        return None

    match = re.search(r"\d+", text)
    if match is None:
        return None
    pounds = int(match.group(0))
    return pounds if 80 <= pounds <= 350 else None


def normalize_hand(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    key = text.casefold()
    if key in {"r", "right", "rh"}:
        return "R"
    if key in {"l", "left", "lh"}:
        return "L"
    if key in {"s", "switch"}:
        return "S"
    return None


def parse_bats_throws(
    bats_throws: object = None, bats: object = None, throws: object = None
) -> tuple[str | None, str | None]:
    normalized_bats = normalize_hand(bats)
    normalized_throws = normalize_hand(throws)
    if normalized_bats or normalized_throws:
        return normalized_bats, normalized_throws

    text = clean_text(bats_throws)
    if text is None:
        return None, None

    parts = [part for part in re.split(r"[/\\|-]", text) if clean_text(part)]
    if len(parts) >= 2:
        return normalize_hand(parts[0]), normalize_hand(parts[1])
    return None, None


def normalize_roster_year(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    key = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    compact_key = key.replace(" ", "")
    is_redshirt = "redshirt" in key or compact_key.startswith("rs")
    base_key = compact_key.removeprefix("rs") if is_redshirt else compact_key

    if base_key in {"fr", "freshman", "frosh", "1", "1st", "firstyear"} or "freshman" in key:
        base_year = "freshman"
    elif base_key in {"so", "soph", "sophomore", "2", "2nd"} or "sophomore" in key:
        base_year = "sophomore"
    elif base_key in {"jr", "junior", "3", "3rd"} or "junior" in key:
        base_year = "junior"
    elif base_key in {"sr", "senior", "4", "4th"} or "senior" in key:
        base_year = "senior"
    elif base_key in {"gr", "grad", "graduate", "5", "5th"} or "graduate" in key:
        base_year = "graduate"
    else:
        return text.casefold()

    if is_redshirt and base_year != "graduate":
        return f"redshirt {base_year}"
    return base_year


def parse_transfer_flag(value: object) -> bool:
    text = clean_text(value)
    if text is None:
        return False
    return text.casefold() in {"1", "true", "t", "yes", "y", "transfer", "transferred", "portal"}


def parse_hometown(value: object) -> HometownParts:
    text = clean_text(value)
    if text is None:
        return HometownParts(city=None, state=None, country=None)

    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) >= 3:
        return HometownParts(city=parts[0], state=parts[1], country=parts[2])
    if len(parts) == 2:
        return HometownParts(city=parts[0], state=parts[1], country=None)
    return HometownParts(city=text, state=None, country=None)


def split_name(
    full_name: object, first_name: object = None, last_name: object = None
) -> NameParts | None:
    explicit_first_name = clean_text(first_name)
    explicit_last_name = clean_text(last_name)
    cleaned_full_name = clean_text(full_name)

    if cleaned_full_name is None and (explicit_first_name or explicit_last_name):
        cleaned_full_name = " ".join(
            part for part in [explicit_first_name, explicit_last_name] if part is not None
        )
    if cleaned_full_name is None:
        return None

    if explicit_first_name or explicit_last_name:
        return NameParts(
            first_name=explicit_first_name,
            last_name=explicit_last_name,
            full_name=cleaned_full_name,
        )

    if "," in cleaned_full_name:
        last_part, first_part = [part.strip() for part in cleaned_full_name.split(",", 1)]
        full_name_for_storage = f"{first_part} {last_part}".strip()
        return NameParts(
            first_name=first_part or None,
            last_name=last_part or None,
            full_name=full_name_for_storage,
        )

    name_parts = cleaned_full_name.split()
    if len(name_parts) == 1:
        return NameParts(first_name=None, last_name=name_parts[0], full_name=cleaned_full_name)
    return NameParts(
        first_name=name_parts[0], last_name=" ".join(name_parts[1:]), full_name=cleaned_full_name
    )


def normalize_position(value: object) -> PositionParts | None:
    text = clean_text(value)
    if text is None:
        return None

    for raw_token in re.split(r"[/,;|]", text):
        token = clean_text(raw_token)
        if token is None:
            continue
        compact_token = re.sub(r"[^A-Za-z0-9]+", "", token).upper()
        position = POSITION_ALIASES.get(compact_token)
        if position is not None:
            return position
    return None
