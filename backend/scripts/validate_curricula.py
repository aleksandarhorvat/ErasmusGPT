"""Check curriculum JSON files against docs/03-data-schema.md.

    python backend/scripts/validate_curricula.py                  # every data/curricula/*.json
    python backend/scripts/validate_curricula.py path/to/file.json

Prints one line per problem as file: message and exits 1 if any file has an error.
Standard library only, so CI can run it without installing anything.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CURRICULA = REPO / "data" / "curricula"

# field -> allowed types. type(None) in the tuple means the field may be null.
PROGRAMME_FIELDS: dict[str, tuple] = {
    "programme_id": (str,),
    "institution_id": (str,),
    "institution_name": (str,),
    "country": (str,),
    "programme_name": (str,),
    "level": (str,),
    "language": (str,),
    "total_ects": (int, float),
    "academic_year": (str,),
    "source_url": (str,),
    "scraped_at": (str,),
    "courses": (list,),
}
COURSE_FIELDS: dict[str, tuple] = {
    "code": (str,),
    "title": (str,),
    "ects": (int, float),
    "year": (int, type(None)),
    "semester": (int, type(None)),
    "mandatory": (bool,),
    "module": (str, type(None)),
    "language": (str,),
    "description": (str,),
    "learning_outcomes": (list,),
    "topics": (list,),
    "prerequisites": (list,),
    "url": (str, type(None)),
}
LEVELS = {"bachelor", "master"}


def _type_errors(record: dict, fields: dict[str, tuple], where: str) -> list[str]:
    errors = []
    for name, types in fields.items():
        if name not in record:
            errors.append(f"{where}: missing field '{name}'")
        # bool is a subclass of int, so True must not pass as an ECTS value.
        elif not isinstance(record[name], types) or (
            isinstance(record[name], bool) and bool not in types
        ):
            allowed = " or ".join("null" if t is type(None) else t.__name__ for t in types)
            errors.append(f"{where}: '{name}' is {record[name]!r}, expected {allowed}")
    return errors


def validate(path: Path) -> list[str]:
    """Every problem in one file, as human-readable strings. Empty list means valid."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read: {exc}"]
    if not isinstance(data, dict):
        return ["top level must be an object"]

    errors = _type_errors(data, PROGRAMME_FIELDS, "programme")
    if data.get("programme_id") != path.stem:
        errors.append(f"programme_id {data.get('programme_id')!r} != file name {path.stem!r}")
    if data.get("level") not in LEVELS:
        errors.append(f"level {data.get('level')!r} not in {sorted(LEVELS)}")

    courses = data.get("courses") if isinstance(data.get("courses"), list) else []
    if not courses:
        errors.append("no courses")

    seen: set[str] = set()
    for index, course in enumerate(courses):
        if not isinstance(course, dict):
            errors.append(f"courses[{index}]: not an object")
            continue
        where = f"course {course.get('code', f'[{index}]')}"
        errors += _type_errors(course, COURSE_FIELDS, where)

        code = course.get("code")
        if code in seen:
            errors.append(f"{where}: duplicate code, course_uid would collide")
        seen.add(code)
        if isinstance(code, str) and (not code.strip() or not code.isascii()):
            errors.append(f"{where}: code must be non-empty ASCII, got {code!r}")
        if isinstance(course.get("ects"), int | float) and course["ects"] <= 0:
            errors.append(f"{where}: ects must be positive")
        for name in ("learning_outcomes", "topics", "prerequisites"):
            items = course.get(name)
            if isinstance(items, list) and not all(isinstance(i, str) for i in items):
                errors.append(f"{where}: '{name}' must contain only strings")

    return errors


def warnings_for(path: Path) -> list[str]:
    """Things worth seeing that are not schema violations, so they never fail a build.

    A prerequisite outside the programme is normal for a master's catalogue: EPFL's MSc
    courses require EPFL bachelor courses that this file does not contain.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    courses = data.get("courses", [])
    codes = {c.get("code") for c in courses if isinstance(c, dict)}
    out = []
    dangling = {
        prerequisite
        for course in courses
        if isinstance(course, dict) and isinstance(course.get("prerequisites"), list)
        for prerequisite in course["prerequisites"]
        if prerequisite not in codes
    }
    if dangling:
        out.append(
            f"{len(dangling)} prerequisites name courses outside this programme, "
            f"for example {', '.join(sorted(dangling)[:3])}"
        )
    empty = [c.get("code") for c in courses if isinstance(c, dict) and not c.get("description")]
    if empty:
        out.append(f"{len(empty)} courses have an empty description: {', '.join(empty[:5])}")
    return out


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or sorted(CURRICULA.glob("*.json"))
    if not paths:
        print(f"no curriculum files in {CURRICULA}")
        return 1
    failed = 0
    for path in paths:
        errors = validate(path)
        if errors:
            failed += 1
            for error in errors:
                print(f"{path.name}: {error}")
        else:
            print(f"{path.name}: ok")
            for warning in warnings_for(path):
                print(f"{path.name}: note: {warning}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
