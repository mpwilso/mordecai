"""What no tracked file may hold: a local home folder (results, cards and docs use paths relative
to the repository, or placeholders such as $DEMO), or an em or en dash."""

import subprocess

import pytest
from conftest import ROOT


def tracked() -> list[str]:
    done = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True)
    if done.returncode != 0:
        pytest.skip("not a Git checkout")
    return [p for p in done.stdout.decode().split("\0") if p]


# Built from parts so this file doesn't match itself.
MARKERS = [b"/" + b"home/", b"/" + b"Users/", b"C:" + b"\\" + b"Users"]


def test_no_tracked_file_has_a_home_folder_path():
    bad = []
    for rel in tracked():
        path = ROOT / rel
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if any(m in data for m in MARKERS):
                bad.append(rel)
    assert bad == []


def test_no_tracked_file_has_an_em_or_en_dash():
    dashes = [chr(0x2014).encode(), chr(0x2013).encode()]
    bad = []
    for rel in tracked():
        path = ROOT / rel
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if any(d in data for d in dashes):
                bad.append(rel)
    assert bad == []
