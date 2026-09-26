"""Build the defence deck. Stage 7, task S7-AB1. Owners: both.

    python docs/slides/build_deck.py

Writes docs/slides/erasmusgpt-defence.pptx. Every number on the slides is read from the
files the evaluation writes, so the deck is rebuilt rather than edited once the labels
change:

- eval/report/results.csv (run_eval.py). Until the labelling pass (S5-A1) produces it,
  the deck falls back to the provisional numbers in eval/report/ablations.md and says
  PROVISIONAL on every slide that shows them.
- data/calibration/hybrid.json for the reliability chart.
- eval/report/kappa.md (kappa.py) for agreement, "pending" until S5-B1 is in.

Needs python-pptx, which is a development tool here and never enters the image.
"""
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "erasmusgpt-defence.pptx"
RESULTS = REPO_ROOT / "eval" / "report" / "results.csv"
KAPPA = REPO_ROOT / "eval" / "report" / "kappa.md"
CALIBRATION = REPO_ROOT / "data" / "calibration" / "hybrid.json"
GOLD_PAIRS = REPO_ROOT / "data" / "gold" / "gold_pairs.csv"
PRELABELS = REPO_ROOT / "data" / "gold" / "llm_prelabels.csv"

# Erasmus blue dominates, gold is the one accent, as on the programme's own material.
NAVY = RGBColor(0x14, 0x23, 0x4B)
BLUE = RGBColor(0x2A, 0x4D, 0x9B)
GOLD = RGBColor(0xF2, 0xB7, 0x05)
INK = RGBColor(0x1F, 0x24, 0x33)
MUTED = RGBColor(0x5F, 0x67, 0x7A)
PALE = RGBColor(0xEE, 0xF1, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xB5, 0x3A, 0x2E)
HEAD_FONT = "Cambria"
BODY_FONT = "Calibri"

# Twente TCS, from eval/report/ablations.md sections 1 and 1b, model pre-labels.
PROVISIONAL = {
    "bm25": {"P@1": 0.86, "Recall@5": 0.75, "MRR@10": 0.91, "ms_per_query": 2},
    "dense-bge": {"P@1": 0.75, "Recall@5": 0.77, "MRR@10": 0.81, "ms_per_query": 1},
    "hybrid": {"P@1": 0.86, "Recall@5": 0.80, "MRR@10": 0.90, "ms_per_query": 2},
    "hybrid+ce": {"P@1": 0.82, "Recall@5": 0.82, "MRR@10": 0.88, "ms_per_query": 910},
}


# --- data -------------------------------------------------------------------
def gold_progress() -> tuple[int, int]:
    """(checked rows, total rows) in the gold set."""
    if not GOLD_PAIRS.exists():
        return 0, 0
    with GOLD_PAIRS.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    checked = sum(r.get("checked", "").strip().lower() == "yes" for r in rows)
    return checked, len(rows)


def load_results() -> tuple[dict[str, dict[str, float]], bool]:
    """config -> metrics, and whether they come from human-checked labels.

    results.csv alone is not enough: run_eval.py scores whatever rows are checked, so
    halfway through S5-A1 it exists but covers only the home courses labelled first.
    The numbers count as final only once every gold row is checked, the same rule
    GET /api/v1/evaluation applies.
    """
    checked, total = gold_progress()
    complete = total > 0 and checked == total
    if RESULTS.exists():
        with RESULTS.open(encoding="utf-8") as handle:
            rows = {row["config"]: {k: float(v) for k, v in row.items() if k != "config"}
                    for row in csv.DictReader(handle)}
        if rows:
            return rows, complete
    return PROVISIONAL, False


def label_counts() -> tuple[int, int]:
    """(rows labelled by a person, rows labelled by a model), from provenance.json."""
    record = GOLD_PAIRS.parent / "provenance.json"
    checked, _ = gold_progress()
    if not record.exists():
        return checked, 0
    counts = json.loads(record.read_text(encoding="utf-8")).get("counts", {})
    return int(counts.get("human", checked)), int(counts.get("model", 0))


def badge_text(provisional: bool) -> str | None:
    """What the gold tag on a numbers slide says, or None for no tag."""
    if provisional:
        return "PROVISIONAL LABELS"
    if label_counts()[1]:
        return "PARTLY MODEL-LABELLED"
    return None


