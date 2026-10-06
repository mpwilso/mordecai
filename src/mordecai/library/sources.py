"""Where skills come from: the config file, each source read at one commit, and the rule that
decides which copy wins when several sources have it.

The rule: each copy (a skill's base, or one named variant) is looked up in every source, and the
source listed last wins. List sources broad to narrow, org then team then personal, and a
narrower source overrides a broader one copy by copy. A shadowed copy is reported, never used,
never merged.

A Git source is read at a commit, from Git objects, into a temporary folder: never from a
working tree. A local folder that isn't a Git repository is read as it is, and is unpinned.
"""

import os
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from mordecai.library import LibraryError, gitio
from mordecai.library import changelog as cl
from mordecai.library.evidence import DEFAULT_REFUSE, STATES, Evidence, assess, cases_dir
from mordecai.library.store import Copy, read_changelog, scan
from mordecai.library.versions import TAG_PREFIX, Version, check_name, parse_tag, tag_name
from mordecai.provenance import within
from mordecai.verdict import VERDICTS

CONFIG_NAME = "mordecai-library.toml"
TARGET_NAMES = ("agents", "claude", "github", "cursor")
DEFAULT_TARGETS = ("agents", "claude", "github")


@dataclass(frozen=True)
class SourceSpec:
    name: str
    github: str | None = None
    path: Path | None = None
    ref: str | None = None
    library: str = "library"
    written: str | None = None  # the path as the config wrote it, before resolving

    def describe(self) -> dict:
        """The source as the lockfile and export record it: a GitHub repository, or a local
        path as the config wrote it, so no machine's folder names end up in either."""
        if self.github:
            where = {"github": self.github}
        else:
            where = {"path": self.written if self.written is not None else str(self.path)}
        extra = {"ref": self.ref} if self.ref else {}
        if self.library != "library":
            extra["library"] = self.library
        return {"name": self.name, **where, **extra}


@dataclass(frozen=True)
class Config:
    path: Path | None
    sources: tuple[SourceSpec, ...]
    variants: dict = field(default_factory=dict)
    refuse: tuple[str, ...] = DEFAULT_REFUSE
    targets: tuple[str, ...] = DEFAULT_TARGETS


def find_config(explicit: Path | None, cwd: Path) -> Path | None:
    if explicit is not None:
        return explicit
    env = os.environ.get("MORDECAI_LIBRARY_CONFIG")
    if env:
        return Path(env)
    if (cwd / CONFIG_NAME).is_file():
        return cwd / CONFIG_NAME
    home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    user = Path(home) / "mordecai" / "library.toml"
    return user if user.is_file() else None


def _keys(table: dict, allowed: set[str], where: str) -> None:
    extra = sorted(set(table) - allowed)
    if extra:
        raise LibraryError(f"{where}: unknown key(s) {', '.join(extra)}")


def _text(table: dict, key: str, where: str) -> str | None:
    value = table.get(key)
    if value is not None and (not isinstance(value, str) or not value):
        raise LibraryError(f"{where}: {key} should be non-empty text")
    return value


def _subpath(value: str, where: str) -> str:
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "\\" in value or not p.parts:
        raise LibraryError(f"{where}: library should be a relative folder inside the source")
    return p.as_posix()


def parse_config(doc: dict, path: Path | None, base: Path) -> Config:
    where = str(path) if path else "the config"
    _keys(doc, {"source", "variants", "policy", "install"}, where)
    raw = doc.get("source", [])
    if not isinstance(raw, list) or not all(isinstance(s, dict) for s in raw):
        raise LibraryError(f"{where}: [[source]] should be a list of tables")
    sources, names = [], set()
    for i, s in enumerate(raw, start=1):
        at = f"{where}, source {i}"
        _keys(s, {"name", "github", "path", "ref", "library"}, at)
        name = check_name(_text(s, "name", at), "source")
        if name in names:
            raise LibraryError(f"{at}: two sources are named {name!r}")
        names.add(name)
        github, local = _text(s, "github", at), _text(s, "path", at)
        if bool(github) == bool(local):
            raise LibraryError(f"{at}: give exactly one of github or path")
        if local is not None:
            p = Path(os.path.expanduser(local))
            local = p if p.is_absolute() else base / p
        sources.append(
            SourceSpec(
                name=name,
                github=github,
                path=local,
                ref=_text(s, "ref", at),
                library=_subpath(_text(s, "library", at) or "library", at),
                written=_text(s, "path", at),
            )
        )
    variants = doc.get("variants", {})
    if not isinstance(variants, dict):
        raise LibraryError(f"{where}: [variants] should map skills to variant names")
    for skill, variant in variants.items():
        check_name(skill)
        check_name(variant, "variant")
    policy = doc.get("policy", {})
    if not isinstance(policy, dict):
        raise LibraryError(f"{where}: [policy] should be a table")
    _keys(policy, {"refuse"}, f"{where}, [policy]")
    refuse = policy.get("refuse", list(DEFAULT_REFUSE))
    known = set(VERDICTS) | set(STATES)
    if not isinstance(refuse, list) or not all(isinstance(r, str) and r in known for r in refuse):
        raise LibraryError(
            f"{where}: [policy] refuse should list verdicts or states from "
            f"{', '.join(sorted(known))}"
        )
    install = doc.get("install", {})
    if not isinstance(install, dict):
        raise LibraryError(f"{where}: [install] should be a table")
    _keys(install, {"targets"}, f"{where}, [install]")
    targets = install.get("targets", list(DEFAULT_TARGETS))
    if not isinstance(targets, list) or not all(t in TARGET_NAMES for t in targets):
        raise LibraryError(
            f"{where}: [install] targets should list names from {', '.join(TARGET_NAMES)}"
        )
    if not sources:
        sources = [SourceSpec(name="local", path=base)]
    return Config(path, tuple(sources), dict(variants), tuple(refuse), tuple(targets))


