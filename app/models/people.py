from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Person(TimestampMixin, Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(200), index=True)

    player: Mapped[Player | None] = relationship(back_populates="person")
    coach: Mapped[Coach | None] = relationship(back_populates="person")


class Player(TimestampMixin, Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), unique=True, index=True)
    bats: Mapped[str | None] = mapped_column(String(10))
    throws: Mapped[str | None] = mapped_column(String(10))
    height_inches: Mapped[int | None]
    weight_lbs: Mapped[int | None]
    hometown_city: Mapped[str | None] = mapped_column(String(100))
    hometown_state: Mapped[str | None] = mapped_column(String(100), index=True)
    hometown_country: Mapped[str | None] = mapped_column(String(100))

    person: Mapped[Person] = relationship(back_populates="player")


class Coach(TimestampMixin, Base):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), unique=True, index=True)

    person: Mapped[Person] = relationship(back_populates="coach")