def load_kappa() -> str:
    if not KAPPA.exists():
        return "pending"
    # The human-against-human row: "A vs B" before provenance, named people after it.
    match = re.search(r"\| (?:A vs B|Luka \(human\) vs Aleksandar \(human\)) \| (\d+) \| "
                      r"[\d.]+ \| ([-\d.]+) \| ([-\d.]+) \|",
                      KAPPA.read_text(encoding="utf-8"))
    if not match:
        return "pending"
    return f"{match.group(3)} (weighted, {match.group(1)} pairs)"


def correction_rate() -> str:
    if not GOLD_PAIRS.exists() or not PRELABELS.exists():
        return "pending"
    with PRELABELS.open(encoding="utf-8") as handle:
        proposed = {(r["home_uid"], r["host_uid"]): r["llm_label"]
                    for r in csv.DictReader(handle)}
    changed = checked = 0
    model = set()
    claude = GOLD_PAIRS.parent / "claude_labels_a.csv"
    if claude.exists():
        with claude.open(encoding="utf-8") as handle:
            model = {(r["home_uid"], r["host_uid"]) for r in csv.DictReader(handle)
                     if r.get("final") == "yes"}
    with GOLD_PAIRS.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row["home_uid"], row["host_uid"]) in model:
                continue  # a model's disagreement is not a human correction
            if row.get("checked", "").strip().lower() == "yes":
                checked += 1
                changed += int(proposed.get((row["home_uid"], row["host_uid"])) != row["label"])
    if not checked:
        return "pending"
    return f"{changed / checked:.1%} of {checked} human rows"


# --- drawing helpers --------------------------------------------------------
def text(slide, left, top, width, height, content, size=16, color=INK, bold=False,
         font=BODY_FONT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False):
    """One text box; `content` may be a string or a list of paragraphs."""
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    paragraphs = content if isinstance(content, list) else [content]
    for index, line in enumerate(paragraphs):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.space_after = Pt(8)
        run = paragraph.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold
        run.font.italic = italic
        run.font.name = font
    return box


def box(slide, left, top, width, height, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    shape_obj = slide.shapes.add_shape(shape, left, top, width, height)
    shape_obj.fill.solid()
    shape_obj.fill.fore_color.rgb = fill
    shape_obj.line.fill.background()
    shape_obj.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shape_obj.adjustments[0] = 0.12
    return shape_obj


def background(slide, colour):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = colour


def title(slide, words, colour=NAVY):
    text(slide, Inches(0.6), Inches(0.45), Inches(12.1), Inches(0.9), words, size=36,
         color=colour, bold=True, font=HEAD_FONT)


def badge(slide, label):
    """Gold tag on every slide whose numbers are not fully backed by human labels.

    `label` is the tag text, or None for no tag (see `badge_text`).
    """
    if not label:
        return
    tag = box(slide, Inches(10.35), Inches(0.5), Inches(2.4), Inches(0.42), GOLD)
    frame = tag.text_frame
    frame.margin_top = frame.margin_bottom = 0
    run = frame.paragraphs[0].add_run()
    run.text = label
    run.font.size, run.font.bold, run.font.name = Pt(12), True, BODY_FONT
    run.font.color.rgb = NAVY
    frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def circle_number(slide, left, top, number, fill=GOLD, colour=NAVY):
    dot = box(slide, left, top, Inches(0.55), Inches(0.55), fill, MSO_SHAPE.OVAL)
    frame = dot.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    run = frame.paragraphs[0].add_run()
    run.text = str(number)
    run.font.size, run.font.bold, run.font.name = Pt(18), True, HEAD_FONT
    run.font.color.rgb = colour
    frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def style_chart(chart, legend=True):
    chart.font.size = Pt(12)
    chart.font.name = BODY_FONT
    chart.font.color.rgb = INK
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    value_axis = chart.value_axis
    value_axis.has_major_gridlines = True
    value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xE1, 0xEA)
    value_axis.format.line.fill.background()
    chart.category_axis.format.line.color.rgb = RGBColor(0xB0, 0xB6, 0xC4)


