# data/

- `curricula/*.json` - one study programme per file. Schema: `docs/03-data-schema.md`.
  **Source of truth.** Committed to git. Never scraped at request time.
- `gold/llm_prelabels.csv` - the model's raw proposed labels. Written once, then frozen.
- `gold/gold_pairs.csv` - the labelled evaluation set, checked and corrected by a human.
  Only `checked=yes` rows count. Label it with `tools/annotate.html`.
- `gold/gold_pairs_b.csv` - Person B's cold slice, for Cohen's kappa.

  Schema for all three: `docs/03-data-schema.md` section Gold set.
  Protocol: `docs/05-evaluation.md`.
- `.cache/` - generated embedding caches (`*.npy`) and scraper downloads
  (`uns-pmf-pdf/`). Git-ignored, safe to delete.

All three curriculum files are real, one scraper each in `backend/scripts/`:

| File | Courses | Source |
|---|---|---|
| `uns-pmf-informatics-bsc.json` | 50 | PMF programme page plus one syllabus PDF per course |
| `utwente-tcs-bsc.json` | 40 | Osiris JSON API, 2025-2026 |
| `epfl-cs-msc.json` | 78 | edu.epfl.ch coursebooks |

`gold/gold_pairs.csv` holds only its header until stage 5 builds the real set.
