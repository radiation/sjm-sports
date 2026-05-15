from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class Repository[ModelT]:
    def __init__(self, session: Session) -> None:
        self.session = session
