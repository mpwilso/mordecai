"""Branches the main tests don't reach: bad lockfiles, bad layouts, a release outside Git, a
status that meets an untrustworthy tag, and the hand-off when the library extra is missing."""

import importlib.util
import io
import json

import pytest

from mordecai.cli import main


def run(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


@pytest.mark.skipif(importlib.util.find_spec("strictyaml") is not None, reason="extra installed")
def test_library_commands_say_how_to_get_the_extra(capsys):
    assert run(["library", "list"])[0] == 2
    assert run(["mcp"])[0] == 2
    assert "uv sync --extra library" in capsys.readouterr().err


needs_extra = pytest.mark.skipif(
    importlib.util.find_spec("strictyaml") is None, reason="needs the library extra"
)


@needs_extra
@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"lockfileVersion": 2, "installed": {}}',
        '{"lockfileVersion": 1, "installed": []}',
        "[1, 2]",
    ],
)
def test_bad_lockfiles_are_refused_with_a_reason(tmp_path, text, capsys):
    (tmp_path / "mordecai-lock.json").write_text(text)
    assert run(["library", "uninstall", "x", "--project", str(tmp_path)])[0] == 2
    assert "mordecai-lock.json" in capsys.readouterr().err


@needs_extra
def test_a_lockfile_that_is_a_link_is_refused(tmp_path, capsys):
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"lockfileVersion": 1, "installed": {}}))
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "mordecai-lock.json").symlink_to(real)
    assert run(["library", "uninstall", "x", "--project", str(proj)])[0] == 2
    assert "is a link" in capsys.readouterr().err


@needs_extra
def test_bad_layouts_are_reported(gitenv, monkeypatch):
    from libkit import write_copy

    root = gitenv / "plain"
    write_copy(root, "greeting")
    (root / "library" / "Bad_Name").mkdir()
    (root / "library" / "greeting" / "variants" / "base").mkdir(parents=True)
    (root / "library" / "greeting" / "variants" / "Upper").mkdir()
    monkeypatch.chdir(root)
    code, text = run(["library", "validate"])
    assert code == 1
    assert "'Bad_Name' isn't a valid skill name" in text
    assert "'base' isn't a valid variant name" in text
    assert "'Upper' isn't a valid variant name" in text
    code, _ = run(["library", "validate", "--library", "nowhere"])
    assert code == 2


@needs_extra
def test_release_and_fork_need_a_git_repository(gitenv, capsys):
    from libkit import write_copy

    root = gitenv / "plain"
    write_copy(root, "greeting")
    for argv in (
        ["library", "release", "greeting", "--bump", "major", "--library", str(root / "library")],
        ["library", "fork", "greeting", "--variant", "x", "--library", str(root / "library")],
        ["library", "release", "nope", "--bump", "major", "--library", str(gitenv / "nowhere")],
    ):
        assert run(argv)[0] == 2
    assert "isn't in a Git repository" in capsys.readouterr().err


@needs_extra
def test_status_reports_an_untrustworthy_tag_instead_of_failing(gitenv):
    from libkit import git, greeting_library

    repo = greeting_library(gitenv / "lib")
    git(repo, "tag", "-a", "skill/greeting@9.0.0", "-m", "a tag whose changelog says 1.1.0")
    cfg = gitenv / "c.toml"
    cfg.write_text(f'[[source]]\nname = "org"\npath = "{repo}"\n')
    code, text = run(["library", "status", "--config", str(cfg), "--project", str(gitenv)])
    assert code == 1
    assert "won't trust it" in text
    code, text = run(["library", "list", "--config", str(cfg)])
    assert code == 0 and "error: tag skill/greeting@9.0.0" in text


@needs_extra
def test_show_prints_a_skill_that_isnt_utf8_without_failing(gitenv):
    from libkit import commit, git, init, write_copy

    from mordecai.library import catalog
    from mordecai.library.sources import Library, parse_config

    repo = init(gitenv / "lib")
    write_copy(repo, "greeting")
    (repo / "library/greeting/base/greeting/SKILL.md").write_bytes(
        b"---\nname: greeting\ndescription: \xff\n---\nx\n"
    )
    commit(repo)
    git(repo, "rev-parse", "HEAD")
    doc = {"source": [{"name": "s", "path": str(repo)}]}
    with Library(parse_config(doc, None, gitenv)) as lib:
        d = catalog.show(lib, "greeting", None, None)
    assert "isn't UTF-8" in " ".join(d["problems"])
    assert d["text"].startswith("---\nname: greeting")
