# ADR-0002 - SQLite, not Postgres

**Status:** accepted - 2026-09-18

## Context
The dataset is a handful of study programmes, a few hundred courses. The grading
criterion is "someone else can run this with minimal effort".

## Decision
SQLite in a named Docker volume. Two compose services: `backend`, `frontend`.

## Consequences
- `docker compose up --build` and nothing else.
- Curricula are also committed as JSON, so the DB is a cache, not the source of truth -
  deleting the volume loses nothing.
- If user accounts or concurrent writes ever appear, revisit. SQLAlchemy keeps the
  migration cheap.