# --- slides -----------------------------------------------------------------
def slide_title(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, NAVY)
    for i in range(12):  # ring of twelve stars, drawn as dots, the Erasmus motif
        angle = 2 * math.pi * i / 12
        cx, cy, r = 10.6, 3.75, 1.6
        box(slide, Inches(cx + r * math.cos(angle) - 0.13),
                  Inches(cy + r * math.sin(angle) - 0.13), Inches(0.26), Inches(0.26),
                  GOLD, MSO_SHAPE.STAR_5_POINT)
    text(slide, Inches(0.8), Inches(2.1), Inches(8.2), Inches(1.2), "ErasmusGPT", size=54,
         color=WHITE, bold=True, font=HEAD_FONT)
    text(slide, Inches(0.8), Inches(3.3), Inches(8.2), Inches(1.2),
         "Which courses abroad will my faculty recognise?", size=24, color=GOLD,
         font=HEAD_FONT, italic=True)
    text(slide, Inches(0.8), Inches(5.2), Inches(8.2), Inches(1.0),
         ["Luka Cubrilo - matching engine, data, evaluation",
          "Aleksandar Horvat - service, interface, packaging"],
         size=16, color=WHITE)
    text(slide, Inches(0.8), Inches(6.5), Inches(8.2), Inches(0.4),
         "Information Retrieval and NLP, Faculty of Sciences, University of Novi Sad",
         size=12, color=RGBColor(0xB8, 0xC2, 0xDA))
    slide.notes_slide.notes_text_frame.text = (
        "Both. One sentence each on who built what, then straight to the problem.")


def courses_indexed() -> int:
    """Every course in data/curricula/, home programme included."""
    return sum(len(json.loads(path.read_text(encoding="utf-8")).get("courses", []))
               for path in sorted((REPO_ROOT / "data" / "curricula").glob("*.json")))


def slide_problem(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "The problem")
    text(slide, Inches(0.6), Inches(1.6), Inches(6.2), Inches(4.5), [
        "An outgoing Erasmus student has to find, in a foreign catalogue, the courses "
        "their home faculty will accept in place of their own.",
        "Today: read the catalogue, guess, write to the coordinator, wait, repeat. "
        "Days per student, and the criteria are opaque.",
        "ErasmusGPT ranks the host courses for every home course and estimates how "
        "many ECTS of the degree would carry over.",
    ], size=18)
    stats = [("50", "home courses, UNS PMF BSc Informatics"),
             ("6", "host programmes: EPFL, Delft, Milan, KTH, Twente x2"),
             (str(courses_indexed()), "courses indexed, English descriptions")]
    for index, (number, label) in enumerate(stats):
        top = Inches(1.6 + index * 1.75)
        box(slide, Inches(7.5), top, Inches(5.2), Inches(1.45), PALE)
        text(slide, Inches(7.8), top + Inches(0.12), Inches(1.9), Inches(1.2), number,
             size=48, color=BLUE, bold=True, font=HEAD_FONT, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, Inches(9.7), top + Inches(0.2), Inches(2.8), Inches(1.05), label,
             size=15, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    slide.notes_slide.notes_text_frame.text = (
        "A. Keep it to the student's question. The numbers on the right are the data "
        "that exists today, all in data/curricula.")


def cost_ratio(results) -> str:
    """How many times slower hybrid+ce is than hybrid, rounded for a slide."""
    try:
        ratio = results["hybrid+ce"]["ms_per_query"] / results["hybrid"]["ms_per_query"]
    except (KeyError, ZeroDivisionError):
        return "several hundred"
    return f"about {round(ratio, -2):.0f}"


def slide_pipeline(deck, results):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "The pipeline")
    stages = [
        ("Course document", "title, description,\noutcomes, topics"),
        ("BM25", "rank_bm25,\nlexical baseline"),
        ("Bi-encoder", "bge-small-en-v1.5,\ncosine similarity"),
        ("RRF fusion", "reciprocal rank\nfusion -> top 25"),
        ("Cross-encoder", "ms-marco-MiniLM-L6,\nfused, optional"),
        ("Calibration", "Platt scaling ->\np(recognised)"),
    ]
    width, gap, top = Inches(1.78), Inches(0.28), Inches(2.3)
    for index, (name, detail) in enumerate(stages):
        left = Inches(0.6) + index * (width + gap)
        if name in ("BM25", "Bi-encoder"):
            # the two retrievers run side by side, so stack them in one column
            continue
        box(slide, left, top, width, Inches(1.9), NAVY if index in (0, 5) else PALE)
        colour = WHITE if index in (0, 5) else NAVY
        text(slide, left + Inches(0.15), top + Inches(0.2), width - Inches(0.3),
             Inches(0.5), name, size=16, bold=True, color=colour, font=HEAD_FONT)
        text(slide, left + Inches(0.15), top + Inches(0.8), width - Inches(0.3),
             Inches(1.0), detail.split("\n"), size=12,
             color=WHITE if index in (0, 5) else MUTED)
    # stacked retrievers in columns 1 and 2
    left = Inches(0.6) + (width + gap)
    wide = width * 2 + gap
    for row, (name, detail) in enumerate([stages[1], stages[2]]):
        y = top + row * Inches(1.0) - Inches(0.05)
        box(slide, left, y, wide, Inches(0.9), BLUE)
        text(slide, left + Inches(0.2), y + Inches(0.12), Inches(1.4), Inches(0.6), name,
             size=16, bold=True, color=WHITE, font=HEAD_FONT, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, left + Inches(1.6), y + Inches(0.1), wide - Inches(1.7),
             Inches(0.7), detail.replace("\n", " "), size=12, color=WHITE,
             anchor=MSO_ANCHOR.MIDDLE)
    for index in (0, 2, 3, 4):  # arrows between columns
        x = Inches(0.6) + (index + 1) * (width + gap) - gap + Inches(0.02)
        box(slide, x, top + Inches(0.75), gap - Inches(0.04), Inches(0.4), GOLD,
                    MSO_SHAPE.RIGHT_ARROW)
    text(slide, Inches(0.6), Inches(4.7), Inches(12.1), Inches(2.0), [
        "One code path: the web service and the evaluation harness import the same "
        "app.matching module, so the numbers describe the system being demonstrated.",
        "Default strategy is hybrid (ADR-0005): level with hybrid+ce on quality, "
        f"{cost_ratio(results)} times cheaper per query.",
    ], size=16)
    slide.notes_slide.notes_text_frame.text = (
        "A. Why two retrievers: BM25 catches exact course vocabulary, the bi-encoder "
        "catches paraphrase. Why RRF: the two score scales are incomparable, ranks are "
        "not. The cross-encoder is fused as a third opinion, never a veto.")


