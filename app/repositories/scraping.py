from __future__ import annotations

from app.models.scraping import ScrapePage, ScrapeRun
from app.repositories.base import Repository


class ScrapeRunRepository(Repository[ScrapeRun]):
    def get(self, scrape_run_id: int) -> ScrapeRun | None:
        return self.session.get(ScrapeRun, scrape_run_id)

    def add(self, scrape_run: ScrapeRun) -> ScrapeRun:
        self.session.add(scrape_run)
        return scrape_run


class ScrapePageRepository(Repository[ScrapePage]):
    def get(self, scrape_page_id: int) -> ScrapePage | None:
        return self.session.get(ScrapePage, scrape_page_id)

    def add(self, scrape_page: ScrapePage) -> ScrapePage:
        self.session.add(scrape_page)
        return scrape_page
