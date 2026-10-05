"""Every Python file is ASCII. Characters outside it are built with chr()."""

from conftest import ROOT


def test_python_sources_are_ascii():
    files = [*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py"), *ROOT.glob("scripts/*.py")]
    assert files
    bad = [p.relative_to(ROOT).as_posix() for p in files if not p.read_bytes().isascii()]
    assert bad == []
