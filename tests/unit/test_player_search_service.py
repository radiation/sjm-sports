from __future__ import annotations

from app.schemas.players import PlayerSearchFilters, PlayerSearchResult
from app.services.players import PlayerSearchService


class FakeRosterRepository:
    def __init__(self) -> None:
        self.seen_limit: int | None = None
        self.seen_offset: int | None = None
        self.seen_filters: PlayerSearchFilters | None = None

    def count_search_results(self, filters: PlayerSearchFilters) -> int:
        self.seen_filters = filters
        return 125

    def search(
        self, filters: PlayerSearchFilters, limit: int, offset: int
    ) -> list[PlayerSearchResult]:
        self.seen_filters = filters
        self.seen_limit = limit
        self.seen_offset = offset
        return [
            PlayerSearchResult(
                player_name="Alex Example",
                college="Example State",
                year=2025,
                position="RHP",
            )
        ]


def test_player_search_service_paginates_and_normalizes_filters() -> None:
    repository = FakeRosterRepository()
    service = PlayerSearchService(rosters=repository)  # type: ignore[arg-type]

    page = service.search(
        PlayerSearchFilters(year=2025, college=" Example ", roster_year="Jr", is_transfer=True),
        page=2,
        page_size=500,
    )

    assert page.page == 2
    assert page.page_size == 100
    assert page.total_pages == 2
    assert page.has_previous is True
    assert page.has_next is False
    assert repository.seen_limit == 100
    assert repository.seen_offset == 100
    assert repository.seen_filters is not None
    assert repository.seen_filters.college == "Example"
    assert repository.seen_filters.roster_year == "junior"
    assert page.active_filters["is_transfer"] == "true"
