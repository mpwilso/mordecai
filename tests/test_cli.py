import io
import json
import shutil

from conftest import FIXTURES, ROOT, make_result, same

from mordecai.cli import main


def run(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


def test_identify_prints_the_card_and_writes_files(tmp_path):
    card, md = tmp_path / "card.json", tmp_path / "card.md"
    code, text = run(
        [
            "identify",
            str(FIXTURES / "probe-result.json"),
            "--skill",
            str(FIXTURES / "probe"),
            "--card",
            str(card),
            "--markdown",
            str(md),
        ]
    )
    assert code == 0
    assert text.startswith("schema-probe 0.0.1: Inconclusive\n")
    assert json.loads(card.read_text())["verdict"] == "inconclusive"
    assert md.read_text().startswith("### schema-probe 0.0.1: Inconclusive")


def test_fail_on(tmp_path):
    result = tmp_path / "r.json"
    result.write_text(json.dumps(make_result(same(6, [0, 0, 0], [1, 1, 1]))))
    assert run(["identify", str(result), "--fail-on", "hurts,invalid"])[0] == 1
    assert run(["identify", str(result), "--fail-on", "invalid"])[0] == 0
    assert run(["identify", str(result), "--fail-on", "bad"])[0] == 2


def test_crawl_mode_off_a_terminal_has_no_animation_or_color(monkeypatch):
    monkeypatch.setenv("MORDECAI_MODE", "crawl")
    code, text = run(["identify", str(FIXTURES / "probe-result.json")])
    assert code == 0
    assert text.startswith("NEW ACHIEVEMENT!")
    assert "\033[" not in text and "\r" not in text


def test_unreadable_result():
    code, _ = run(["identify", str(ROOT / "pyproject.toml")])
    assert code == 2


def test_check(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    probe = tmp_path / "probe"
    shutil.copytree(FIXTURES / "probe", probe)
    card = tmp_path / "card.json"
    run(
        [
            "identify",
            str(FIXTURES / "probe-result.json"),
            "--skill",
            str(probe),
            "--card",
            str(card),
        ]
    )
    assert run(["check", str(card)])[0] == 0
    (probe / "skills" / "team-signoff" / "SKILL.md").write_text("changed")
    code, text = run(["check", str(card)])
    assert code == 1
    assert "The skill's files changed" in text
    assert run(["check", str(tmp_path / "missing.json")])[0] == 2


def test_check_model_on_the_suite_2_pair():
    """The worked example: suite 2's skill measured on Haiku 4.5 and on Sonnet 5.5. Both cards
    match the files, so only --model can tell them apart."""
    cards = ROOT / "docs" / "planted-results"
    haiku, sonnet = cards / "2-commits.card.json", cards / "2-commits-sonnet.card.json"
    assert run(["check", str(haiku)])[0] == 0
    assert run(["check", str(sonnet)])[0] == 0
    code, text = run(["check", str(haiku), "--model", "claude-sonnet-5-5"])
    assert code == 1
    assert "The card was measured on claude-haiku-4-5-20251001, not claude-sonnet-5-5." in text
    assert run(["check", str(sonnet), "--model", "claude-sonnet-5-5"])[0] == 0
    assert run(["check", str(haiku), "--model", "claude-haiku-4-5-20251001"])[0] == 0


SCENARIOS = {
    "helps": same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3),
    "hurts": same(6, [0, 0, 0], [1, 1, 1], fired=[True] * 3),
    "already-handled": same(6, [1, 1, 1], [1, 1, 1], fired=[True] * 3),
    "no-effect": same(6, [0, 0, 0], [0, 0, 0], fired=[True] * 3),
    "inconclusive": same(2, [1, 1, 1], [0, 0, 0], fired=[True] * 3),
    "never-fired": same(6, [1, 1, 1], [0, 0, 0], fired=[False] * 3),
    "invalid": same(6, [1, 1, 1], [0, 0, 0], skipped=True),
}


def test_plain_and_crawl_agree_for_every_verdict(tmp_path, monkeypatch):
    """Through the command line, for each verdict: both modes print the same numbers and
    reason, and --fail-on gives the same exit code in both."""
    import re

    from mordecai.verdict import VERDICTS

    assert sorted(SCENARIOS) == sorted(VERDICTS)
    monkeypatch.delenv("MORDECAI_MODE", raising=False)
    number = re.compile(r"[+-]?\d+(?:\.\d+)?")
    for verdict, cases in SCENARIOS.items():
        result = tmp_path / f"{verdict}.json"
        result.write_text(json.dumps(make_result(cases)))
        for fail_on, code in (
            (verdict, 1),
            ("", 0),
            (",".join(v for v in VERDICTS if v != verdict), 0),
        ):
            p_code, p_text = run(["identify", str(result), "--plain", "--fail-on", fail_on])
            c_code, c_text = run(["identify", str(result), "--crawl", "--fail-on", fail_on])
            assert p_code == c_code == code, (verdict, fail_on)
        reason = p_text.split("\n")[1]
        assert reason in c_text, verdict
        assert set(number.findall(c_text)) <= set(number.findall(p_text)), verdict
        stats = [s for s in p_text.split("\n") if s.startswith("  ") and not s.startswith("  - ")]
        assert "\n".join(stats) in c_text, verdict


def test_fail_on_values(tmp_path, capsys):
    result = tmp_path / "r.json"
    result.write_text(json.dumps(make_result(SCENARIOS["hurts"])))
    assert run(["identify", str(result)])[0] == 0
    assert run(["identify", str(result), "--fail-on", ""])[0] == 0
    assert run(["identify", str(result), "--fail-on", " , ,"])[0] == 0
    assert run(["identify", str(result), "--fail-on", " hurts , invalid "])[0] == 1
    assert run(["identify", str(result), "--fail-on", "hurts,hurts"])[0] == 1
    capsys.readouterr()
    for bad in ("Hurts", "hurts,nope", "nope"):
        assert run(["identify", str(result), "--fail-on", bad])[0] == 2, bad
        err = capsys.readouterr().err
        assert "unknown verdict(s) for --fail-on" in err and "Use helps, hurts" in err
    # An unreadable result is 2 even when --fail-on would have matched.
    assert run(["identify", str(tmp_path / "missing.json"), "--fail-on", "hurts"])[0] == 2


def test_plain_overrides_the_environment(monkeypatch):
    monkeypatch.setenv("MORDECAI_MODE", "crawl")
    assert run(["identify", str(FIXTURES / "probe-result.json")])[1].startswith("NEW ACHIEVEMENT!")
    text = run(["identify", str(FIXTURES / "probe-result.json"), "--plain"])[1]
    assert text.startswith("schema-probe 0.0.1: Inconclusive")


def test_usage_errors_exit_2(capsys):
    import pytest

    for argv in ([], ["identify"], ["nope"], ["identify", "x", "--crawl", "--plain"], ["check"]):
        with pytest.raises(SystemExit) as e:
            main(argv, out=io.StringIO())
        assert e.value.code == 2, argv
    with pytest.raises(SystemExit) as e:
        main(["--version"], out=io.StringIO())
    assert e.value.code == 0


def test_identify_cant_write_its_files(tmp_path, capsys):
    code, _ = run(
        ["identify", str(FIXTURES / "probe-result.json"), "--card", str(tmp_path / "no" / "c.json")]
    )
    assert code == 2
    assert capsys.readouterr().err.startswith("mordecai: ")
