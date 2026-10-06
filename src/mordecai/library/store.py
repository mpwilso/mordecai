"""The layout of a library on disk, and the checks `validate` runs on it.

    library/<skill>/base/<skill>/                  the base's skill folder
    library/<skill>/base/CHANGELOG.md
    library/<skill>/base/evidence/<X.Y.Z>/         card.json and result.json
    library/<skill>/variants/<variant>/<skill>/    a variant's skill folder
    library/<skill>/variants/<variant>/CHANGELOG.md

A copy is the base or one variant. Its skill folder is what gets installed; everything beside
it is bookkeeping and is never installed.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from mordecai.library import LibraryError
from mordecai.library import changelog as cl
from mordecai.library.skillmd import Report, check_folder
from mordecai.library.versions import RESERVED_VARIANTS, ZERO, copy_id, valid_name

ALLOWED_IN_COPY = {"CHANGELOG.md", "evidence"}


@dataclass(frozen=True)
class Copy:
    skill: str
    variant: str | None
    path: str  # the copy's folder, POSIX, relative to the source root: library/<skill>/base

    @property
    def id(self) -> str:
        return copy_id(self.skill, self.variant)

    @property
    def folder(self) -> str:
        """The skill folder, relative to the source root."""
        return f"{self.path}/{self.skill}"

    @property
    def label(self) -> str:
        return f"{self.skill} (variant {self.variant})" if self.variant else f"{self.skill} (base)"


def copy_path(library: str, skill: str, variant: str | None) -> str:
    lib = PurePosixPath(library)
    return (lib / skill / "variants" / variant if variant else lib / skill / "base").as_posix()


def _dirs(path: Path) -> list[str]:
    if not path.is_dir() or path.is_symlink():
        return []
    with os.scandir(path) as it:
        return sorted(e.name for e in it if e.is_dir(follow_symlinks=False))


def scan(root: Path, library: str = "library") -> tuple[list[Copy], list[str]]:
    """Every copy under root/library, and the problems with the layout itself. A skill may have
    variants and no base here: a team library can hold variants of an org's skill."""
    lib = root / library
    problems: list[str] = []
    copies: list[Copy] = []
    if lib.is_symlink() or not lib.is_dir():
        return [], [f"there is no {library}/ folder"]
    for skill in _dirs(lib):
        where = f"{library}/{skill}"
        if not valid_name(skill):
            problems.append(f"{where}: {skill!r} isn't a valid skill name")
            continue
        found = set(_dirs(lib / skill))
        if "base" in found:
            copies.append(Copy(skill, None, copy_path(library, skill, None)))
        for variant in _dirs(lib / skill / "variants"):
            if not valid_name(variant) or variant in RESERVED_VARIANTS:
                problems.append(f"{where}/variants: {variant!r} isn't a valid variant name")
                continue
            copies.append(Copy(skill, variant, copy_path(library, skill, variant)))
        for extra in sorted(found - {"base", "variants"}):
            problems.append(f"{where}/{extra}: only base/ and variants/ belong here")
    return copies, problems


def read_changelog(root: Path, copy: Copy) -> cl.Changelog:
    path = root / copy.path / "CHANGELOG.md"
    if path.is_symlink() or not path.is_file():
        raise LibraryError(f"{copy.path}/CHANGELOG.md is missing")
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as e:
        raise LibraryError(f"{copy.path}/CHANGELOG.md isn't UTF-8 text") from e
    return cl.parse(text, copy.variant is not None, f"{copy.path}/CHANGELOG.md")


@dataclass
class CopyCheck:
    copy: Copy
    report: Report
    log: cl.Changelog | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def all_errors(self) -> list[str]:
        return self.errors + self.report.errors


def check_copy(root: Path, copy: Copy, base_log: cl.Changelog | None = None) -> CopyCheck:
    """Everything wrong with one copy: its skill folder, its changelog, its stamps, the files
    beside it, and (for a variant, given the base's changelog) its lineage."""
    report = check_folder(root / copy.folder, copy.skill)
    out = CopyCheck(copy, report)
    beside = set(os.listdir(root / copy.path)) - {copy.skill}
    for extra in sorted(beside - ALLOWED_IN_COPY):
        out.errors.append(f"{copy.path}/{extra}: only the skill folder, CHANGELOG.md and evidence/")
    try:
        out.log = read_changelog(root, copy)
    except LibraryError as e:
        out.errors.append(str(e))
        return out
    log = out.log
    stamps = report.stamps
    if stamps:
        want = {"mordecai-version": str(log.version)}
        if copy.variant:
            want["mordecai-variant"] = copy.variant
            if log.based_on:
                want["mordecai-based-on"] = f"{copy.skill}@{log.based_on}"
        for key in sorted(set(stamps) | set(want)):
            if key not in want:
                out.errors.append(f"{copy.id}: SKILL.md has {key}, which a base can't have")
            elif stamps.get(key) != want[key]:
                out.errors.append(
                    f"{copy.id}: SKILL.md's {key} is {stamps.get(key)!r}, but the changelog "
                    f"says {want[key]!r}"
                )
    if copy.variant and base_log is not None:
        released = {s.version for s in base_log.releases}
        for s in (log.unreleased, *log.releases):
            if s is not None and s.based_on is not None and s.based_on not in released:
                what = "Unreleased" if s.version is None else str(s.version)
                out.errors.append(
                    f"{copy.id}: its {what} section is based on base {s.based_on}, which the "
                    "base never released"
                )
    evidence = root / copy.path / "evidence"
    if evidence.is_dir() and not evidence.is_symlink():
        versions = {str(s.version) for s in log.releases}
        for name in sorted(os.listdir(evidence)):
            if name not in versions:
                out.errors.append(f"{copy.path}/evidence/{name}: not a released version")
    if log.version == ZERO and not log.unreleased:
        out.errors.append(f"{copy.id}: the changelog has no release and no Unreleased section")
    return out
