# AGENTS.md - read this first

You are a coding agent working on **ErasmusGPT**, a two-person university project
(Information Retrieval + NLP course). Two humans work on this repo, each with their
own LLM agent. They are called **Person A** and **Person B**.

## Bootstrap protocol (do this every session, in order)

1. Ask (or read from the user's first message) **which person you are: A or B**.
   If it is not stated, ask once and stop. Do not guess. A is the matching engine and
   data; B is the web service and platform.
2. Read `TASKS.md` -> the **Project state** block at the top. It tells you in five lines:
   which stage the project is in, what each person is currently on, and what is blocked.
3. Read `PROGRESS.md` - the top 2-3 entries. That is what actually landed, including
   anything the other person broke or is asking you for.
4. Read `CONTEXT.md` - the project bible. Architecture, contracts, ownership zones.
   Read the stage-relevant file in `docs/` too (each task names one).
5. Go to your stage's section in `TASKS.md`, find **your lane** (`Lane A` or `Lane B`),
   and take the first task that is not `done` and not `blocked`. Task IDs read
   `S<stage>-<lane><n>` - `S3-A2` is stage 3, lane A, task 2.
6. Set that task to `wip` and update the *Project state* block **in the same commit** as
   your first change, so the other agent sees it immediately.
7. Work **only inside your ownership zone** (see CONTEXT.md section Ownership).
8. Before finishing: set the task `done`, tick your lane's gate if it was your last task in
   the stage, and append a `PROGRESS.md` entry using the template at the bottom of
   that file.

## Reading the stage board

- A stage has **two lanes that run in parallel**. Lane A and lane B never touch the same
  files, so you do not need to wait for the other person to start.
- A stage closes only when **both** lanes pass their gate. Whoever ticks the second half
  moves *Current stage* forward and says so in `PROGRESS.md`.
- **If your lane is done and theirs is not:** pull the next stage's tasks *from your own
  lane*, mark them `early`, and note it. Never "help" by working in their lane - that is
  how you get a merge conflict in a file you do not understand.
- **If you are blocked by the other lane:** set your task to `blocked`, write a
  `### Request to A|B` bullet in your PROGRESS entry, and move to the next task in your
  own lane. Do not idle and do not work around it by duplicating their code.
- The contract in `backend/app/schemas/` and `matching/interface.py` is frozen precisely
  so that "blocked by the other lane" is almost never true. Build against the contract.

## Hard rules

- **Never edit files owned by the other person.** If you need a change there, add a
  `### Request to <A|B>` bullet in your PROGRESS.md entry and work around it locally.
- **The API contract is frozen.** `backend/app/schemas/*.py`, `backend/app/matching/interface.py`
  and `docs/04-api-contract.md` are *shared*. Changing them requires a `CONTRACT CHANGE`
  block in PROGRESS.md explaining what broke and why, plus an update to all three.
- **No new heavyweight dependencies** without recording an ADR in `docs/adr/`.
- **Nothing baked into the image larger than ~200 MB, and under 400 MB in total.** The
  demo must run on CPU inside Docker. Bigger models are allowed in `notebooks/` on Colab
  and never ship. See `docs/02-models.md`.
- **Models are baked into the Docker image at build time** and the runtime is offline
  (`HF_HUB_OFFLINE=1`). Never add code that downloads a model at request time.
- Keep commits small and scoped. Commit message prefix: `[A]` or `[B]`. Run
  `git pull --rebase` before pushing. A conflict in `PROGRESS.md` or `TASKS.md` is
  resolved by keeping **both** sides, never by dropping the other person's entry.
- Write English in code, comments, docs and commit messages.
- **Follow the writing style in `CONTEXT.md` section 11.** ASCII only (no em dashes, no
  curly quotes, no emoji, no box-drawing characters), no LLM filler vocabulary, no
  negation-then-reveal sentences. Run `python scripts/check_style.py` before you commit; CI runs it
  too and a failure blocks the build. This applies to PROGRESS entries and commit
  messages as much as to docs.

## Where things are

| Path | What |
|---|---|
| `CONTEXT.md` | Project bible: problem, architecture, contracts, ownership |
| `PROGRESS.md` | Append-only log of what each person did, per commit |
| `TASKS.md` | Staged board: project state, stage ladder, per-stage lane A / lane B tasks |
| `docs/00-map.md` | The picture: request path, ownership boundary, stage graph |
| `docs/` | Universities, model choices, data schema, API contract, evaluation protocol |
| `backend/` | FastAPI service + matching pipeline |
| `frontend/` | React + Vite UI |
| `data/` | Curriculum JSON files and the gold-standard evaluation set |
| `scripts/check_style.py` | Writing-style check (CONTEXT.md section 11), also run in CI |
| `eval/` | Offline evaluation harness (the "measurable improvement" part of the grade) |
| `tools/` | `annotate.html`, the gold-set annotator. Not part of the application |

## Definition of done for any task

- Code runs via `docker compose up --build` with no network access to huggingface.co.
- `python scripts/check_style.py` passes.
- `pytest backend/tests` passes.
- Docs updated if behaviour changed.
- The task is `done` in `TASKS.md` and the *Project state* block is current.
- PROGRESS.md entry appended, naming the stage.
