from __future__ import annotations

from math import ceil

from app.repositories.rosters import PlayerRosterRepository
from app.schemas.players import PlayerSearchFilters, PlayerSearchPage
from app.utils.roster_normalization import clean_text, normalize_roster_year

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class PlayerSearchService:
    def __init__(self, rosters: PlayerRosterRepository) -> None:
        self.rosters = rosters

    def search(
        self,
        filters: PlayerSearchFilters,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PlayerSearchPage:
        normalized_filters = self._normalize_filters(filters)
        safe_page = max(1, page)
        safe_page_size = min(MAX_PAGE_SIZE, max(1, page_size))
        offset = (safe_page - 1) * safe_page_size
        total_results = self.rosters.count_search_results(normalized_filters)
        results = self.rosters.search(normalized_filters, limit=safe_page_size, offset=offset)
        total_pages = max(1, ceil(total_results / safe_page_size))

        return PlayerSearchPage(
            filters=normalized_filters,
            results=results,
            total_results=total_results,
            page=safe_page,
            page_size=safe_page_size,
            total_pages=total_pages,
            active_filters=self._active_filter_params(normalized_filters),
        )

    def _normalize_filters(self, filters: PlayerSearchFilters) -> PlayerSearchFilters:
        return PlayerSearchFilters(
            year=filters.year,
            college=clean_text(filters.college),
            conference=clean_text(filters.conference),
            position=clean_text(filters.position),
            roster_year=normalize_roster_year(filters.roster_year),
            is_transfer=filters.is_transfer,
            hometown_state=clean_text(filters.hometown_state),
        )

    def _active_filter_params(self, filters: PlayerSearchFilters) -> dict[str, str]:
        params: dict[str, str] = {}
        for key, value in filters.model_dump().items():
            if value is None or value == "":
                continue
            if isinstance(value, bool):
                params[key] = "true" if value else "false"
            else:
                params[key] = str(value)
        return params
