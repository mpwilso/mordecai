"""skill-creator's benchmark.json as a second input to identify (#29). The fixture is written
by hand from the documented schema (tests/fixtures/benchmark/NOTE.md), not a real run."""

import copy
import io
import json
import shutil

import pytest
from conftest import FIXTURES, ROOT, make_result, same

from mordecai.card import build, to_json
from mordecai.cli import main
from mordecai.render import plain
from mordecai.result import ResultError, load, parse, parse_result

BENCH = FIXTURES / "benchmark" / "benchmark.json"
NOT_MEASURED = (
    "Not measured in benchmark.json: whether the skill fired, quiet cases, cost per run, turns, "
    "refused tool calls, early stops and rate limits"
)


def bench() -> dict:
    return json.loads(BENCH.read_text())


def test_identify_reads_a_benchmark_json_by_its_shape(monkeypatch):
    monkeypatch.chdir(ROOT)
    out = io.StringIO()
    assert main(["identify", "tests/fixtures/benchmark/benchmark.json"], out=out) == 0
    text = out.getvalue()
    assert text.startswith("release-notes: Helps\n")
    assert "The skill raised the score: 90% interval " in text
    assert "Cases 6: 6 better, 0 same, 0 worse" in text
    assert "  " + NOT_MEASURED + "\n" in text
    assert "Tested on claude-sonnet-4-20250514 " in text and "2026-01-15" in text


def test_what_benchmark_json_lacks_is_never_invented(monkeypatch):
    monkeypatch.chdir(ROOT)
    suite, data = load(BENCH)
    card = build(suite, data)
    text = plain(card)
    assert "Fired in" not in text and "Cost per run" not in text and "Turns" not in text
    assert "Refused tool calls weren't checked" not in text
    r = card.reading
    assert r.fired is None and r.misfired is None
    assert r.cost_with is r.cost_without is r.turns_with is r.turns_without is None
    assert card.claude_version is None and card.judge_model is None
    doc = json.loads(to_json(card))
    assert doc["input"] == "skill-creator benchmark.json"
    assert doc["numbers"]["fired"] is None and doc["numbers"]["costPerRunWith"] is None
    assert doc["hashes"]["cases"] is None and doc["hashes"]["skill"].startswith("sha256:")
    assert any("doesn't name its eval cases' files" in w for w in r.warnings)


def test_runs_map_to_cases_and_arms():
    suite = parse_result(bench())
    assert [c.name for c in suite.cases] == [
        "Patch release",
        "Breaking change",
        "Security fix",
        "First release",
        "Docs only",
        "eval 6",
    ]
    first = suite.cases[0]
    assert [r.score for r in first.with_runs] == [1.0, 1.0, 0.86]
    assert [r.score for r in first.without_runs] == [0.43, 0.29, 0.43]
    assert first.trigger == "unmeasured" and first.dir == ""
    assert suite.model == "claude-sonnet-4-20250514"
    assert suite.started_at == "2026-01-15T10:30:00Z"
    assert suite.plugins[0].name == "release-notes" and suite.plugins[0].version is None
    assert suite.plugins[0].path == "tests/fixtures/benchmark/release-notes"
    assert suite.partial is False and suite.input == "benchmark"


def test_a_plugin_eval_result_still_parses_the_same_way():
    doc = make_result(same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3))
    assert parse_result(doc) == parse(doc)
    assert parse(doc).input == "plugin-eval"


def test_anything_else_is_refused():
    for doc in ({}, [], {"metadata": {}}, {"runs": []}, {"schemaVersion": 2}):
        with pytest.raises(ResultError, match="schemaVersion 1"):
            parse_result(doc)


def test_only_with_skill_and_without_skill_are_compared():
    """skill-creator can also compare old_skill and new_skill; that isn't a with-without
    comparison, so Mordecai refuses it rather than guessing which side is the baseline."""
    doc = bench()
    for run in doc["runs"]:
        run["configuration"] = run["configuration"].replace("without_skill", "old_skill")
    with pytest.raises(ResultError, match="with_skill and without_skill"):
        parse_result(doc)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda r: r["result"].update(pass_rate=1.5), "pass_rate is 1.5"),
        (lambda r: r["result"].pop("pass_rate"), "has no pass_rate"),
        (lambda r: r.pop("result"), "has no pass_rate"),
        (lambda r: r.update(eval_id=None), "eval_id"),
        (lambda r: r.update(eval_name=7), "eval_name should be a string"),
    ],
)
def test_a_malformed_run_is_refused(change, message):
    doc = bench()
    change(doc["runs"][0])
    with pytest.raises(ResultError, match=message):
        parse_result(doc)


def test_a_bad_metadata_or_runs_shape_is_refused():
    doc = bench()
    doc["runs"][0] = "run"
    with pytest.raises(ResultError, match="every entry of runs should be an object"):
        parse_result(doc)
    doc = bench()
    doc["metadata"]["executor_model"] = 3
    with pytest.raises(ResultError, match="executor_model should be a string"):
        parse_result(doc)


def test_the_same_verdict_rules_apply():
    doc = bench()
    for run in doc["runs"]:
        if run["configuration"] == "with_skill":
            run["result"]["pass_rate"] = 0.0
    assert build(parse_result(doc), b"x", roots=[ROOT]).reading.verdict == "hurts"
    few = copy.deepcopy(bench())
    few["runs"] = [r for r in few["runs"] if r["eval_id"] <= 4]
    assert build(parse_result(few), b"x", roots=[ROOT]).reading.verdict == "inconclusive"


def test_the_library_rechecks_a_benchmark_card(tmp_path, monkeypatch):
    pytest.importorskip("strictyaml")
    from mordecai.library.evidence import assess

    skill = tmp_path / "release-notes"
    shutil.copytree(FIXTURES / "benchmark" / "release-notes", skill)
    monkeypatch.chdir(tmp_path)
    suite, data = load(BENCH)
    card = build(suite, data, skill)
    out = tmp_path / "evidence"
    out.mkdir()
    (out / "result.json").write_bytes(data)
    (out / "card.json").write_text(to_json(card, out))
    e = assess(out, skill, tmp_path)
    assert (e.state, e.verdict) == ("cases-changed", "helps")
