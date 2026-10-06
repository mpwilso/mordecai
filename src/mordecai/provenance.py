"""Hashes that tie a card to exactly what was tested: the skill's files, the eval cases, and the
result file. If any of them changes, the card is stale.

A directory's hash covers every file's path relative to the directory and its bytes, in sorted
path order, so it doesn't depend on timestamps, permissions or the order the disk lists files.

Symbolic links are never followed. A link is hashed as its path and the text of its target, so
retargeting a link changes the hash, but changing the file a link points to does not. That
keeps the hash inside the directory: a skill under review can't make Mordecai read, or hang on,
a file somewhere else. Pipes, sockets and devices are left out, and never opened.

Paths that come from a result or a card are checked before anything is read: case directories
must be relative and stay inside the cases' root, and PathError says which one didn't.
"""

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

SKIP_DIRS = {".git", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache", "results"}
CHUNK = 1 << 20


class PathError(Exception):
    """A path from a result or a card points outside where Mordecai will read."""


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def within(path: Path, root: Path) -> bool:
    """Whether path, with every link resolved, is root or inside it."""
    path, root = path.resolve(), root.resolve()
    return path == root or root in path.parents


def _entries(root: Path, skip_top: set[str]) -> list[tuple[str, str]]:
    """(relative path, kind) for every regular file and link under root, links not followed."""
    out = []

    def walk(directory: Path, prefix: str) -> None:
        with os.scandir(directory) as it:
            for e in it:
                if e.name in SKIP_DIRS or (not prefix and e.name in skip_top):
                    continue
                rel = prefix + e.name
                mode = e.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    out.append((rel, "link"))
                elif stat.S_ISDIR(mode):
                    walk(Path(e.path), rel + "/")
                elif stat.S_ISREG(mode):
                    out.append((rel, "file"))

    walk(root, "")
    return sorted(out)


def hash_dir(root: Path, skip_top: set[str] = frozenset()) -> str:
    h = hashlib.sha256()
    for rel, kind in _entries(root, set(skip_top)):
        path = root / rel
        h.update(rel.encode() + b"\0")
        if kind == "link":
            h.update(b"\0symlink\0" + os.fsencode(os.readlink(path)))
        else:
            with open(path, "rb") as f:
                while chunk := f.read(CHUNK):
                    h.update(chunk)
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def check_case_dir(d: str) -> str:
    """d, if it is a relative path that stays below the directory it's relative to."""
    if not isinstance(d, str) or not d:
        raise PathError(f"a case directory should be a non-empty string, not {d!r}")
    for flavor in (PurePosixPath, PureWindowsPath):
        p = flavor(d)
        if p.is_absolute() or p.drive or p.root or ".." in p.parts or not p.parts:
            raise PathError(f"the case directory {d!r} isn't a relative path inside the suite")
    return d


def eval_dirs(case_dirs: list[str]) -> set[str]:
    """The top-level directories that hold the cases, such as evals/, so the skill's hash
    leaves them out: changing a case shouldn't look like changing the skill."""
    return {PurePosixPath(check_case_dir(d)).parts[0] for d in case_dirs}


def hash_skill(plugin_dir: Path, case_dirs: list[str]) -> str:
    return hash_dir(plugin_dir, eval_dirs(case_dirs))


def hash_cases(root: Path, case_dirs: list[str]) -> str | None:
    """One hash over every case directory, in name order. None if any is missing. A case
    directory that is a link out of root is a PathError."""
    h = hashlib.sha256()
    for d in sorted(case_dirs):
        path = root / check_case_dir(d)
        if path.exists() and not within(path, root):
            raise PathError(f"the case directory {d!r} leads outside {root}")
        if not path.is_dir():
            return None
        h.update(d.encode() + b"\0" + hash_dir(path).encode() + b"\0")
    return "sha256:" + h.hexdigest()


def skill_names(plugin_dir: Path) -> list[str]:
    skills = plugin_dir / "skills"
    if not skills.is_dir():
        return []
    return sorted(p.name for p in skills.iterdir() if (p / "SKILL.md").is_file())
