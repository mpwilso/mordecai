"""Path checks shared by the library: everything that reads from a source or writes to a target
goes through these, so a crafted name, link or lockfile can't lead outside where it should.
They build on the engine's within(), which resolves every link."""

import os
import re
import unicodedata
from pathlib import Path, PurePosixPath

from mordecai.library import LibraryError

# Control characters and the backslash: a backslash is a separator on Windows, so a name like
# ..\..\x would escape there even though it is one ordinary file name on Linux.
BAD_TEXT = re.compile(r"[\x00-\x1f\x7f\\]")
DRIVE = re.compile(r"^[A-Za-z]:")


def no_links(root: Path, path: Path) -> None:
    """Refuse if any existing folder from root down to path (path included) is a link. path
    must be root or below it, spelled without links."""
    rel = Path(os.path.normpath(path)).relative_to(Path(os.path.normpath(root)))
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise LibraryError(f"{current} is a symbolic link; Mordecai won't go through it")


def relative(text: str, what: str) -> PurePosixPath:
    """text as a relative POSIX path with no '..', backslash, drive or control character."""
    p = PurePosixPath(text) if isinstance(text, str) else None
    if (
        p is None
        or not text
        or BAD_TEXT.search(text)
        or DRIVE.match(text)
        or p.is_absolute()
        or ".." in p.parts
    ):
        raise LibraryError(f"{what} {text!r} isn't a relative path Mordecai will use")
    return p


def fold(name: str) -> str:
    """The form two file names share if a case-insensitive or normalizing file system (macOS,
    Windows) would treat them as one."""
    return unicodedata.normalize("NFC", name).casefold()


def open_new(path: Path, mode: int = 0o644) -> int:
    """A file descriptor for a new file at path, never following a link and never replacing a
    file that is already there."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags, mode)
