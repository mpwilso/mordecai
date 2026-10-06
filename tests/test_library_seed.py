"""The seeded library in this repository: every stored copy is spec-valid, the planted variants
are byte for byte the measured skills, their cards are the recorded results' cards and check
current, every copy installs byte for byte, and skills/ is what export writes."""

import io
import json

import pytest
from conftest import ROOT

pytest.importorskip("strictyaml")

from mordecai.card import check  # noqa: E402
from mordecai.cli import main  # noqa: E402
from mordecai.library import install as inst  # noqa: E402
from mordecai.library.export import EXPORT_NAME, export_skills  # noqa: E402
from mordecai.library.lock import Lock  # noqa: E402
from mordecai.library.sources import Library, load_config  # noqa: E402
from mordecai.provenance import hash_dir  # noqa: E402
from mordecai.result import read_json  # noqa: E402

LIBRARIES = ["library", "examples/team/library", "examples/personal/library"]
PLANTED = {
    # library copy: (planted skill folder, recorded card)
    "library/ferry-workflow/variants/qrx": (
        "evals/planted/1-convention/skills/ferry-workflow",
        "docs/planted-results/1-convention.card.json",
    ),
    "library/branch-naming/variants/camelcase": (
        "evals/planted/validation/h1-must-fire/skills/branch-naming",
        "docs/planted-results/h1-must-fire.card.json",
    ),
}


def stored_copies():
    """Every stored skill folder: <library>/<skill>/base/<skill> and .../variants/<v>/<skill>."""
    out = []
    for lib in LIBRARIES:
        for skill in sorted((ROOT / lib).iterdir()):
            out += [p for p in [skill / "base" / skill.name] if p.is_dir()]
            out += sorted((skill / "variants").glob(f"*/{skill.name}"))
    return out


def test_every_library_validates(monkeypatch):
    monkeypatch.chdir(ROOT)
    for lib in LIBRARIES:
        out = io.StringIO()
        assert main(["library", "validate", "--library", lib], out=out) == 0, out.getvalue()
        assert " 0 error(s)" in out.getvalue()
    assert len(stored_copies()) == 9


def test_the_reference_validator_accepts_every_stored_and_published_copy():
    validator = pytest.importorskip("skills_ref.validator")
    folders = stored_copies() + sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    assert len(folders) == 12
    for folder in folders:
        assert validator.validate(folder) == [], folder


def test_planted_variants_are_byte_for_byte_the_measured_skills():
    for copy, (planted, _) in PLANTED.items():
        name = planted.rsplit("/", 1)[1]
        stored = ROOT / copy / name
        assert hash_dir(stored) == hash_dir(ROOT / planted)
        assert sorted(p.name for p in stored.iterdir()) == ["SKILL.md"]
        assert (stored / "SKILL.md").read_bytes() == (ROOT / planted / "SKILL.md").read_bytes()


def test_library_cards_are_the_recorded_results_and_check_current(monkeypatch):
    monkeypatch.chdir(ROOT)
    for copy, (_, recorded_path) in PLANTED.items():
        evidence = ROOT / copy / "evidence" / "1.0.0"
        card, _ = read_json(evidence / "card.json", "a card")
        recorded, _ = read_json(ROOT / recorded_path, "a card")
        for key in ("verdict", "numbers", "rules", "tested"):
            assert card[key] == recorded[key], (copy, key)
        assert card["hashes"]["cases"] == recorded["hashes"]["cases"]
        # The result is the raw recorded result, byte for byte.
        assert card["hashes"]["result"] == recorded["hashes"]["result"]
        assert check(card, evidence) == []
        # The library card hashes the skill folder; the recorded one hashed the whole plugin.
        assert card["hashes"]["skill"] != recorded["hashes"]["skill"]
    for recorded in sorted((ROOT / "docs/planted-results").glob("*.card.json")):
        doc, _ = read_json(recorded, "a card")
        assert check(doc, recorded.parent) == [], recorded


def test_the_library_reads_helps_and_hurts_from_them(monkeypatch):
    monkeypatch.chdir(ROOT)
    with Library(load_config(ROOT / "mordecai-library.toml")) as lib:
        for (skill, variant), verdict in {
            ("ferry-workflow", "qrx"): "helps",
            ("branch-naming", "camelcase"): "hurts",
        }.items():
            r = lib.get(skill, variant)
            e = lib.evidence(r, lib.pick(r))
            assert (e.state, e.verdict) == ("current", verdict)


def test_every_seeded_copy_installs_byte_for_byte(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    with Library(load_config(ROOT / "examples/library.toml")) as lib:
        for skill in lib.skills():
            for r in lib.copies(skill):
                proj = inst.project(tmp_path / r.copy.id)
                proj.root.mkdir()
                lock = Lock(proj.lock_path)
                p = inst.plan(lib, proj, lock, skill, r.copy.variant, exact=True, allow=["hurts"])
                inst.apply(p, proj, lock)
                installed = proj.root / ".agents/skills" / skill
                assert hash_dir(installed) == hash_dir(p.picked.folder), r.copy.id
                assert hash_dir(installed) == hash_dir(ROOT / r.copy.folder), r.copy.id


def test_skills_folder_is_what_export_writes(tmp_path, monkeypatch):
    """skills/ is the published view for npx skills and APM: one copy per name."""
    monkeypatch.chdir(ROOT)
    out = tmp_path / "skills"
    with Library(load_config(ROOT / "mordecai-library.toml")) as lib:
        export_skills(lib, out)
        tagged = bool(lib.snapshots[0].tags)
        names = set(lib.skills())
    published = ROOT / "skills"
    assert {p.name for p in published.iterdir() if p.is_dir()} == names
    for name in names:
        assert hash_dir(published / name) == hash_dir(out / name), name
    manifest = json.loads((published / EXPORT_NAME).read_text())
    assert manifest["skipped"] == []
    if tagged:  # a clone without the library's tags reads untagged copies at HEAD
        assert (published / EXPORT_NAME).read_text() == (out / EXPORT_NAME).read_text()


def test_npx_skills_finds_one_copy_per_name_first():
    """npx skills reads skills/ before anything else and keeps the first copy of each name, so
    every library skill resolves to its published copy, never to another base or variant."""
    for folder in stored_copies():
        assert (ROOT / "skills" / folder.name / "SKILL.md").is_file(), folder
