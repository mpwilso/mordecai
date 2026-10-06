"""show and search: what a reader or an MCP client sees for one copy."""

import io
import json

import pytest

pytest.importorskip("strictyaml")

from libkit import greeting_library  # noqa: E402

from mordecai.cli import main  # noqa: E402
from mordecai.library import LibraryError, catalog  # noqa: E402
from mordecai.library.sources import Library, parse_config  # noqa: E402


@pytest.fixture
def lib(gitenv):
    repo = greeting_library(gitenv / "lib")
    with Library(
        parse_config({"source": [{"name": "org", "path": str(repo)}]}, None, gitenv)
    ) as lib:
        yield lib


def test_show_gives_text_files_lineage_and_verdict(lib):
    d = catalog.show(lib, "greeting", "formal", None)
    assert d["files"] == ["SKILL.md"] and "Say good day" in d["text"]
    assert d["basedOn"] == "1.0.0" and d["behindBase"] == "1.1.0"
    assert d["evidence"]["state"] == "unmeasured"
    old = catalog.show(lib, "greeting", None, "1.0.0")
    assert "warmly" not in old["text"] and old["tag"] == "skill/greeting@1.0.0"


def test_search_matches_every_word(lib):
    assert {c["id"] for c in catalog.search(lib, "greeting")} == {
        "greeting",
        "greeting.brief",
        "greeting.formal",
    }
    assert [c["id"] for c in catalog.search(lib, "formal greeting")] == ["greeting.formal"]
    assert catalog.search(lib, "nothing-like-this") == []
    with pytest.raises(LibraryError):
        catalog.search(lib, "  ")


def test_show_command_prints_through_clean(gitenv, monkeypatch):
    repo = greeting_library(gitenv / "lib")
    monkeypatch.chdir(repo)
    out = io.StringIO()
    assert main(["library", "show", "greeting", "--json"], out=out) == 0
    assert json.loads(out.getvalue())["version"] == "1.1.0"
    out = io.StringIO()
    assert main(["library", "show", "greeting"], out=out) == 0
    assert out.getvalue().startswith("greeting 1.1.0: unmeasured\n")