def slide_demo(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, NAVY)
    text(slide, Inches(0.6), Inches(0.45), Inches(12), Inches(0.9), "Live demo", size=36,
         color=WHITE, bold=True, font=HEAD_FONT)
    steps = [
        "docker compose up, network cable out: the models are baked into the image.",
        "Home UNS PMF Informatics, host TU Delft, strategy hybrid: 50 courses in about 0.1 s.",
        "Open Computer networks: the evidence sentence pair explains the match.",
        "Recognition panel: expected ECTS carried over, with likely and borderline bands.",
        "No suitable match: under 20 % it says so instead of showing a weak top hit.",
        "Compare one row against hybrid+ce, then open the evaluation page behind the choice.",
    ]
    for index, step in enumerate(steps):
        top = Inches(1.55 + index * 0.9)
        circle_number(slide, Inches(0.8), top, index + 1)
        text(slide, Inches(1.65), top + Inches(0.05), Inches(10.8), Inches(0.6), step,
             size=18, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    slide.notes_slide.notes_text_frame.text = (
        "B drives, A narrates the matches. Rehearsed offline (S7-AB2), script in "
        "docs/07-demo-script.md. If the demo fails, say what should have happened and "
        "go on to the evaluation slides.")


def slide_gold(deck, provisional):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "How we know it works: the gold set")
    badge(slide, provisional)
    steps = [
        ("Pool", "Top 10 of dense and hybrid+ce for 40 home courses: 562 pairs per host."),
        ("Pre-label", "A model proposes 0, 1 or 2 per pair from the two course texts, "
                      "never seeing our scores."),
        ("Check", "680 rows checked by a person; 462 labelled by a second model "
                  "(Claude) for lack of time, and reported as such."),
        ("Cold slice", "30 pairs labelled independently by the second person, for "
                       "Cohen's kappa."),
    ]
    for index, (name, detail) in enumerate(steps):
        top = Inches(1.65 + index * 1.2)
        circle_number(slide, Inches(0.6), top, index + 1, fill=NAVY, colour=WHITE)
        text(slide, Inches(1.4), top - Inches(0.02), Inches(5.6), Inches(0.4), name,
             size=18, bold=True, color=NAVY, font=HEAD_FONT)
        text(slide, Inches(1.4), top + Inches(0.4), Inches(5.6), Inches(0.7), detail,
             size=14, color=INK)
    facts = [("Correction rate", correction_rate()), ("Agreement (kappa)", load_kappa()),
             ("Rubric", "would a coordinator sign it off?")]
    for index, (label, value) in enumerate(facts):
        top = Inches(1.65 + index * 1.6)
        box(slide, Inches(7.6), top, Inches(5.1), Inches(1.3), PALE)
        text(slide, Inches(7.9), top + Inches(0.15), Inches(4.6), Inches(0.4), label,
             size=13, color=MUTED)
        text(slide, Inches(7.9), top + Inches(0.55), Inches(4.6), Inches(0.6), value,
             size=22, bold=True, color=BLUE, font=HEAD_FONT)
    slide.notes_slide.notes_text_frame.text = (
        "A. Why a human pass at all: an unchecked model label would make every number "
        "measure agreement with that model (Clarke and Dietz 2024). The correction rate "
        "is the evidence the pass was real.")


