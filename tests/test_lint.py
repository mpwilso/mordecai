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


def broken_plugin(tmp_path, name):
    import shutil

    plugin = tmp_path / name
    shutil.copytree(FIXTURES / "probe", plugin)
    return plugin, plugin / "evals" / "goodbye" / "prompt.md"


def test_unreadable_case_files_exit_2_naming_the_file(tmp_path, capsys):
    import os

    cases = {
        "utf8": lambda p, prompt: prompt.write_bytes(b"---\nname: x\n---\n\xff\n"),
        "runs": lambda p, prompt: prompt.write_text("---\nruns: abc\n---\nhi\n"),
        "zero-runs": lambda p, prompt: prompt.write_text("---\nruns: 0\n---\nhi\n"),
        "json": lambda p, prompt: (p / ".claude-plugin" / "plugin.json").write_text("{"),
        "link": lambda p, prompt: (
            prompt.unlink(),
            (tmp_path / "outside.md").write_text("---\nmodel: secret\n---\n"),
            os.symlink(tmp_path / "outside.md", prompt),
        ),
    }
    for name, breakage in cases.items():
        plugin, prompt = broken_plugin(tmp_path, name)
        breakage(plugin, prompt)
        assert main(["lint", str(plugin)], out=io.StringIO()) == 2, name
        err = capsys.readouterr().err
        assert err.startswith("mordecai: ") and name in err, name
        assert "secret" not in err
    assert main(["lint", str(tmp_path / "missing")], out=io.StringIO()) == 2
    assert "isn't a directory" in capsys.readouterr().err


def test_one_broken_plugin_does_not_hide_the_others(tmp_path):
    plugin, prompt = broken_plugin(tmp_path, "broken")
    prompt.write_text("---\nruns: abc\n---\nhi\n")
    out = io.StringIO()
    assert main(["lint", str(plugin), str(FIXTURES / "probe")], out=out) == 2
    assert "3 warning(s)" in out.getvalue()


def test_a_manifest_that_is_not_an_object_falls_back_to_the_directory_name(tmp_path):
    from mordecai.lint import plugin_name

    plugin, _ = broken_plugin(tmp_path, "listy")
    (plugin / ".claude-plugin" / "plugin.json").write_text("[1]")
    assert plugin_name(plugin) == "listy"
