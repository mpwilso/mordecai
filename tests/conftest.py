import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from builder import make_result, same  # noqa: E402,F401


@pytest.fixture
def gitenv(tmp_path, monkeypatch):
    """Git with a test identity and no global config, and Mordecai's caches in tmp_path."""
    from libkit import isolate_git

    isolate_git(monkeypatch, tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _no_github(monkeypatch, tmp_path_factory):
    """No test reaches github.com: GitHub sources point at a folder that doesn't exist unless a
    test points them at a local stand-in."""
    try:
        from mordecai.library import gitio
    except ImportError:
        return
    monkeypatch.setattr(gitio, "GITHUB", (tmp_path_factory.getbasetemp() / "no-github").as_uri())
