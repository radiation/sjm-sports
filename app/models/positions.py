from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Position(TimestampMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        CheckConstraint("position_type in ('player', 'coach')", name="valid_position_type"),
        UniqueConstraint("code", "position_type", name="uq_positions_code_position_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100), index=True)
    position_type: Mapped[str] = mapped_column(String(20), index=True)
    position_group: Mapped[str | None] = mapped_column(String(50), index=True)
