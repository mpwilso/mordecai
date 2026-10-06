"""CHANGELOG.md beside each stored copy: the record of its versions and, for a variant, the
base version each release is based on.

    # Changelog

    ## Unreleased

    Based on base 1.2.0.

    - What changed since the last release.

    ## 1.1.0 - 2026-10-06

    Based on base 1.2.0.

    - What changed.

The newest release heading is the copy's version; a copy with no release is 0.0.0. Releases
must be newest first. "Based on base X.Y.Z." is required in every section of a variant's
changelog and not allowed in a base's. `release` writes this form; `validate` reads it.
"""

import datetime
import re
from dataclasses import dataclass, replace

from mordecai.library import LibraryError
from mordecai.library.versions import ZERO, Version, parse_version

TITLE = "# Changelog"
UNRELEASED = "## Unreleased"
HEADING = re.compile(r"## (?P<version>\S+) - (?P<date>\d{4}-\d{2}-\d{2})")
BASED_ON = re.compile(r"Based on base (?P<version>\S+)\.")
MAX_BYTES = 1 << 20


@dataclass(frozen=True)
class Section:
    version: Version | None  # None for Unreleased
    date: str | None
    based_on: Version | None
    notes: tuple[str, ...]  # the section's other lines, blank lines at either end trimmed


@dataclass(frozen=True)
class Changelog:
    unreleased: Section | None
    releases: tuple[Section, ...]  # newest first

    @property
    def version(self) -> Version:
        return self.releases[0].version if self.releases else ZERO

    @property
    def based_on(self) -> Version | None:
        """The lineage of the copy as it is now: Unreleased's, else the newest release's."""
        for s in (self.unreleased, *self.releases[:1]):
            if s is not None and s.based_on is not None:
                return s.based_on
        return None

    def release(self, version: Version) -> Section | None:
        return next((s for s in self.releases if s.version == version), None)


def _trim(lines: list[str]) -> tuple[str, ...]:
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return tuple(lines)


def parse(text: str, variant: bool, where: str = "CHANGELOG.md") -> Changelog:
    """The changelog in text. A LibraryError names the first line that doesn't fit the form."""
    if len(text.encode("utf-8", "surrogatepass")) > MAX_BYTES:
        raise LibraryError(f"{where} is over 1 MB")
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].rstrip() != TITLE:
        raise LibraryError(f"{where} should start with the line {TITLE!r}")
    sections: list[tuple[int, str, list[str]]] = []
    for n, line in enumerate(lines[1:], start=2):
        if line.startswith("## "):
            sections.append((n, line.rstrip(), []))
        elif line.startswith("#"):
            raise LibraryError(f"{where} line {n}: only ## headings are allowed after the title")
        elif sections:
            sections[-1][2].append(line.rstrip())
        elif line.strip():
            raise LibraryError(f"{where} line {n}: text before the first ## heading")
    unreleased, releases = None, []
    for n, heading, body in sections:
        if heading == UNRELEASED:
            if unreleased is not None or releases:
                raise LibraryError(f"{where} line {n}: Unreleased must come first, and once")
            version, date = None, None
        else:
            m = HEADING.fullmatch(heading)
            if not m:
                raise LibraryError(
                    f"{where} line {n}: a heading should be '## Unreleased' or "
                    f"'## X.Y.Z - YYYY-MM-DD', not {heading!r}"
                )
            try:
                version = parse_version(m["version"])
            except LibraryError as e:
                raise LibraryError(f"{where} line {n}: in the heading, {e}") from e
            date = m["date"]
            try:
                datetime.date.fromisoformat(date)
            except ValueError as e:
                raise LibraryError(f"{where} line {n}: {date} isn't a date") from e
            if releases and not version < releases[-1].version:
                raise LibraryError(f"{where} line {n}: releases must be listed newest first")
        notes = list(_trim(body))
        based_on = None
        if notes and BASED_ON.fullmatch(notes[0].strip()):
            based_on = parse_version(BASED_ON.fullmatch(notes[0].strip())["version"])
            notes = list(_trim(notes[1:]))
        what = "Unreleased" if version is None else str(version)
        if variant and based_on is None:
            raise LibraryError(
                f"{where}: the {what} section of a variant should start with 'Based on base X.Y.Z.'"
            )
        if not variant and based_on is not None:
            raise LibraryError(f"{where}: a base's changelog can't say what it is based on")
        section = Section(version, date, based_on, tuple(notes))
        if version is None:
            unreleased = section
        else:
            releases.append(section)
    return Changelog(unreleased, tuple(releases))


def render(log: Changelog) -> str:
    out = [TITLE]
    for s in (log.unreleased, *log.releases):
        if s is None:
            continue
        out += ["", UNRELEASED if s.version is None else f"## {s.version} - {s.date}"]
        body = ([f"Based on base {s.based_on}."] if s.based_on else []) + list(s.notes)
        if s.based_on and s.notes:
            body.insert(1, "")
        if body:
            out += ["", *body]
    return "\n".join(out) + "\n"


def new(based_on: Version | None, notes: list[str]) -> Changelog:
    return Changelog(Section(None, None, based_on, tuple(notes)), ())


def cut_release(
    log: Changelog, version: Version, date: str, based_on: Version | None, notes: list[str]
) -> Changelog:
    """The changelog with Unreleased (plus notes) moved under a new release heading."""
    pending = list(log.unreleased.notes) if log.unreleased else []
    pending += [n if n.startswith("- ") else f"- {n}" for n in notes]
    if not any(line.strip() for line in pending):
        raise LibraryError(
            "nothing to release: add notes under '## Unreleased' in the changelog, or pass --note"
        )
    section = Section(version, date, based_on, _trim(pending))
    unreleased = Section(None, None, based_on, ())
    return replace(log, unreleased=unreleased, releases=(section, *log.releases))
