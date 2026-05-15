from __future__ import annotations


class HomeService:
    def get_home_context(self) -> dict[str, str]:
        return {"page_title": "SJM Sports Recruiting Portal"}


def get_home_service() -> HomeService:
    return HomeService()
