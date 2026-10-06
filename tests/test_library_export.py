"""Exporting the resolved library as a Claude Code marketplace and as plain skill folders."""

import io
import json

import pytest

pytest.importorskip("strictyaml")

from libkit import add_card, commit, greeting_library  # noqa: E402

from mordecai.cli import main  # noqa: E402
from mordecai.library import LibraryError  # noqa: E402
from mordecai.library.export import export_marketplace, export_skills  # noqa: E402
from mordecai.library.sources import Library, parse_config  # noqa: E402
from mordecai.provenance import hash_dir  # noqa: E402


@pytest.fixture
def repo(gitenv):
    repo = greeting_library(gitenv / "lib")
    add_card(repo, repo / "library/greeting/variants/brief", "1.0.0", "hurts")
    commit(repo, "card")
    return repo


def lib_for(repo, variants=None):
    doc = {"source": [{"name": "org", "path": str(repo)}], "variants": variants or {}}
    return Library(parse_config(doc, None, repo.parent))


def test_marketplace_layout_and_byte_identical_skills(repo, gitenv):
    out = gitenv / "market"
    with lib_for(repo, {"greeting": "formal"}) as lib:
        r = export_marketplace(lib, out, "acme-skills", "Acme")
    market = json.loads((out / ".claude-plugin/marketplace.json").read_text())
    assert market["name"] == "acme-skills" and market["owner"] == {"name": "Acme"}
    [plugin] = market["plugins"]
    assert plugin["name"] == "greeting" and plugin["source"] == "./plugins/greeting"
    assert plugin["version"] == "1.0.0"
    assert "Mordecai: unmeasured, greeting.formal 1.0.0" in plugin["description"]
    manifest = json.loads((out / "plugins/greeting/.claude-plugin/plugin.json").read_text())
    assert manifest["name"] == "greeting" and manifest["version"] == "1.0.0"
    exported = out / "plugins/greeting/skills/greeting"
    assert hash_dir(exported) == hash_dir(repo / "library/greeting/variants/formal/greeting")
    record = json.loads((out / "mordecai-export.json").read_text())
    assert record["skills"][0]["variant"] == "formal" and r.skipped == []


def test_refused_copies_are_left_out_and_reported(repo, gitenv):
    out = gitenv / "market"
    with lib_for(repo, {"greeting": "brief"}) as lib:
        r = export_marketplace(lib, out, "acme", "Acme")
    assert r.written == [] and "hurts" in r.skipped[0]
    assert json.loads((out / ".claude-plugin/marketplace.json").read_text())["plugins"] == []


def test_reserved_names_and_non_empty_folders(repo, gitenv):
    with lib_for(repo) as lib:
        for bad in ("claude-plugins-official", "agent-skills", "claudeai-x", "-x", "a..b"):
            with pytest.raises(LibraryError):
                export_marketplace(lib, gitenv / "m", bad, "Acme")
        busy = gitenv / "busy"
        busy.mkdir()
        (busy / "keep.txt").write_text("mine")
        with pytest.raises(LibraryError, match="isn't empty"):
            export_skills(lib, busy)
        assert (busy / "keep.txt").exists()
        export_skills(lib, gitenv / "flat")
        export_skills(lib, gitenv / "flat")  # a previous export may be replaced
    assert (gitenv / "flat/greeting/SKILL.md").is_file()
    assert json.loads((gitenv / "flat/mordecai-export.json").read_text())["export"] == "skills"


def test_export_command(repo, gitenv, monkeypatch):
    monkeypatch.chdir(repo)
    out = io.StringIO()
    code = main(
        [
            "library",
            "export",
            "--marketplace",
            str(gitenv / "m"),
            "--name",
            "acme",
            "--owner",
            "Acme",
        ],
        out=out,
    )
    assert code == 0
    assert "Wrote 1 skill(s)" in out.getvalue()
