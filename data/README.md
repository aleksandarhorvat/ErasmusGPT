# data/

- `curricula/*.json` - one study programme per file. Schema: `docs/03-data-schema.md`.
  **Source of truth.** Committed to git. Never scraped at request time.
- `gold/gold_pairs.csv` - the labelled evaluation set. Schema and labelling rules:
  `docs/03-data-schema.md` section Gold set. Protocol: `docs/05-evaluation.md`.
- `.cache/` - generated embedding caches (`*.npy`). Git-ignored, safe to delete.

The two curriculum files currently here are **sample placeholders** so the stub matcher
has something to return. Person A replaces them with real scraped data in S1-A1 / S1-A2.
