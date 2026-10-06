"""Hashes, the card's JSON, staleness, and the three ways of printing a card."""

import json
import re
import shutil

from conftest import FIXTURES, make_result, same

from mordecai.card import build, check, to_json
from mordecai.provenance import hash_dir, hash_skill
from mordecai.render import crawl, markdown, plain, stat_block
from mordecai.result import load, parse
from mordecai.verdict import VERDICTS


def probe_copy(tmp_path):
    dest = tmp_path / "probe"
    shutil.copytree(FIXTURES / "probe", dest)
    return dest


def test_hash_ignores_results_and_caches(tmp_path):
    d = probe_copy(tmp_path)
    before = hash_dir(d)
    (d / "evals" / "results").mkdir()
    (d / "evals" / "results" / "x.json").write_text("{}")
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "a.pyc").write_bytes(b"x")
    assert hash_dir(d) == before


def test_skill_hash_leaves_out_the_cases(tmp_path):
    d = probe_copy(tmp_path)
    before = hash_skill(d, ["evals/goodbye"])
    (d / "evals" / "goodbye" / "prompt.md").write_text("changed")
    assert hash_skill(d, ["evals/goodbye"]) == before
    (d / "skills" / "team-signoff" / "SKILL.md").write_text("changed")
    assert hash_skill(d, ["evals/goodbye"]) != before


def test_a_card_goes_stale_when_the_skill_or_cases_change(tmp_path):
    d = probe_copy(tmp_path)
    suite, data = load(FIXTURES / "probe-result.json")
    doc = json.loads(to_json(build(suite, data, d)))
    assert check(doc, roots=[tmp_path]) == []
    (d / "evals" / "goodbye" / "prompt.md").write_text("changed")
    assert check(doc, roots=[tmp_path]) == ["The eval cases changed since the card was written."]
    (d / "skills" / "team-signoff" / "SKILL.md").write_text("changed")
    assert (
        check(doc, roots=[tmp_path])[0] == "The skill's files changed since the card was written."
    )


def test_card_json_is_stable_and_complete(tmp_path):
    d = probe_copy(tmp_path)
    suite, data = load(FIXTURES / "probe-result.json")
    a, b = to_json(build(suite, data, d)), to_json(build(suite, data, d))
    assert a == b
    doc = json.loads(a)
    assert doc["verdict"] == "inconclusive"
    assert doc["subject"] == {
        "plugin": "schema-probe",
        "version": "0.0.1",
        "skills": ["team-signoff"],
    }
    assert doc["hashes"]["result"].startswith("sha256:")
    assert doc["tested"]["model"] == "haiku"


def test_a_card_without_files_says_it_cant_be_checked():
    suite, data = load(FIXTURES / "probe-result.json")
    card = build(suite, data)
    assert card.skill_hash is None
    assert "can't be checked for staleness" in card.reading.warnings[-1]


NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?")


def cards():
    """One card for each verdict."""
    scenarios = {
        "helps": same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3),
        "hurts": same(6, [0, 0, 0], [1, 1, 1], fired=[True] * 3),
        "already-handled": same(6, [1, 1, 1], [1, 1, 1], fired=[True] * 3),
        "no-effect": same(6, [0, 0, 0], [0, 0, 0], fired=[True] * 3),
        "inconclusive": same(2, [1, 1, 1], [0, 0, 0], fired=[True] * 3),
        "never-fired": same(6, [1, 1, 1], [0, 0, 0], fired=[False] * 3),
        "invalid": same(6, [1, 1, 1], [0, 0, 0], skipped=True),
    }
    out = {}
    for verdict, cases in scenarios.items():
        doc = make_result(cases)
        out[verdict] = build(parse(doc), json.dumps(doc).encode())
    assert sorted(out) == sorted(VERDICTS)
    return out


def test_every_mode_shows_the_same_facts():
    for verdict, card in cards().items():
        block = "\n".join("  " + s for s in stat_block(card))
        assert block in plain(card), verdict
        assert block in crawl(card), verdict
        assert "\n".join(stat_block(card)) in markdown(card), verdict
        assert card.reading.reason in crawl(card)


