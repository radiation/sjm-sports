from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from app.schemas.school_sources import SchoolSourceRow
from app.utils.roster_normalization import clean_text


@dataclass(frozen=True)
class VendorClassification:
    vendor: str
    is_sidearm: bool
    note: str


def normalize_school_id(value: object) -> str | None:
    text = clean_text(value)
    return text.upper() if text else None


def normalize_ipeds_id(value: object) -> str | None:
    text = clean_text(value)
    return text if text else None


def normalize_public_private(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    key = text.casefold()
    if key == "public":
        return "Public"
    if key == "private":
        return "Private"
    return text


def detect_roster_vendor_from_url(url: object) -> VendorClassification:
    text = clean_text(url)
    if text is None:
        return VendorClassification(vendor="unknown", is_sidearm=False, note="no roster url")

    parsed = urlparse(text)
    host = parsed.netloc.casefold()
    path = parsed.path.casefold()
    query = parsed.query.casefold()

    if "sidearm" in host or "sidearm" in path:
        return VendorClassification(vendor="sidearm", is_sidearm=True, note="sidearm host or path")

    if "roster.aspx" in path and "path=baseball" in query:
        return VendorClassification(vendor="sidearm", is_sidearm=True, note="sidearm roster.aspx")

    if re.fullmatch(r"/sports/baseball/roster/?", path):
        return VendorClassification(vendor="sidearm", is_sidearm=True, note="sidearm roster path")

    if "presto" in host or "prestosports" in host or "prestosports" in text.casefold():
        return VendorClassification(vendor="presto", is_sidearm=False, note="presto url pattern")

    return VendorClassification(vendor="unknown", is_sidearm=False, note="no known url marker")


def classify_roster_vendor_from_url(url: object) -> tuple[str, bool]:
    classification = detect_roster_vendor_from_url(url)
    return classification.vendor, classification.is_sidearm


def detect_roster_vendor_from_html(html: object) -> VendorClassification:
    text = clean_text(html)
    if text is None:
        return VendorClassification(
            vendor="unknown", is_sidearm=False, note="no known vendor marker"
        )

    soup = BeautifulSoup(text, "lxml")
    visible_text = soup.get_text(" ", strip=True).casefold()

    for link in soup.find_all("a", href=True):
        href = clean_text(link.get("href"))
        if href is None:
            continue
        href_key = href.casefold()
        link_text = clean_text(link.get_text(" ", strip=True))
        link_text_key = link_text.casefold() if link_text else ""

        if "sidearmsports.com" in href_key:
            if any(
                marker in link_text_key
                for marker in ("terms of service", "privacy policy", "accessibility")
            ):
                return VendorClassification(
                    vendor="sidearm", is_sidearm=True, note="sidearm footer link"
                )
            return VendorClassification(vendor="sidearm", is_sidearm=True, note="sidearm link")

        if "prestosports.com" in href_key:
            return VendorClassification(vendor="presto", is_sidearm=False, note="presto link")

    if "powered by sidearm" in visible_text:
        return VendorClassification(
            vendor="sidearm", is_sidearm=True, note="sidearm powered by text"
        )

    if "sidearm sports" in visible_text:
        return VendorClassification(vendor="sidearm", is_sidearm=True, note="sidearm visible text")

    if "prestosports" in visible_text or "presto sports" in visible_text:
        return VendorClassification(vendor="presto", is_sidearm=False, note="presto visible text")

    for image in soup.find_all("img", alt=True):
        alt = clean_text(image.get("alt"))
        if alt is None:
            continue
        alt_key = alt.casefold()
        if "sidearm sports" in alt_key or "sidearm" in alt_key:
            return VendorClassification(vendor="sidearm", is_sidearm=True, note="sidearm image alt")

    return VendorClassification(vendor="unknown", is_sidearm=False, note="no known vendor marker")


def classify_roster_vendor_from_html(html: object) -> tuple[str, bool]:
    classification = detect_roster_vendor_from_html(html)
    return classification.vendor, classification.is_sidearm


def detect_roster_vendor(url: object, html: object | None = None) -> VendorClassification:
    if html is not None:
        return detect_roster_vendor_from_html(html)
    return detect_roster_vendor_from_url(url)


def classify_roster_vendor(url: object, html: object | None = None) -> tuple[str, bool]:
    classification = detect_roster_vendor(url, html)
    return classification.vendor, classification.is_sidearm


def merge_school_source_note(existing_note: object, new_note: str) -> str:
    existing_text = clean_text(existing_note)
    if existing_text is None or existing_text == new_note:
        return new_note
    return f"{existing_text}; {new_note}"


def normalize_school_source_row(row: SchoolSourceRow) -> SchoolSourceRow:
    roster_url = clean_text(row.roster_url)
    roster_vendor, is_sidearm = classify_roster_vendor_from_url(roster_url)
    return SchoolSourceRow(
        school_id=normalize_school_id(row.school_id) or row.school_id,
        ipeds_id=normalize_ipeds_id(row.ipeds_id),
        school_name=clean_text(row.school_name) or row.school_name,
        city=clean_text(row.city),
        state=clean_text(row.state),
        public_private=normalize_public_private(row.public_private),
        division=clean_text(row.division),
        conference=clean_text(row.conference),
        roster_url=roster_url,
        roster_vendor=roster_vendor,
        is_sidearm=is_sidearm,
        import_enabled=roster_url is not None,
        notes=clean_text(row.notes),
    )


def school_sort_key(row: SchoolSourceRow) -> tuple[int, str]:
    match = re.fullmatch(r"[A-Za-z]+(\d+)", row.school_id)
    if match:
        return int(match.group(1)), row.school_id
    return 10**9, row.school_id
