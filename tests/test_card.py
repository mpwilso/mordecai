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
    assert check(doc) == []
    (d / "evals" / "goodbye" / "prompt.md").write_text("changed")
    assert check(doc) == ["The eval cases changed since the card was written."]
    (d / "skills" / "team-signoff" / "SKILL.md").write_text("changed")
    assert check(doc)[0] == "The skill's files changed since the card was written."


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
