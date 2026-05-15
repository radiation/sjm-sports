from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.dashboard import DashboardSummary
from app.schemas.players import PlayerSearchFilters, PlayerSearchPage, PlayerSearchResult
from app.web.routes.home import get_dashboard_service
from app.web.routes.players import get_player_search_service


def test_health_route() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page_renders() -> None:
    app = create_app()
    app.dependency_overrides[get_dashboard_service] = lambda: FakeDashboardService()
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "SJM Sports Recruiting Portal" in response.text
    assert "Colleges" in response.text


def test_players_page_renders() -> None:
    app = create_app()
    app.dependency_overrides[get_player_search_service] = lambda: FakePlayerSearchService()
    client = TestClient(app)

    response = client.get("/players?year=2025&college=Example")

    assert response.status_code == 200
    assert "Alex Example" in response.text
    assert "Example State" in response.text


class FakeDashboardService:
    def get_summary(self) -> DashboardSummary:
        return DashboardSummary(
            total_colleges=1,
            total_players=2,
            total_roster_records=2,
            total_transfers=1,
            available_years=[2025],
        )


class FakePlayerSearchService:
    def search(
        self, filters: PlayerSearchFilters, page: int = 1, page_size: int = 50
    ) -> PlayerSearchPage:
        return PlayerSearchPage(
            filters=filters,
            results=[
                PlayerSearchResult(
                    player_name="Alex Example",
                    college="Example State",
                    conference="Example League",
                    year=2025,
                    position="RHP",
                    normalized_roster_year="junior",
                    height_inches=74,
                    weight_lbs=205,
                    bats="R",
                    throws="R",
                    hometown_city="Austin",
                    hometown_state="TX",
                    high_school="Example High",
                    is_transfer=False,
                )
            ],
            total_results=1,
            page=page,
            page_size=page_size,
            total_pages=1,
            active_filters={"year": "2025"},
        )