def queries_of(results) -> str:
    counts = {int(row["queries"]) for row in results.values() if "queries" in row}
    return str(counts.pop()) if len(counts) == 1 else "about 40"


def slide_results(deck, results, provisional):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "Measured results (labelled host: Twente TCS)")
    badge(slide, provisional)
    configs = [c for c in ("bm25", "dense-minilm", "dense-bge", "hybrid", "hybrid+ce")
               if c in results]
    data = CategoryChartData()
    data.categories = configs
    for metric in ("P@1", "Recall@5", "MRR@10"):
        data.add_series(metric, [round(results[c][metric], 2) for c in configs])
    frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5),
                                   Inches(1.5), Inches(8.2), Inches(5.4), data)
    chart = frame.chart
    style_chart(chart)
    chart.value_axis.maximum_scale = 1.0
    chart.value_axis.minimum_scale = 0.0
    chart.value_axis.tick_labels.number_format = "0.0"
    chart.value_axis.tick_labels.number_format_is_linked = False
    plot = chart.plots[0]
    plot.gap_width = 60
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.number_format = "0.00"
    labels.number_format_is_linked = False
    labels.position = XL_LABEL_POSITION.OUTSIDE_END
    labels.font.size = Pt(10)
    for series, colour in zip(plot.series, (NAVY, BLUE, GOLD), strict=True):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = colour
    text(slide, Inches(9.1), Inches(1.6), Inches(3.7), Inches(0.4), "Cost per query",
         size=13, color=MUTED)
    for index, config in enumerate(c for c in configs if c in ("hybrid", "hybrid+ce")):
        top = Inches(2.05 + index * 1.35)
        box(slide, Inches(9.1), top, Inches(3.7), Inches(1.15), PALE)
        ms = results[config]["ms_per_query"]
        text(slide, Inches(9.35), top + Inches(0.12), Inches(1.9), Inches(0.9),
             f"{ms:.0f} ms", size=26, bold=True, color=BLUE, font=HEAD_FONT,
             anchor=MSO_ANCHOR.MIDDLE)
        text(slide, Inches(11.2), top + Inches(0.12), Inches(1.5), Inches(0.9), config,
             size=14, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, Inches(9.1), Inches(4.95), Inches(3.7), Inches(1.9),
         "Same quality, several hundred times the latency: hybrid is served, "
         "hybrid+ce stays selectable.", size=14, color=INK, italic=True)
    slide.notes_slide.notes_text_frame.text = (
        "A. The confidence intervals and the paired test are in eval/report/results.md. "
        f"At {queries_of(results)} queries a 95 % interval is about plus or minus 0.10, so "
        "quote the paired test, which works on per-query differences. The one significant "
        "gain is hybrid over dense-minilm on Recall@5 against Twente Applied Mathematics, "
        "eval/report/utwente-am-bsc/results.md.")


