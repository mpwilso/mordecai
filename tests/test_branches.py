"""Branches the other tests don't reach: crawl mode on a real terminal, cards and results with
nothing in them, and lint's remaining warnings."""

import io
import subprocess
import sys

import pytest
from conftest import FIXTURES, ROOT, make_result, same

from mordecai import cli
from mordecai.card import build, check
from mordecai.lint import frontmatter, lint
from mordecai.render import DOT, plain
from mordecai.result import ResultError, parse


class Terminal(io.StringIO):
    def isatty(self):
        return True


def test_crawl_on_a_terminal_opens_the_box_and_colors_the_rarity(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    opened = []
    monkeypatch.setattr(cli, "_open_box", lambda stream: opened.append(stream))
    out = Terminal()
    assert cli.main(["identify", str(FIXTURES / "probe-result.json"), "--crawl"], out=out) == 0
    assert opened == [out]
    assert "\033[1;36mUNIDENTIFIED\033[0m" in out.getvalue()


@pytest.mark.parametrize("env", [{"NO_COLOR": "1"}, {"TERM": "dumb"}])
def test_no_color_and_dumb_terminals_get_no_box_or_color(monkeypatch, env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    out = Terminal()
    cli.main(["identify", str(FIXTURES / "probe-result.json"), "--crawl"], out=out)
    assert "\033[" not in out.getvalue() and "\r" not in out.getvalue()


def test_the_box_redraws_one_line_and_clears_it():
    out, waits = io.StringIO(), []
    cli._open_box(out, sleep=waits.append)
    assert out.getvalue().count("\r") == len(cli.BOX) + 2
    assert "\n" not in out.getvalue() and len(waits) == len(cli.BOX)


def test_python_dash_m_runs_the_command():
    done = subprocess.run(
        [sys.executable, "-m", "mordecai", "--version"], capture_output=True, text=True, cwd=ROOT
    )
    assert done.returncode == 0 and done.stdout.startswith("mordecai ")


def test_a_result_with_another_schema_version_is_refused():
    for doc in ({"schemaVersion": 2}, {}, []):
        with pytest.raises(ResultError, match="schemaVersion 1"):
            parse(doc)


def test_a_card_with_nothing_measured_prints_only_what_it_has():
    doc = make_result(same(6, [1, 1, 1], []), model=None)
    doc["suite"]["judgeModel"] = doc["claudeVersion"] = doc["startedAt"] = None
    doc["suite"]["plugins"] = []
    text = plain(build(parse(doc), b"x", roots=[]))
    assert text.startswith("unnamed: Invalid\n")
    assert "With " not in text and "Cost per run" not in text and "Fired in" not in text
    assert "  Tested on the default model\n" in text
    assert f"  Skill none{DOT}Cases none{DOT}" in text


def test_a_card_with_no_hashes_or_a_missing_skill(tmp_path):
    assert check({"card": 1}) == [
        "The card has no skill hash, so it can't be checked.",
        "The card has no cases hash, so it can't be checked.",
    ]
    doc = {"card": 1, "hashes": {"skill": "sha256:x", "cases": "sha256:y"}}
    doc["paths"] = {"skill": "gone", "casesRoot": ".", "caseDirs": ["evals/a"]}
    assert check(doc, tmp_path, roots=[tmp_path])[0] == "The skill directory gone is missing."


def test_lint_warnings_for_no_cases_empty_prompts_and_model_aliases(tmp_path):
    (tmp_path / "empty" / "evals").mkdir(parents=True)
    _, warnings = lint(tmp_path / "empty")
    assert warnings[0].startswith("No eval cases found under")
    case = tmp_path / "p" / "evals" / "c"
    (case / "graders").mkdir(parents=True)
    (case / "prompt.md").write_text("---\nmodel: sonnet\n---\n\n")
    (case / "graders" / "g.md").write_text("---\ntype: regex\n---\n")
    _, warnings = lint(tmp_path / "p")
    assert "Some cases set the model to an alias (sonnet), not a pinned ID." in warnings
    assert "1 case(s) have an empty prompt (c)." in warnings


def test_frontmatter_without_a_header_and_with_comments():
    assert frontmatter("just text\n") == ({}, "just text\n")
    fields, body = frontmatter("---\n# a comment\nname: a\n  stray: indented\n---\nbody\n")
    assert fields == {"name": "a"} and body == "body\n"