def test_crawl_mode_adds_no_numbers():
    for verdict, card in cards().items():
        assert set(NUMBER.findall(crawl(card))) <= set(NUMBER.findall(plain(card))), verdict


def test_crawl_mode_has_loot():
    c = cards()
    assert "ENCHANTED (+100)" in crawl(c["helps"])
    assert "CURSED (-100)" in crawl(c["hurts"])
    assert "VENDOR TRASH" in crawl(c["already-handled"])
    assert crawl(c["helps"]).startswith("NEW ACHIEVEMENT! Actually Useful.")
    assert "\033[" not in crawl(c["helps"])
    assert "\033[1;33mENCHANTED (+100)\033[0m" in crawl(c["helps"], color=True)


def test_plain_mode_has_no_flavor():
    for card in cards().values():
        text = plain(card)
        for word in ("ACHIEVEMENT", "Mordecai:", "ENCHANTED", "CURSED", "dungeon"):
            assert word not in text


def test_card_paths_are_relative_and_survive_a_move(tmp_path):
    """A card stores no absolute paths: the skill is relative to the card's directory and the
    cases' root to the skill. Moving the whole tree keeps the card checkable."""
    tree = tmp_path / "repo"
    skill = tree / "skills-under-test" / "probe"
    shutil.copytree(FIXTURES / "probe", skill)
    cards = tree / "docs" / "cards"
    cards.mkdir(parents=True)
    suite, data = load(FIXTURES / "probe-result.json")
    text = to_json(build(suite, data, skill), cards)
    doc = json.loads(text)
    assert str(tmp_path) not in text
    assert doc["paths"]["skill"] == "../../skills-under-test/probe"
    assert doc["paths"]["casesRoot"] == "."
    assert check(doc, cards, roots=[tree]) == []
    moved = tmp_path / "elsewhere"
    shutil.move(str(tree), str(moved))
    assert check(doc, moved / "docs" / "cards", roots=[moved]) == []
    (moved / "skills-under-test" / "probe" / "skills" / "team-signoff" / "SKILL.md").write_text("x")
    assert check(doc, moved / "docs" / "cards", roots=[moved]) == [
        "The skill's files changed since the card was written."
    ]


def test_an_old_card_with_absolute_paths_still_checks(tmp_path):
    d = probe_copy(tmp_path)
    suite, data = load(FIXTURES / "probe-result.json")
    doc = json.loads(to_json(build(suite, data, d)))
    doc["paths"]["skill"] = str(d)
    doc["paths"]["casesRoot"] = str(d)
    assert check(doc, tmp_path / "anywhere", roots=[tmp_path]) == []


def test_a_card_reads_refusals_from_run_traces_inside_its_roots(tmp_path, monkeypatch):
    """The runs' traces are read only where the result's other paths are: inside the current
    directory or the skill directory. A trace anywhere else is never opened."""
    inside, outside = tmp_path / "inside", tmp_path / "outside"
    inside.mkdir()
    outside.mkdir()
    trace = (FIXTURES / "denied-trace.jsonl").read_bytes()
    (inside / "trace.jsonl").write_bytes(trace)
    (outside / "trace.jsonl").write_bytes(trace)
    monkeypatch.chdir(inside)

    def card_with(path):
        doc = make_result(same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3))
        doc["cases"][0]["arms"]["without"][1]["tracePath"] = str(path)
        return build(parse(doc), json.dumps(doc).encode())

    card = card_with(inside / "trace.jsonl")
    assert card.reading.verdict == "helps"
    assert any(
        w.startswith("1 of the 1 runs whose traces were read (of 36) had a tool call refused")
        and "(0 with the skill, 1 without)" in w
        for w in card.reading.warnings
    )
    assert not any("refused" in w for w in card_with(outside / "trace.jsonl").reading.warnings)
    # A trace path the system can't even look up is skipped too: the trace is optional.
    for odd in ("x" * 5000, "a" + chr(0) + "b"):
        assert card_with(odd).reading.verdict == "helps"
