# ADR-0001 - English-only pipeline

**Status:** accepted - 2026-09-18

## Context
UNS PMF publishes its Informatics programme in English as well as Serbian. Partner
catalogues are available in English. A multilingual pipeline would need
`paraphrase-multilingual-*` or `bge-m3`, both larger and weaker per parameter on
English, plus a language-detection step and cross-lingual evaluation.

## Decision
Both sides of every comparison are English text. Only English models are used.

## Consequences
- Smaller, faster models; the whole thing fits in a CPU Docker image.
- Evaluation is simpler: no cross-lingual confound.
- Cost: a partner without English descriptions cannot be added without reopening this.
  Record it as future work rather than half-supporting it.
