"""Hashes that tie a card to exactly what was tested: the skill's files, the eval cases, and the
result file. If any of them changes, the card is stale.

A directory's hash covers every file's path relative to the directory and its bytes, in sorted
path order, so it doesn't depend on timestamps, permissions or the order the disk lists files.
"""

import hashlib
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache", "results"}


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _files(root: Path, skip_top: set[str]) -> list[Path]:
    out = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if rel.parts[0] in skip_top or any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.is_file():
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def hash_dir(root: Path, skip_top: set[str] = frozenset()) -> str:
    h = hashlib.sha256()
    for p in _files(root, set(skip_top)):
        h.update(p.relative_to(root).as_posix().encode() + b"\0")
        h.update(p.read_bytes() + b"\0")
    return "sha256:" + h.hexdigest()


def eval_dirs(case_dirs: list[str]) -> set[str]:
    """The top-level directories that hold the cases, such as evals/, so the skill's hash
    leaves them out: changing a case shouldn't look like changing the skill."""
    return {Path(d).parts[0] for d in case_dirs if d and Path(d).parts}


def hash_skill(plugin_dir: Path, case_dirs: list[str]) -> str:
    return hash_dir(plugin_dir, eval_dirs(case_dirs))


def hash_cases(root: Path, case_dirs: list[str]) -> str | None:
    """One hash over every case directory, in name order. None if any is missing."""
    h = hashlib.sha256()
    for d in sorted(case_dirs):
        path = root / d
        if not path.is_dir():
            return None
        h.update(d.encode() + b"\0" + hash_dir(path).encode() + b"\0")
    return "sha256:" + h.hexdigest()


def skill_names(plugin_dir: Path) -> list[str]:
    skills = plugin_dir / "skills"
    if not skills.is_dir():
        return []
    return sorted(p.name for p in skills.iterdir() if (p / "SKILL.md").is_file())
