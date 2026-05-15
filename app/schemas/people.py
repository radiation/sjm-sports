from __future__ import annotations

from pydantic import BaseModel


class PersonCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str


class PersonRead(PersonCreate):
    id: int
