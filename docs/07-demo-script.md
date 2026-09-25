# Demo script and offline rehearsal

Owner: Person B (task `S7-AB2`, shared with A for the narration). The deck's "Live demo"
slide points here.

The demo runs on one laptop with the network cable out. Everything below has been set up
so that is possible: the models are in the image, `HF_HUB_OFFLINE=1` is set, and the
embedding cache is on disk. The rehearsal exists to prove it on the machine we will
actually use, not on a CI runner.

## The evening before

Do these with the network **on**.

1. `git pull`, then check `.env` has `MATCHER_IMPL=real` and `BAKE_MODELS=1`.
2. `docker compose up --build -d`. The first build takes about 5 minutes (see README).
3. Wait until the app answers, then run `python scripts/rehearse_demo.py --allow-network`
   once. This also warms `data/.cache/`, so the boot in the room reads the cache instead
   of encoding every course.
4. `docker compose down`.

## The rehearsal

Now with the network **off**: cable out, Wi-Fi off.

1. `python scripts/rehearse_demo.py --start`. It runs `docker compose up -d` (no
   `--build`), times the boot, walks every step of the demo against the API through
   nginx, and checks that huggingface.co is unreachable. Every line should read `ok` and
   the last line should say offline as intended.
2. Open <http://localhost:8080> and click through the demo below by hand, with a
   stopwatch. The target is 4 minutes.
3. Take the fallback screenshots listed at the end while you go.
4. Write the boot time and the two match times into the README's timing paragraph.

To measure a **cold** first boot, the case the healthcheck's 5 minutes are for, rename
`data/.cache` to `data/.cache-off` before step 1 and rename it back afterwards. Nobody
should see a cold boot in the room, but the number belongs in the README.

## The demo, 4 minutes

B drives, A narrates the matches.

| # | Do | Say | Should see |
|---|---|---|---|
| 1 | Show the terminal with `docker compose up` running and the cable visibly out | "Everything runs on this laptop. The models are inside the image." | footer: matcher real, models loaded |
| 2 | My curriculum: UNS PMF Informatics. Host curriculum: Twente TCS. Strategy: Hybrid. My study path: Computer Science. **Match courses** | "Fifty courses, both catalogues, BM25 and a bi-encoder fused by rank." | table in well under a second |
| 3 | Scroll to **Computer networks**, open **why** on the top match | "This is the sentence pair that drove the score." | evidence, two sentences |
| 4 | Point at the recognition panel above the table | "About this many of the 180 ECTS would likely carry over. The probabilities are calibrated, and the panel says they are provisional until the labels are checked." | ECTS estimate, likely and borderline bands, provisional note |
| 5 | On one row, **compare** against Hybrid + cross-encoder | "The reranker we promised. Fused as one opinion among three it is level with hybrid and about 400 times slower, so it is not the default." | the two columns side by side |
| 6 | **how well does this work?** | "Every number here is only as good as the labels. The page counts how many of the 1142 pairs a human has checked." | gold progress, the reports, the provisional warning |

If a step fails, do not debug in front of the examiners. Say what should have happened
and switch to the screenshots.

## Fallback screenshots

Save them as PNG in `docs/screenshots/` during the rehearsal, one per demo step:

1. `1-health.png`: the page footer, matcher real and models loaded.
2. `2-matches.png`: the results table for UNS PMF Informatics against Twente TCS.
3. `3-evidence.png`: Computer networks with **why** open.
4. `4-recognition.png`: the recognition panel.
5. `5-compare.png`: one row compared against Hybrid + cross-encoder.
6. `6-evaluation.png`: the evaluation page.
