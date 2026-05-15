from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class ScrapedPageRecord(BaseModel):
    url: HttpUrl
    page_type: str
    status_code: int | None = None
    content_hash: str | None = None
    error_message: str | None = None
