# ADR-0004 - ECTS, year and institution are metadata, not embedding input

**Status:** accepted - 2026-09-18

## Context
It is tempting to concatenate everything known about a course into the embedded text.

## Decision
Embed only title, description, learning outcomes and topics. ECTS, year, semester,
mandatory flag and institution name are returned as metadata and used for display,
the confidence band and optional post-filters.

## Consequences
- Numbers and institution names are strong lexical distractors: two unrelated 6-ECTS
  courses should not be pulled together because both say "6 ECTS".
- ECTS difference stays available as an independent, interpretable signal, which is
  what an academic coordinator reasons about anyway.
- Revisit only with an ablation showing it helps.
