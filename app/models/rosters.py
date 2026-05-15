from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.people import Coach, Player
from app.models.positions import Position
from app.models.schools import College, HighSchool


class PlayerRoster(TimestampMixin, Base):
    __tablename__ = "player_rosters"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "college_id", "year", name="uq_player_rosters_player_college_year"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    roster_year: Mapped[str | None] = mapped_column(String(50), index=True)
    normalized_roster_year: Mapped[str | None] = mapped_column(String(50), index=True)
    primary_position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), index=True)
    positions_raw: Mapped[str | None] = mapped_column(String(100))
    high_school_id: Mapped[int | None] = mapped_column(ForeignKey("high_schools.id"), index=True)
    previous_college_id: Mapped[int | None] = mapped_column(ForeignKey("colleges.id"), index=True)
    previous_school_raw: Mapped[str | None] = mapped_column(String(200))
    is_transfer: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", index=True
    )
    jersey_number: Mapped[str | None] = mapped_column(String(20))
    roster_url: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(Text)

    player: Mapped[Player] = relationship()
    college: Mapped[College] = relationship(foreign_keys=[college_id])
    primary_position: Mapped[Position | None] = relationship()
    high_school: Mapped[HighSchool | None] = relationship()
    previous_college: Mapped[College | None] = relationship(foreign_keys=[previous_college_id])


class CoachAssignment(TimestampMixin, Base):
    __tablename__ = "coach_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id"), index=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), index=True)
    title_raw: Mapped[str | None] = mapped_column(String(200))
    bio_url: Mapped[str | None] = mapped_column(Text)
    staff_url: Mapped[str | None] = mapped_column(Text)

    coach: Mapped[Coach] = relationship()
    college: Mapped[College] = relationship()
    position: Mapped[Position | None] = relationship()
