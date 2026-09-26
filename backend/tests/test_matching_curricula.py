"""Owner: Person A. The curriculum validator (S1-A3) and the committed curricula."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_curricula.py"
_spec = importlib.util.spec_from_file_location("validate_curricula", SCRIPT)
validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validator)

PMF = validator.CURRICULA / "uns-pmf-informatics-bsc.json"


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / f"{data['programme_id']}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def pmf() -> dict:
    return json.loads(PMF.read_text(encoding="utf-8"))


def test_committed_pmf_curriculum_is_valid() -> None:
    assert validator.validate(PMF) == []


def test_pmf_meets_s1_a1_acceptance(pmf: dict) -> None:
    assert len(pmf["courses"]) >= 45
    assert all(course["description"].strip() for course in pmf["courses"])


def test_duplicate_code_is_rejected(tmp_path: Path, pmf: dict) -> None:
    pmf["courses"].append(copy.deepcopy(pmf["courses"][0]))
    errors = validator.validate(_write(tmp_path, pmf))
    assert any("duplicate code" in e for e in errors)


def test_null_string_field_is_rejected(tmp_path: Path, pmf: dict) -> None:
    pmf["courses"][0]["description"] = None
    errors = validator.validate(_write(tmp_path, pmf))
    assert any("'description'" in e for e in errors)


def test_file_name_must_match_programme_id(tmp_path: Path, pmf: dict) -> None:
    path = tmp_path / "renamed.json"
    path.write_text(json.dumps(pmf), encoding="utf-8")
    assert any("file name" in e for e in validator.validate(path))


def test_prerequisite_outside_the_programme_is_a_note_not_an_error(
    tmp_path: Path, pmf: dict
) -> None:
    """Master's catalogues require bachelor courses this file does not contain."""
    pmf["courses"][0]["prerequisites"] = ["NOPE"]
    path = _write(tmp_path, pmf)
    assert validator.validate(path) == []
    assert any("NOPE" in w for w in validator.warnings_for(path))


def test_main_exits_non_zero_on_a_broken_file(tmp_path: Path, pmf: dict) -> None:
    del pmf["courses"][0]["ects"]
    assert validator.main(["validate", str(_write(tmp_path, pmf))]) == 1
    assert validator.main(["validate", str(PMF)]) == 0


# --- the loader keeps serving when one file is bad (B's audit, 2026-09-26) ----------

def test_loader_skips_a_broken_file_and_a_duplicate_programme(tmp_path: Path,
                                                               pmf: dict) -> None:
    import copy

    from app.ingest.loader import CurriculumStore

    (tmp_path / "a-good.json").write_text(json.dumps(pmf), encoding="utf-8")
    (tmp_path / "b-broken.json").write_text("{not json", encoding="utf-8")
    twin = copy.deepcopy(pmf)
    twin["programme_name"] = "a second file with the same programme_id"
    (tmp_path / "c-twin.json").write_text(json.dumps(twin), encoding="utf-8")
    store = CurriculumStore(tmp_path)
    programmes = store.list_programmes()
    assert [p.programme_id for p in programmes] == [pmf["programme_id"]]
    assert programmes[0].programme_name == pmf["programme_name"]


def test_programmes_are_listed_home_first_then_in_partner_order(tmp_path: Path,
                                                                pmf: dict) -> None:
    from app.ingest.loader import CurriculumStore

    curricula = tmp_path / "curricula"
    curricula.mkdir()
    for institution in ("aaa", "zzz", "uns-pmf", "mmm"):
        data = dict(pmf, institution_id=institution, programme_id=f"{institution}-x")
        (curricula / f"{institution}-x.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "partners.json").write_text(json.dumps({
        "home": ["uns-pmf"],
        "partners": [{"institution_id": "zzz"}, {"institution_id": "mmm"}],
    }), encoding="utf-8")
    listed = [p.programme_id for p in CurriculumStore(curricula).list_programmes()]
    assert listed == ["uns-pmf-x", "zzz-x", "mmm-x", "aaa-x"]
