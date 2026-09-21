"""ORM models. Owner: Person B. Task S2-B3.

The curriculum JSON files are the source of truth (ADR-0002). This table is a record of
what the running container has already seen, keyed by a hash of the file, so a restart
can tell "the same data as last time" from "somebody edited a curriculum". Person A's
embedding cache keys off the same hash, which is why it lives somewhere durable rather
than in memory.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class IngestedProgramme(Base):
    __tablename__ = "ingested_programmes"

    programme_id: Mapped[str] = mapped_column(String, primary_key=True)
    institution_id: Mapped[str] = mapped_column(String, index=True)
    programme_name: Mapped[str] = mapped_column(String, default="")
    course_count: Mapped[int] = mapped_column(Integer, default=0)
    total_ects: Mapped[float] = mapped_column(Float, default=0.0)
    content_hash: Mapped[str] = mapped_column(String, default="")
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
