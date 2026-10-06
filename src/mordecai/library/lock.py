"""mordecai-lock.json: what Mordecai installed, where from, and the hash of what it wrote.

One entry per installed folder, keyed by its path relative to the project (or the home folder,
for --user installs). JSON with sorted keys and no timestamps, so it merges cleanly. Mordecai
never reads or writes another tool's lockfile.
"""

import json
import os
import tempfile
from pathlib import Path

from mordecai.library import LibraryError
from mordecai.result import ResultError, read_json

LOCK_NAME = "mordecai-lock.json"
LOCK_VERSION = 1
FIELDS = {
    "skill": str,
    "variant": (str, type(None)),
    "version": str,
    "tag": (str, type(None)),
    "source": dict,
    "commit": (str, type(None)),
    "path": str,
    "hash": str,
    "verdict": str,
    "evidence": str,
    "allowed": list,
}


class Lock:
    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[str, dict] = {}
        if path.exists() or path.is_symlink():
            self._read()

    def _read(self) -> None:
        if self.path.is_symlink():
            raise LibraryError(f"{self.path} is a link; Mordecai won't follow it")
        try:
            doc, _ = read_json(self.path, "a Mordecai lockfile")
        except ResultError as e:
            raise LibraryError(str(e)) from e
        if not isinstance(doc, dict) or doc.get("lockfileVersion") != LOCK_VERSION:
            raise LibraryError(f"{self.path} isn't a Mordecai lockfile, version {LOCK_VERSION}")
        installed = doc.get("installed")
        if not isinstance(installed, dict):
            raise LibraryError(f"{self.path}: installed should be an object")
        for key, entry in installed.items():
            if not isinstance(entry, dict) or any(
                not isinstance(entry.get(f), kind) for f, kind in FIELDS.items()
            ):
                raise LibraryError(f"{self.path}: the entry for {key!r} is malformed")
        self.entries = installed

    def save(self) -> None:
        doc = {"lockfileVersion": LOCK_VERSION, "installed": self.entries}
        text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".mordecai-lock-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def for_skill(self, skill: str) -> dict[str, dict]:
        return {k: e for k, e in sorted(self.entries.items()) if e["skill"] == skill}
