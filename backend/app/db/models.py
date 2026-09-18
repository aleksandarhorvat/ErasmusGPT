"""ORM models. Owner: Person B. Stage 2, task S2-B3 - extend as needed."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IngestedProgramme(Base):
    __tablename__ = "ingested_programmes"

    programme_id: Mapped[str] = mapped_column(String, primary_key=True)
    institution_id: Mapped[str] = mapped_column(String, index=True)
    course_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String, default="")
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
