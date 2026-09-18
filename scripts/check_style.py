"""Enforce CONTEXT.md section 11 (Writing style).

Checks every tracked text file for non-ASCII characters and for the banned words and
sentence patterns. Exits non-zero with a file:line report so CI fails on a bad commit.

    python scripts/check_style.py            # whole repo
    python scripts/check_style.py docs/      # one path
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "node_modules", "dist", ".cache", ".venv", "__pycache__",
             ".pytest_cache", ".ruff_cache", "report"}
TEXT_SUFFIXES = {".py", ".md", ".ts", ".tsx", ".css", ".html", ".json", ".yml",
                 ".yaml", ".csv", ".txt", ".toml", ".ini", ".cfg", ".conf"}
EXTRA_FILES = {"Dockerfile", ".env.example", ".gitignore", ".dockerignore", "nginx.conf"}

# Allowed non-ASCII, with the reason. Keep this list almost empty.
ALLOWED_NON_ASCII: set[str] = set()

BANNED_WORDS = [
    "delve", "leverages", "leveraging", "seamless", "seamlessly", "holistic",
    "cutting-edge", "state-of-the-art", "game-changing", "elevate", "empower",
    "unlock", "streamline", "foster", "embark", "tapestry", "testament",
    "showcase", "underscore", "myriad", "plethora", "paramount", "pivotal",
    "crucial", "vital", "meticulous", "nuanced", "multifaceted", "furthermore",
    "moreover", "notably", "arguably", "in essence", "at its core",
    "when it comes to", "it is worth noting", "it's worth noting", "in conclusion",
    "at the end of the day", "generally speaking", "needless to say",
]

BANNED_PATTERNS = [
    (r"\bnot just\b.{0,60}\bbut\b", "'not just X but Y' - state what it is"),
    (r"\bis not (just|merely|only)\b", "negation-then-reveal - state what it is"),
    (r"\b(isn't|is not) a .{1,40}\. It'?s a\b", "negation-then-reveal"),
    (r"\bmore than just\b", "'more than just' - state what it is"),
    (r"\blet's\b", "'let's' - use an imperative"),
    (r"\byou'll want to\b", "'you'll want to' - use an imperative"),
    (r"\bwe'll\b", "'we'll' - use a plain statement"),
    (r"\bdive (in|into)\b", "'dive into'"),
]

# Words that are fine in code identifiers but not in prose.
CODE_SAFE = re.compile(r"^\s*(#|//|\*|\"\"\")?")


def text_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in EXTRA_FILES:
            out.append(path)
    return out


def check(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return [f"{path}: not valid UTF-8"]

    is_style_doc = path.name in {"check_style.py", "CONTEXT.md"}

    for number, line in enumerate(lines, start=1):
        for char in line:
            if ord(char) > 127 and char not in ALLOWED_NON_ASCII:
                problems.append(
                    f"{path}:{number}: non-ASCII {char!r} (U+{ord(char):04X}) - "
                    f"see CONTEXT.md section 11"
                )
                break
        if is_style_doc:
            continue
        lowered = line.lower()
        for word in BANNED_WORDS:
            if re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", lowered):
                problems.append(f"{path}:{number}: banned word '{word}'")
        for pattern, why in BANNED_PATTERNS:
            if re.search(pattern, lowered):
                problems.append(f"{path}:{number}: banned pattern - {why}")
    return problems


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [REPO_ROOT]
    problems: list[str] = []
    for root in roots:
        for path in text_files(root if root.is_dir() else root.parent):
            if root.is_file() and path != root:
                continue
            problems.extend(check(path))

    if problems:
        print(f"{len(problems)} style problem(s):\n")
        for problem in problems:
            print("  " + problem)
        print("\nRules: CONTEXT.md section 11.")
        return 1
    print("style ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
