from __future__ import annotations

from app.services.dashboard import DashboardService


class FakeCollegeRepository:
    def count_all(self) -> int:
        return 286


class FakePlayerRepository:
    def count_all(self) -> int:
        return 10919


class FakeRosterRepository:
    def count_all(self) -> int:
        return 10919

    def count_transfers(self) -> int:
        return 1200

    def list_distinct_years(self) -> list[int]:
        return [2025]


def test_dashboard_service_returns_summary() -> None:
    service = DashboardService(
        colleges=FakeCollegeRepository(),  # type: ignore[arg-type]
        players=FakePlayerRepository(),  # type: ignore[arg-type]
        rosters=FakeRosterRepository(),  # type: ignore[arg-type]
    )

    summary = service.get_summary()

    assert summary.total_colleges == 286
    assert summary.total_players == 10919
    assert summary.total_roster_records == 10919
    assert summary.total_transfers == 1200
    assert summary.available_years == [2025]
