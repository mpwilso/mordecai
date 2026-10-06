"""Every commit hash the docs cite still names a commit in this repository."""

import re
import subprocess

import pytest
from conftest import ROOT

CITED = re.compile(r"\b(?:commit|commits|at|in) ([0-9a-f]{7,40})\b")


def shallow() -> bool:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        text=True,
    )
    return out.returncode != 0 or out.stdout.strip() != "false"


@pytest.mark.skipif(shallow(), reason="needs the full history (CI fetches it)")
def test_cited_commits_resolve():
    docs = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    cited = {h for d in docs for h in CITED.findall(d.read_text(encoding="utf-8"))}
    assert len(cited) >= 5
    for h in sorted(cited):
        done = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{h}^{{commit}}"])
        assert done.returncode == 0, h
