"""docs/library-demo.md shows real output. This replays every command in it and checks that each
prints exactly what the doc shows, so the doc can't drift from the code. It needs the library's
release tags, which a clone without them doesn't have."""

import io
import re
import subprocess

import pytest
from conftest import ROOT

pytest.importorskip("strictyaml")

from mordecai.cli import main  # noqa: E402

DOC = (ROOT / "docs" / "library-demo.md").read_text(encoding="utf-8")


def blocks() -> list[tuple[str, str]]:
    """(command, shown output) for every ``` block that starts with a $ line, after Setup."""
    body = DOC.split("## List", 1)[1]
    out = []
    for block in re.findall(r"```\n(\$ [^\n]+)\n(.*?)```", body, re.S):
        out.append((block[0][2:], block[1]))
    return out


def tagged() -> bool:
    done = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list", "skill/*"], capture_output=True, text=True
    )
    return done.returncode == 0 and bool(done.stdout.strip())


@pytest.mark.skipif(not tagged(), reason="needs the library's skill/ tags")
def test_every_demo_command_prints_what_the_doc_shows(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("MORDECAI_LIBRARY_CONFIG", "examples/library.toml")
    demo = tmp_path / "demo"
    demo.mkdir()
    shown = blocks()
    assert len(shown) >= 12
    for command, expected in shown:
        argv = command.replace("$DEMO", str(demo)).split()
        if argv[0] == "cat":
            got = open(argv[1], encoding="utf-8").read()
        else:
            assert argv[:3] == ["uv", "run", "mordecai"], command
            args = [a.strip('"') for a in argv[3:]]
            if "--owner" in args:  # the one quoted argument with a space
                i = args.index("--owner")
                args[i + 1 : i + 3] = [" ".join(args[i + 1 : i + 3])]
            out = io.StringIO()
            main(args, out=out)
            got = out.getvalue()
        assert got.replace(str(demo), "$DEMO") == expected, command
