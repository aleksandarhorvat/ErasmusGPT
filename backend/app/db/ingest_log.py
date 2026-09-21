"""Record which curricula this container has seen. Owner: Person B. Task S2-B3.

Called once at startup. Never in a request path, and never a reason to fail the boot:
if the database is unwritable the app still serves, because the JSON files are the
source of truth and this table is bookkeeping.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import IngestedProgramme
from app.db.session import Base

log = logging.getLogger(__name__)


def content_hash(path: Path) -> str:
    """Hash the courses, not the file, so a re-scrape that only moves `scraped_at` is
    recognised as the same data."""
    data = json.loads(path.read_text(encoding="utf-8"))
    payload = json.dumps(data.get("courses", []), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def record_curricula(settings: Settings) -> dict[str, str]:
    """Upsert one row per curriculum file. Returns programme_id -> "new" | "changed" | "same"."""
    outcome: dict[str, str] = {}
    try:
        # Build the engine from the settings we were handed rather than the module-level
        # one, so the argument is not a lie and a test can point this at its own file.
        engine = create_engine(
            settings.database_url, connect_args={"check_same_thread": False}, future=True
        )
        Base.metadata.create_all(engine)
        with sessionmaker(bind=engine, expire_on_commit=False)() as session:
            for path in sorted(settings.curricula_dir.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                digest = content_hash(path)
                row = session.get(IngestedProgramme, data["programme_id"])
                if row is None:
                    session.add(IngestedProgramme(
                        programme_id=data["programme_id"],
                        institution_id=data["institution_id"],
                        programme_name=data.get("programme_name", ""),
                        course_count=len(data.get("courses", [])),
                        total_ects=float(data.get("total_ects") or 0.0),
                        content_hash=digest,
                    ))
                    outcome[data["programme_id"]] = "new"
                elif row.content_hash != digest:
                    row.content_hash = digest
                    row.course_count = len(data.get("courses", []))
                    row.total_ects = float(data.get("total_ects") or 0.0)
                    outcome[data["programme_id"]] = "changed"
                else:
                    outcome[data["programme_id"]] = "same"
            session.commit()
    except Exception:  # noqa: BLE001 - bookkeeping must never stop the app booting
        log.exception("could not record ingested curricula; continuing without it")
        return {}
    changed = [k for k, v in outcome.items() if v != "same"]
    log.info("curricula recorded: %d total, %d new or changed %s",
             len(outcome), len(changed), changed or "")
    return outcome
