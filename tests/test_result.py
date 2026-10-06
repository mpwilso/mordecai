"""A result may come from someone else. Every malformed one is refused with a clear message and
exit code 2: never a traceback, and never a card built from a value read as something else."""

import io
import json

import pytest
from conftest import make_result, same

from mordecai import result
from mordecai.cli import main
from mordecai.result import ResultError, parse


def good():
    return make_result(same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3))


def run0(doc):
    return doc["cases"][0]["arms"]["with"][0]


BAD = {
    "score NaN": (lambda d: run0(d).update(score=float("nan")), "score should be a number"),
    "score infinite": (lambda d: run0(d).update(score=float("inf")), "score should be a number"),
    "score above 1": (lambda d: run0(d).update(score=50), "score is 50; it should be from 0 to 1"),
    "score below 0": (lambda d: run0(d).update(score=-0.5), "it should be from 0 to 1"),
    "score a bool": (lambda d: run0(d).update(score=True), "score should be a number, not true"),
    "score a string": (lambda d: run0(d).update(score="1"), 'score should be a number, not "1"'),
    "score missing": (lambda d: run0(d).pop("score"), "the run has no score"),
    "negative cost": (
        lambda d: run0(d).update(costUsd=-5),
        "costUsd is -5; it should be at least 0",
    ),
    "cost a string": (lambda d: run0(d).update(costUsd="free"), "costUsd should be a number"),
    "turns NaN": (lambda d: run0(d).update(turns=float("nan")), "turns should be a number"),
    "error a number": (lambda d: run0(d).update(error=7), "error should be a string"),
    "skipped a string": (
        lambda d: run0(d).update(skippedPaidGraders="no"),
        "skippedPaidGraders should be true or false",
    ),
    "partial a string": (lambda d: d.update(partial="false"), "partial should be true or false"),
    "suite a list": (lambda d: d.update(suite=[]), "suite should be an object"),
    "cases an object": (lambda d: d.update(cases={"a": 1}), "cases should be a list"),
    "case not an object": (
        lambda d: d.update(cases=[1]),
        "every entry of cases should be an object",
    ),
    "case name a number": (lambda d: d["cases"][0].update(name=7), "name should be a string"),
    "case name empty": (lambda d: d["cases"][0].update(name=""), "a case has no name"),
    "grader a string": (
        lambda d: d["cases"][0].update(graders=["x"]),
        "every entry of graders should be an object",
    ),
    "arms a list": (lambda d: d["cases"][0].update(arms=[]), "arms should be an object"),
    "runs an object": (
        lambda d: d["cases"][0]["arms"].update(without={}),
        "without should be a list",
    ),
    "model a number": (
        lambda d: d["suite"].update(modelOverride=5),
        "modelOverride should be a string",
    ),
    "plugin path a number": (
        lambda d: d["suite"]["plugins"][0].update(path=1),
        "path should be a string",
    ),
}


@pytest.mark.parametrize("name", sorted(BAD))
def test_malformed_results_are_refused(name):
    change, message = BAD[name]
    doc = good()
    change(doc)
    with pytest.raises(ResultError, match=message.replace("(", r"\(").replace(")", r"\)")):
        parse(doc)


@pytest.mark.parametrize("name", sorted(BAD))
def test_the_command_exits_2_with_one_line(name, tmp_path, capsys):
    change, _ = BAD[name]
    doc = good()
    change(doc)
    path = tmp_path / "r.json"
    path.write_text(json.dumps(doc, allow_nan=True))
    assert main(["identify", str(path)], out=io.StringIO()) == 2
    err = capsys.readouterr().err
    assert err.startswith("mordecai: ") and err.count("\n") == 1, err


def test_nan_and_infinity_are_refused_anywhere_in_the_file(tmp_path):
    for constant in ("NaN", "Infinity", "-Infinity"):
        path = tmp_path / "r.json"
        path.write_text(json.dumps(good()).replace('"costUsd": 1.0', f'"costUsd": {constant}'))
        with pytest.raises(ResultError, match=f"{constant} isn't a number JSON allows"):
            result.load(path)


def test_unreadable_files(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_bytes(b'{"schemaVersion": 1, "x": "\xff"}')
    with pytest.raises(ResultError, match="isn't UTF-8 text"):
        result.load(bad)
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 100000 + "]" * 100000)
    with pytest.raises(ResultError, match="nested too deeply"):
        result.load(deep)
    with pytest.raises(ResultError, match="can't read"):
        result.load(tmp_path / "missing.json")
    monkeypatch.setattr(result, "MAX_BYTES", 100)
    big = tmp_path / "big.json"
    big.write_text(json.dumps(good()))
    with pytest.raises(ResultError, match="too big to be an eval result"):
        result.load(big)


def test_empty_and_zero_run_results_are_invalid_not_errors():
    """Nothing to compare is a reading, not a malformed file: the card says Invalid."""
    from mordecai.verdict import read

    for doc in (make_result([]), make_result(same(6, [], [])), make_result(same(6, [1], []))):
        r = read(parse(doc))
        assert r.verdict == "invalid"
        assert "nothing to compare" in r.reason