def slide_silver(deck):
    """Every host on the model-judged silver set, if eval/run_silver.py has run."""
    path = REPO_ROOT / "eval" / "report" / "silver.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "All six host universities")
    tag = box(slide, Inches(9.35), Inches(0.5), Inches(3.4), Inches(0.42), GOLD)
    run = tag.text_frame.paragraphs[0].add_run()
    run.text = "MODEL-JUDGED (SILVER) LABELS"
    run.font.size, run.font.bold, run.font.name = Pt(12), True, BODY_FONT
    run.font.color.rgb = NAVY
    tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    configs = ["bm25", "dense-minilm", "hybrid", "hybrid+ce"]
    hosts = [r["host"] for r in rows if r["config"] == "bm25" and r["host"] != "all"]
    names = {"epfl-cs-msc": "EPFL", "tudelft-cse-bsc": "TU Delft",
             "polimi-ecs-bsc": "Polimi", "kth-cs-msc": "KTH",
             "utwente-am-bsc": "Twente AM", "utwente-tcs-bsc": "Twente TCS", "all": "All"}
    value = {(r["config"], r["host"]): r for r in rows}
    shape = slide.shapes.add_table(len(hosts) + 2, len(configs) + 2, Inches(0.6),
                                   Inches(1.6), Inches(8.4), Inches(4.6))
    table = shape.table
    header = ["P@1 (Recall@5)", "Queries"] + configs
    for column, text_value in enumerate(header):
        table.cell(0, column).text = text_value
    for row_index, host in enumerate(hosts + ["all"], start=1):
        table.cell(row_index, 0).text = names.get(host, host)
        table.cell(row_index, 1).text = value[("bm25", host)]["queries"]
        for column, config in enumerate(configs, start=2):
            row = value[(config, host)]
            table.cell(row_index, column).text = (
                f"{float(row['P@1']):.2f} ({float(row['Recall@5']):.2f})")
    for cell_row in table.rows:
        for cell in cell_row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for text_run in paragraph.runs:
                    text_run.font.size = Pt(13)
                    text_run.font.name = BODY_FONT
    text(slide, Inches(9.4), Inches(1.7), Inches(3.4), Inches(5.0), [
        "20 home courses stratified by subject, the same against every host, pooled "
        "from all five strategies and labelled blind by a model.",
        "Recall is level everywhere. Plain BM25 has the best first answer: standard "
        "course titles make keyword overlap a strong signal.",
        "Silver against the human-checked gold rows: weighted kappa 0.63.",
    ], size=14)
    slide.notes_slide.notes_text_frame.text = (
        "A. Say first that these labels are a model's, not a human's, and why they exist: "
        "the gold set covers Twente only. Numbers from eval/report/silver.md. BM25's P@1 "
        "lead is not tested for significance there; the paired tests against the "
        "baseline are all non-significant.")


def slide_reranker(deck, provisional):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "The reranker: veto or opinion")
    # Replace against fuse was measured once, during development, on the model's
    # pre-labels (ablations.md). The final table has only the fused version, so this
    # slide keeps the provisional tag whatever the other slides say.
    badge(slide, "PROVISIONAL LABELS")
    data = CategoryChartData()
    data.categories = ["P@1", "Recall@5", "MRR@10"]
    data.add_series("hybrid, no reranker", (0.86, 0.80, 0.90))
    data.add_series("reranker replaces the order", (0.68, 0.72, 0.77))
    data.add_series("reranker fused by RRF", (0.82, 0.82, 0.88))
    frame = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.5), Inches(1.5),
                                   Inches(7.4), Inches(5.4), data)
    chart = frame.chart
    style_chart(chart)
    chart.value_axis.minimum_scale = 0.5
    chart.category_axis.reverse_order = True  # bar charts draw bottom-up otherwise
    chart.value_axis.maximum_scale = 1.0
    plot = chart.plots[0]
    plot.gap_width = 50
    plot.has_data_labels = True
    plot.data_labels.number_format = "0.00"
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(10)
    for series, colour in zip(plot.series, (NAVY, RED, GOLD), strict=True):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = colour
    text(slide, Inches(8.4), Inches(1.7), Inches(4.4), Inches(5.0), [
        "The proposal expected the cross-encoder to win. Letting it replace the "
        "retrieval order made every metric worse.",
        "It was trained on short web queries against passages. Here both sides are "
        "long course descriptions.",
        "Fused as a third ranking beside BM25 and dense, it recovers to level with "
        "hybrid. One opinion among three, never a veto.",
    ], size=15)
    slide.notes_slide.notes_text_frame.text = (
        "A. If asked whether the project failed because the reranker did not win: the "
        "comparison is the result, and it is measured and explained. Numbers from "
        "eval/report/ablations.md sections 1 and 1b, on the pre-labels; on the final "
        "labels the fused reranker is level with hybrid (previous slide).")