def load_config(explicit: Path | None = None, cwd: Path | None = None) -> Config:
    """The config, or one local source for cwd when there is no config file."""
    cwd = cwd or Path.cwd()
    path = find_config(explicit, cwd)
    if path is None:
        return Config(None, (SourceSpec(name="local", path=cwd),))
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise LibraryError(f"can't read the config {path}: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise LibraryError(f"{path} isn't valid TOML: {e}") from e
    return parse_config(doc, path, path.resolve().parent)


@dataclass(frozen=True)
class Release:
    version: Version
    tag: str
    commit: str
    date: str


@dataclass
class Picked:
    """One version of a copy, ready to read: root holds copy.path at that version."""

    copy: Copy
    version: Version
    tag: str | None
    commit: str | None
    root: Path
    log: cl.Changelog

    @property
    def folder(self) -> Path:
        return self.root / self.copy.folder


class Snapshot:
    """One source, read at one commit (or as a plain folder) into a work folder."""

    def __init__(self, spec: SourceSpec, work: Path, budget: list[int]):
        self.spec, self.work, self.budget = spec, work, budget
        self.repo: Path | None = None
        self.sha: str | None = None
        self.prefix = ""
        self._done: set[str] = set()
        self._versions: dict[str, Path] = {}
        self._releases: dict[str, list[Release]] = {}
        if spec.github:
            self.repo, self.sha = gitio.fetch_github(spec.github, spec.ref)
        else:
            path = spec.path
            if path is None or not path.is_dir():
                raise LibraryError(f"source {spec.name!r}: {path} isn't a folder")
            if gitio.is_repo(path):
                self.repo = gitio.toplevel(path)
                rel = os.path.relpath(path.resolve(), self.repo.resolve())
                self.prefix = "" if rel == "." else PurePosixPath(Path(rel).as_posix()).as_posix()
                if self.prefix.startswith(".."):
                    raise LibraryError(f"source {spec.name!r}: can't place {path} in its repo")
                self.sha = gitio.resolve(self.repo, spec.ref or "HEAD")
            elif spec.ref:
                raise LibraryError(f"source {spec.name!r}: a ref needs a Git repository")
        if self.repo is None:
            self.root = spec.path.resolve()
        else:
            self.root = work / "tree"
            self.root.mkdir(parents=True)
            self.ensure(self.library)
        self.tags = self._tags()

    @property
    def library(self) -> str:
        return f"{self.prefix}/{self.spec.library}" if self.prefix else self.spec.library

    @property
    def pinned(self) -> bool:
        return self.sha is not None

    def ensure(self, rel: str) -> None:
        """Make sure the files under rel (relative to the repository root) are on disk."""
        if self.repo is None or rel in self._done:
            return
        gitio.materialize(self.repo, self.sha, rel, self.root, self.budget)
        self._done.add(rel)

    def _tags(self) -> dict[str, list[Release]]:
        if self.repo is None:
            return {}
        out: dict[str, list[Release]] = {}
        for t in gitio.library_tags(self.repo, within=self.sha):
            parsed = parse_tag(t.name)
            if parsed:
                skill, variant, version = parsed
                key = tag_name(skill, variant, version).rsplit("@", 1)[0]
                out.setdefault(key, []).append(Release(version, t.name, t.commit, t.date))
        for releases in out.values():
            releases.sort(key=lambda r: r.version, reverse=True)
        return out

    def releases(self, copy: Copy) -> list[Release]:
        """The copy's release tags, newest first. A tag counts only if its commit has this copy's
        changelog, since two libraries in one repository share one set of tags."""
        if copy.id not in self._releases:
            self._releases[copy.id] = [
                r
                for r in self.tags.get(f"{TAG_PREFIX}{copy.id}", [])
                if gitio.has_path(self.repo, r.commit, f"{copy.path}/CHANGELOG.md")
            ]
        return self._releases[copy.id]

    def at(self, commit: str, copy: Copy) -> Path:
        """A root holding copy.path as it is in commit."""
        key = f"{commit}:{copy.path}"
        if key not in self._versions:
            root = self.work / "at" / str(len(self._versions))
            root.mkdir(parents=True)
            gitio.materialize(self.repo, commit, copy.path, root, self.budget)
            self._versions[key] = root
        return self._versions[key]


@dataclass
class Resolved:
    """The copy that wins for one entry, and the sources it shadows."""

    copy: Copy
    source: Snapshot
    shadowed: list[str] = field(default_factory=list)
    _log: cl.Changelog | None = None
    error: str | None = None

    @property
    def log(self) -> cl.Changelog | None:
        if self._log is None and self.error is None:
            try:
                self._log = read_changelog(self.source.root, self.copy)
            except LibraryError as e:
                self.error = str(e)
        return self._log


class Library:
    """Every source in a config, resolved. Use as a context manager: the work folder holding
    the sources' files is removed on exit."""

    def __init__(self, config: Config):
        self.config = config
        self._tmp = tempfile.TemporaryDirectory(prefix="mordecai-library-")
        work = Path(self._tmp.name)
        self.budget = [gitio.MAX_TREE_BYTES]
        self.snapshots: list[Snapshot] = []
        self.problems: list[str] = []
        self.entries: dict[tuple[str, str | None], Resolved] = {}
        try:
            for i, spec in enumerate(config.sources):
                snap = Snapshot(spec, work / str(i), self.budget)
                self.snapshots.append(snap)
                copies, problems = scan(snap.root, snap.library)
                self.problems += [f"source {spec.name!r}: {p}" for p in problems]
                for copy in copies:
                    key = (copy.skill, copy.variant)
                    earlier = self.entries.get(key)
                    shadowed = [*earlier.shadowed, earlier.source.spec.name] if earlier else []
                    self.entries[key] = Resolved(copy, snap, shadowed)
        except BaseException:
            self._tmp.cleanup()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def skills(self) -> list[str]:
        return sorted({skill for skill, _ in self.entries})

    def copies(self, skill: str) -> list[Resolved]:
        base = [self.entries[(skill, None)]] if (skill, None) in self.entries else []
        variants = sorted(
            (r for (s, v), r in self.entries.items() if s == skill and v is not None),
            key=lambda r: r.copy.variant,
        )
        return base + variants

    def get(self, skill: str, variant: str | None) -> Resolved:
        check_name(skill)
        if variant is not None:
            check_name(variant, "variant")
        found = self.entries.get((skill, variant))
        if found is None:
            if not any(s == skill for s, _ in self.entries):
                raise LibraryError(f"no source has a skill named {skill!r}")
            names = [r.copy.variant or "base" for r in self.copies(skill)]
            raise LibraryError(
                f"{skill} has no {'variant ' + repr(variant) if variant else 'base'}; "
                f"it has {', '.join(names)}"
            )
        return found

    def default_variant(self, skill: str) -> str | None:
        return self.config.variants.get(skill)

    def pick(self, entry: Resolved, version: str | None = None) -> Picked:
        """The version to read: the given one (a release tag must exist), else the newest release
        the source's ref contains, else the copy as it is at the ref, untagged."""
        snap, copy = entry.source, entry.copy
        releases = snap.releases(copy)
        if version is not None:
            wanted = next((r for r in releases if str(r.version) == version), None)
            if wanted is None:
                known = ", ".join(str(r.version) for r in releases) or "none"
                raise LibraryError(f"{copy.label} has no release {version}; releases: {known}")
            releases = [wanted]
        if releases:
            r = releases[0]
            root = snap.at(r.commit, copy)
            log = read_changelog(root, copy)
            if log.version != r.version:
                raise LibraryError(
                    f"tag {r.tag} points at a commit whose changelog says {log.version}, so "
                    "Mordecai won't trust it"
                )
            return Picked(copy, r.version, r.tag, r.commit, root, log)
        log = entry.log
        if log is None:
            raise LibraryError(entry.error or f"{copy.label} has no changelog")
        return Picked(copy, log.version, None, snap.sha, snap.root, log)

    def evidence(self, entry: Resolved, picked: Picked) -> Evidence:
        snap = entry.source
        card_dir = snap.root / entry.copy.path / "evidence" / str(picked.version)
        cases = cases_dir(card_dir)
        if cases is not None and within(cases, snap.root):
            rel = Path(os.path.relpath(cases, snap.root)).as_posix()
            if not rel.startswith(".."):
                try:
                    snap.ensure(rel)
                except LibraryError:
                    pass
        return assess(card_dir, picked.folder, snap.root)
