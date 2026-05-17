from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class College(TimestampMixin, Base):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100), index=True)
    public_private: Mapped[str | None] = mapped_column(String(50))
    division: Mapped[str | None] = mapped_column(String(50), index=True)
    conference: Mapped[str | None] = mapped_column(String(100), index=True)
    ncaa_school_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    ipeds_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    roster_url: Mapped[str | None] = mapped_column(Text)
    roster_vendor: Mapped[str | None] = mapped_column(String(50), index=True)
    is_sidearm: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="false")
    import_enabled: Mapped[bool] = mapped_column(
        default=False, nullable=False, server_default="false", index=True
    )
    source_notes: Mapped[str | None] = mapped_column(Text)
    staff_url: Mapped[str | None] = mapped_column(Text)


class HighSchool(TimestampMixin, Base):
    __tablename__ = "high_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100), index=True)
    country: Mapped[str | None] = mapped_column(String(100))
