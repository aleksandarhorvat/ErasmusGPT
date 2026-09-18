# notebooks/

Owner: **Person A**. Colab-only work - the things that need a GPU and therefore cannot
live in the CPU Docker image (see `docs/02-models.md`).

- `01_model_sweep.ipynb` - all strategies x bi-encoders x rerankers on a T4, including
  `gte-modernbert-base` and `mxbai-rerank-base-v2`. Exports a CSV into `eval/report/`.
- `02_finetune_biencoder.ipynb` - S6-A3, `MultipleNegativesRankingLoss` on the gold set.

Rules: mount the repo (or `git clone` it), import `backend/app/matching` rather than
copy-pasting logic, and commit the resulting CSV/Markdown - not the notebook outputs.