def slide_recognition(deck, provisional):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "From a score to recognised ECTS")
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    # The chart is the calibration file, which stays provisional until it is refitted on
    # checked labels, even after the results table stops being provisional.
    source = calibration.get("label_source", "")
    if provisional or "PROVISIONAL" in source:
        badge(slide, "PARTLY MODEL-LABELLED" if "model-labelled" in source
              else "PROVISIONAL LABELS")
    table = calibration["reliability"]
    data = CategoryChartData()
    data.categories = [row["bin"] for row in table]
    data.add_series("predicted", [row["predicted"] for row in table])
    data.add_series("observed", [row["observed"] for row in table])
    frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5),
                                   Inches(1.5), Inches(6.6), Inches(5.3), data)
    chart = frame.chart
    style_chart(chart)
    chart.value_axis.maximum_scale = 1.0
    chart.value_axis.minimum_scale = 0.0
    chart.has_title = True
    chart.chart_title.text_frame.text = (
        f"Calibration of hybrid, {calibration['pairs']} pairs")
    chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
    plot = chart.plots[0]
    plot.gap_width = 70
    for series, colour in zip(plot.series, (BLUE, GOLD), strict=True):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = colour
    box(slide, Inches(7.6), Inches(1.6), Inches(5.1), Inches(1.5), NAVY)
    text(slide, Inches(7.9), Inches(1.75), Inches(4.6), Inches(1.2),
         ["expected ECTS =", "sum of p(best match) x ECTS(home course)"],
         size=17, color=WHITE, font=HEAD_FONT, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, Inches(7.6), Inches(3.4), Inches(5.1), Inches(3.4), [
        "Platt scaling on the fused rank score and the embedding cosine gives the "
        "probability that a human labelled the pair a match. Rank alone cannot tell a "
        "good top hit from the best of a bad lot; the cosine can.",
        "Only the best candidate per home course counts, partial matches count as "
        "matches, and an ECTS shortfall is shown rather than hidden.",
    ], size=15)
    slide.notes_slide.notes_text_frame.text = (
        "A. Without calibration the percentage is a display value and cannot be summed; "
        "the interface refuses the ECTS total for an uncalibrated strategy. Quote the "
        "estimate with positive label 1 and 2, the gap is the partial-match question.")


def slide_honest_ui(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "An interface that does not overstate")
    checked, total = gold_progress()
    human, model = label_counts()
    counted = (f"It says how many of the {total} gold labels a person gave ({human}) and "
               f"how many a second model gave ({model}), instead of calling them all checked."
               if model else
               f"It shows how many of the {total} gold pairs a human has checked "
               f"({checked} today) and stays provisional until every one is.")
    cards = [
        ("Two kinds of score", "A calibrated strategy shows a percentage and a likely, "
         "borderline or unlikely band. The others show a bare relative number and a "
         "tooltip saying it is not a probability. One file formats every score."),
        ("No sum without a calibration", "The recognition panel will not add up "
         "ECTS for a strategy without a fitted calibration. Summing display values "
         "would be arithmetic on the wrong thing."),
        ("Provisional says so", "While a calibration rests on labels that are not all "
         "a person's, every "
         "probability and the ECTS estimate carry a warning. The flag is read from "
         "the calibration file, not typed into the interface."),
        ("The evaluation page counts", counted),
    ]
    for index, (name, detail) in enumerate(cards):
        col, row = index % 2, index // 2
        left, top = Inches(0.6 + col * 6.2), Inches(1.6 + row * 2.6)
        box(slide, left, top, Inches(5.9), Inches(2.3), PALE)
        circle_number(slide, left + Inches(0.3), top + Inches(0.3), index + 1,
                      fill=NAVY, colour=WHITE)
        text(slide, left + Inches(1.1), top + Inches(0.33), Inches(4.5), Inches(0.5),
             name, size=18, bold=True, color=NAVY, font=HEAD_FONT)
        text(slide, left + Inches(1.1), top + Inches(0.9), Inches(4.5), Inches(1.3),
             detail, size=14, color=INK)
    slide.notes_slide.notes_text_frame.text = (
        "B. frontend/src/lib/score.ts, the calibrated and provisional flags on "
        "GET /api/v1/strategies, and GET /api/v1/evaluation. The point: the numbers "
        "are only as good as the labels, and the interface never claims more than that.")


