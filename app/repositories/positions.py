from __future__ import annotations

from sqlalchemy import select

from app.models.positions import Position
from app.repositories.base import Repository


class PositionRepository(Repository[Position]):
    def get(self, position_id: int) -> Position | None:
        return self.session.get(Position, position_id)

    def add(self, position: Position) -> Position:
        self.session.add(position)
        return position

    def get_by_code_and_type(self, code: str, position_type: str) -> Position | None:
        return self.session.scalar(
            select(Position).where(Position.code == code, Position.position_type == position_type)
        )

    def get_or_create(
        self, code: str, name: str, position_type: str, position_group: str | None
    ) -> tuple[Position, bool]:
        position = self.get_by_code_and_type(code, position_type)
        if position is not None:
            return position, False

        position = Position(
            code=code,
            name=name,
            position_type=position_type,
            position_group=position_group,
        )
        self.session.add(position)
        self.session.flush()
        return position, True
