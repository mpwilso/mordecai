"""mordecai measure: claude plugin eval with a pinned model and a cost cap, then the card, in one
step. No test runs the real claude: a fake one on PATH records what it was asked and writes a
known result, or the lookup is made to fail."""

import io
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest
from conftest import FIXTURES

from mordecai import cli
from mordecai.cli import main

# The fake claude: records its arguments, then writes the probe result where --json says, or
# exits with FAKE_EXIT, or writes nothing when FAKE_SILENT is set.
FAKE = """\
import json, os, shutil, sys
args = sys.argv[1:]
Path = __import__("pathlib").Path
Path(os.environ["FAKE_ARGV"]).write_text(json.dumps(args))
if os.environ.get("FAKE_EXIT"):
    sys.exit(int(os.environ["FAKE_EXIT"]))
if not os.environ.get("FAKE_SILENT"):
    shutil.copy(os.environ["FAKE_RESULT"], args[args.index("--json") + 1])
"""


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """A claude on PATH that runs FAKE, and the file it records its arguments in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "fake_claude.py"
    script.write_text(FAKE)
    if sys.platform == "win32":
        bat = bin_dir / "claude.bat"
        bat.write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        sh = bin_dir / "claude"
        sh.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        sh.chmod(sh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_ARGV", str(argv_file))
    monkeypatch.setenv("FAKE_RESULT", str(FIXTURES / "probe-result.json"))
    for name in ("FAKE_EXIT", "FAKE_SILENT"):
        monkeypatch.delenv(name, raising=False)
    return argv_file


@pytest.fixture
def work(tmp_path, monkeypatch):
    """A working directory holding a copy of the probe plugin, as a person would run from."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MORDECAI_MODE", raising=False)
    shutil.copytree(FIXTURES / "probe", tmp_path / "probe")
    return tmp_path


def run(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


def test_measure_runs_the_eval_as_the_readme_shows_then_writes_the_card(fake_claude, work):
    card, md = work / "card.json", work / "card.md"
    code, text = run(
        [
            "measure",
            "probe",
            "--model",
            "claude-sonnet-5-5",
            "--max-cost-usd",
            "5",
            "--card",
            str(card),
            "--markdown",
            str(md),
        ]
    )
    assert code == 0
    assert text.startswith("schema-probe 0.0.1: Inconclusive\n")
    recorded = json.loads(fake_claude.read_text())
    assert recorded == [
        "plugin",
        "eval",
        "--trust-plugin",
        "--no-publish",
        "probe",
        "--model",
        "claude-sonnet-5-5",
        "--json",
        "result.json",
        "--max-cost-usd",
        "5",
    ]
    assert (work / "result.json").read_bytes() == (FIXTURES / "probe-result.json").read_bytes()
    assert json.loads(card.read_text())["verdict"] == "inconclusive"
    assert md.read_text().startswith("### schema-probe 0.0.1: Inconclusive")


def test_result_and_skill_can_be_named_and_the_cap_is_passed_as_given(fake_claude, work):
    result = work / "runs" / "r.json"
    result.parent.mkdir()
    code, _ = run(
        [
            "measure",
            "probe",
            "--model",
            "m",
            "--max-cost-usd",
            "2.50",
            "--result",
            str(result),
            "--skill",
            "probe",
        ]
    )
    assert code == 0
    recorded = json.loads(fake_claude.read_text())
    assert recorded[recorded.index("--json") + 1] == str(result)
    assert recorded[-2:] == ["--max-cost-usd", "2.50"]
    assert result.is_file()


def test_fail_on_applies_to_the_measured_card(fake_claude, work):
    assert (
        run(
            ["measure", "probe", "--model", "m", "--max-cost-usd", "1", "--fail-on", "inconclusive"]
        )[0]
        == 1
    )
    (work / "result.json").unlink()
    assert (
        run(["measure", "probe", "--model", "m", "--max-cost-usd", "1", "--fail-on", "hurts"])[0]
        == 0
    )


def test_measure_refuses_without_a_model_and_a_cap_before_anything_runs(fake_claude, work, capsys):
    for argv in (
        ["measure", "probe"],
        ["measure", "probe", "--model", "m"],
        ["measure", "probe", "--max-cost-usd", "1"],
    ):
        assert run(argv)[0] == 2, argv
        assert "needs --model and --max-cost-usd" in capsys.readouterr().err
    for cap in ("0", "-1", "five", "inf", "nan"):
        assert run(["measure", "probe", "--model", "m", "--max-cost-usd", cap])[0] == 2, cap
        assert "must be a number above zero" in capsys.readouterr().err
    assert not fake_claude.exists(), "claude was run"


def test_measure_refuses_bad_input_before_the_eval_spends_anything(fake_claude, work, capsys):
    base = ["measure", "probe", "--model", "m", "--max-cost-usd", "1"]
    assert run(base + ["--fail-on", "nope"])[0] == 2
    assert "unknown verdict(s)" in capsys.readouterr().err
    assert run(["measure", "missing", "--model", "m", "--max-cost-usd", "1"])[0] == 2
    assert "is not a directory" in capsys.readouterr().err
    (work / "result.json").write_text("{}")
    assert run(base)[0] == 2
    assert "already exists" in capsys.readouterr().err
    assert (work / "result.json").read_text() == "{}"
    assert not fake_claude.exists(), "claude was run"


def test_no_claude_on_path_exits_3(work, monkeypatch, capsys):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert run(["measure", "probe", "--model", "m", "--max-cost-usd", "1"])[0] == 3
    assert "claude is not on PATH" in capsys.readouterr().err
    assert not (work / "result.json").exists()


def test_an_eval_that_fails_or_writes_nothing_exits_3_with_no_card(
    fake_claude, work, monkeypatch, capsys
):
    card = work / "card.json"
    base = ["measure", "probe", "--model", "m", "--max-cost-usd", "1", "--card", str(card)]
    monkeypatch.setenv("FAKE_EXIT", "7")
    assert run(base)[0] == 3
    assert "exited 7; no card was written" in capsys.readouterr().err
    assert json.loads(fake_claude.read_text())[:2] == ["plugin", "eval"]
    assert not card.exists() and not (work / "result.json").exists()
    monkeypatch.delenv("FAKE_EXIT")
    monkeypatch.setenv("FAKE_SILENT", "1")
    assert run(base)[0] == 3
    assert "wrote no result.json; no card was written" in capsys.readouterr().err
    assert not card.exists()


def test_the_argv_is_the_readme_command():
    """The eval line in the README's Try it is what measure runs, flag for flag."""
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    line = next(ln for ln in readme.splitlines() if ln.startswith("claude plugin eval "))
    shown = ["plugin" if w == "path/to/plugin" else w for w in line.split()]
    ours = cli.eval_argv("claude", Path("plugin"), "claude-sonnet-5-5", Path("result.json"), "5")
    assert sorted(shown) == sorted(ours)