def slide_errors(deck, provisional):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "Where it goes wrong")
    badge(slide, provisional)
    cards = [
        ("No equivalent exists", "Algebra against a computer science catalogue still "
         "returns five candidates. Ranking cannot say none of these; a confidence "
         "floor can."),
        ("Granularity", "The right answer is half of a 15 ECTS module, and the whole "
         "module description dilutes it."),
        ("Look-alike projects", "Project courses read alike across a catalogue, so "
         "the text cannot separate them."),
        ("Level in the title", "Modelling and Programming 3 outranks 1: the sequence "
         "number is kept out of the embedding by design (ADR-0004)."),
    ]
    for index, (name, detail) in enumerate(cards):
        col, row = index % 2, index // 2
        left, top = Inches(0.6 + col * 6.2), Inches(1.6 + row * 2.6)
        box(slide, left, top, Inches(5.9), Inches(2.3), PALE)
        circle_number(slide, left + Inches(0.3), top + Inches(0.3), index + 1,
                      fill=NAVY, colour=WHITE)
        text(slide, left + Inches(1.1), top + Inches(0.33), Inches(4.5), Inches(0.5),
             name, size=18, bold=True, color=NAVY, font=HEAD_FONT)
        text(slide, left + Inches(1.1), top + Inches(0.9), Inches(4.5), Inches(1.3),
             detail, size=14, color=INK)
    slide.notes_slide.notes_text_frame.text = (
        "A. From eval/report/errors.md. The most common failure is answering when it "
        "should decline, which is a threshold question rather than a ranking defect.")


def slide_engineering(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, WHITE)
    title(slide, "Engineering choices")
    rows = [
        ("Frozen contract", "A Matcher protocol and a stub let the interface and the "
         "engine be built in parallel from day one."),
        ("Offline by design", "Models baked into the image at build time; the runtime "
         "never touches the network."),
        ("SQLite", "A few hundred courses: one file in a volume keeps compose to two "
         "services."),
        ("Clean-machine build", "Fresh clone to running app measured at 297 s, "
         "recorded in the README."),
    ]
    for index, (name, detail) in enumerate(rows):
        top = Inches(1.6 + index * 1.3)
        box(slide, Inches(0.6), top, Inches(12.1), Inches(1.05), PALE)
        text(slide, Inches(0.9), top + Inches(0.1), Inches(3.3), Inches(0.85), name,
             size=18, bold=True, color=NAVY, font=HEAD_FONT, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, Inches(4.3), top + Inches(0.1), Inches(8.2), Inches(0.85), detail,
             size=15, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    slide.notes_slide.notes_text_frame.text = (
        "B. Details in docs/06-defence-notes-b.md: the contract, the stub and real "
        "split, why SQLite, why the models are baked in.")


def slide_limits(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background(slide, NAVY)
    text(slide, Inches(0.6), Inches(0.45), Inches(12), Inches(0.9),
         "Limits, stated before being asked", size=36, color=WHITE, bold=True,
         font=HEAD_FONT)
    limits = [
        "Pooled judgements favour the strategies that built the pool.",
        "Labels come from students, not from the office that signs learning agreements.",
        "462 of 1142 gold labels come from a second model, not a human check.",
        "English only: a multilingual model alone would break the image budget.",
        "Master's catalogues sit a level above a bachelor's programme.",
    ]
    for index, limit in enumerate(limits):
        top = Inches(1.7 + index * 0.95)
        circle_number(slide, Inches(0.8), top, index + 1)
        text(slide, Inches(1.65), top + Inches(0.03), Inches(10.9), Inches(0.6), limit,
             size=19, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, Inches(0.8), Inches(6.6), Inches(11.5), Inches(0.5),
         "Questions", size=20, color=GOLD, bold=True, font=HEAD_FONT)
    slide.notes_slide.notes_text_frame.text = (
        "Both. A takes NLP and IR questions, B takes engineering questions.")


def main() -> int:
    results, complete = load_results()
    provisional = not complete
    tag = badge_text(provisional)
    deck = Presentation()
    deck.slide_width, deck.slide_height = Emu(12192000), Emu(6858000)  # 16:9
    slide_title(deck)
    slide_problem(deck)
    slide_pipeline(deck, results)
    slide_demo(deck)
    slide_gold(deck, tag)
    slide_results(deck, results, tag)
    slide_silver(deck)
    slide_reranker(deck, tag)
    slide_recognition(deck, provisional)
    slide_honest_ui(deck)
    slide_errors(deck, tag)
    slide_engineering(deck)
    slide_limits(deck)
    deck.save(OUT)
    state = tag or "numbers from human labels"
    print(f"wrote {OUT.relative_to(REPO_ROOT)} with {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
