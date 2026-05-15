from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerSearchFilters(BaseModel):
    year: int | None = None
    college: str | None = None
    conference: str | None = None
    position: str | None = None
    roster_year: str | None = None
    is_transfer: bool | None = None
    hometown_state: str | None = None


class PlayerSearchResult(BaseModel):
    player_name: str
    college: str
    conference: str | None = None
    year: int
    position: str | None = None
    positions_raw: str | None = None
    roster_year: str | None = None
    normalized_roster_year: str | None = None
    height_inches: int | None = None
    weight_lbs: int | None = None
    bats: str | None = None
    throws: str | None = None
    hometown_city: str | None = None
    hometown_state: str | None = None
    hometown_country: str | None = None
    high_school: str | None = None
    is_transfer: bool = False
    roster_url: str | None = None
    profile_url: str | None = None


class PlayerSearchPage(BaseModel):
    filters: PlayerSearchFilters
    results: list[PlayerSearchResult]
    total_results: int
    page: int
    page_size: int
    total_pages: int
    active_filters: dict[str, str] = Field(default_factory=dict)

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def previous_page(self) -> int:
        return max(1, self.page - 1)

    @property
    def next_page(self) -> int:
        return min(self.total_pages, self.page + 1)
