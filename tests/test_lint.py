"""mordecai lint runs the card's case-quality warnings on case files, before an eval."""

import io

from conftest import FIXTURES

from mordecai.cli import main
from mordecai.lint import frontmatter, lint


def test_frontmatter():
    fields, body = frontmatter(
        "---\nname: a\nruns: 3\nallowed_tools: [Read, Skill]\npattern: '\\d+ x'\n"
        "append_system_prompt: |\n  line one\n\n  line two\nmax: 0\n---\n\nThe prompt.\n"
    )
    assert fields == {
        "name": "a",
        "runs": 3,
        "allowed_tools": ["Read", "Skill"],
        "pattern": "\\d+ x",
        "append_system_prompt": "line one\n\nline two",
        "max": 0,
    }
    assert body.strip() == "The prompt."


def test_the_probe_gets_the_same_case_warnings_as_its_card():
    _, warnings = lint(FIXTURES / "probe")
    assert warnings[0] == "Only 1 case(s) would be compared; the rules need at least 5."
    assert any("ran 1 time(s) per side" in w for w in warnings)
    assert any("stays quiet" in w for w in warnings)


def test_a_case_that_only_checks_firing_is_flagged(tmp_path):
    plugin = tmp_path / "p"
    (plugin / "skills" / "s").mkdir(parents=True)
    (plugin / "skills" / "s" / "SKILL.md").write_text("---\nname: s\n---\n")
    for i in range(5):
        g = plugin / "evals" / f"c{i}" / "graders"
        g.mkdir(parents=True)
        (g.parent / "prompt.md").write_text("---\nname: c\n---\n\nDo the thing.\n")
        (g / "fired.md").write_text("---\ntype: tool_used\ntool: Skill\n---\n")
    _, warnings = lint(plugin)
    assert any("only check that the skill fired" in w for w in warnings)


def test_lint_exit_codes():
    out = io.StringIO()
    assert main(["lint", str(FIXTURES / "probe")], out=out) == 1
    assert out.getvalue().startswith(
        f"{FIXTURES / 'probe'}: 1 cases (1 compared, 0 quiet), 3 warning(s)"
    )
