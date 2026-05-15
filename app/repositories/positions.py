from __future__ import annotations

from app.models.positions import Position
from app.repositories.base import Repository


class PositionRepository(Repository[Position]):
    def get(self, position_id: int) -> Position | None:
        return self.session.get(Position, position_id)

    def add(self, position: Position) -> Position:
        self.session.add(position)
        return position
