"""Install, update and uninstall: copy one resolved skill folder, byte for byte, into the folder an
AI coding tool reads, and record it in the lockfile.

Every change is planned first and applied second, so the command line and the MCP server share
one path. A plan refuses what the policy refuses, a destination that Mordecai didn't install,
a destination that is a link, and a target outside the project. Replacing an installed folder
needs the caller to have seen the diff. Files are written into a temporary folder beside the
destination and renamed into place, then hashed again.
"""

import difflib
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from mordecai.library import LibraryError
from mordecai.library.evidence import Evidence
from mordecai.library.lock import LOCK_NAME, Lock
from mordecai.library.skillmd import check_folder, walk
from mordecai.library.sources import Library, Picked, Resolved
from mordecai.provenance import hash_dir, within

PROJECT_TARGETS = {
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "github": ".github/skills",
    "cursor": ".cursor/skills",
}
USER_TARGETS = {
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "github": ".copilot/skills",
    "cursor": ".cursor/skills",
}
ALIASES = {"codex": "agents", "copilot": "github"}
MAX_DIFF_LINES = 400


@dataclass(frozen=True)
class Project:
    root: Path
    lock_path: Path
    user: bool = False


def project(root: Path | None = None, user: bool = False) -> Project:
    if user:
        state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
        return Project(Path.home().resolve(), Path(state) / "mordecai" / "lock.json", True)
    root = (root or Path.cwd()).resolve()
    return Project(root, root / LOCK_NAME)


def _no_links(root: Path, path: Path) -> None:
    """Refuse if any existing folder from root down to path is a link."""
    rel = path.relative_to(root)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise LibraryError(f"{current} is a symbolic link; Mordecai won't install through it")


def target_dir(proj: Project, target: str) -> Path:
    """The skills folder a target names: a tool name, or a folder inside the project."""
    name = ALIASES.get(target, target)
    table = USER_TARGETS if proj.user else PROJECT_TARGETS
    if name in table:
        path = proj.root / table[name]
    else:
        path = Path(os.path.expanduser(target))
        path = path if path.is_absolute() else proj.root / path
        path = Path(os.path.normpath(path))
    if not within(path, proj.root) or path == proj.root:
        raise LibraryError(f"the target {target} isn't a folder inside {proj.root}")
    _no_links(proj.root, path)
    return path


def key_for(proj: Project, path: Path) -> str:
    return path.relative_to(proj.root).as_posix()


def files_of(folder: Path) -> dict[str, bytes]:
    files, errors, _ = walk(folder)
    if errors:
        raise LibraryError(f"{folder}: {errors[0]}")
    return {f: (folder / f).read_bytes() for f in files}


def diff(old: Path, new: Path, label: str) -> str:
    """A unified diff from old's files to new's, binary files named only."""
    a, b = files_of(old), files_of(new)
    out: list[str] = []
    for name in sorted(set(a) | set(b)):
        if a.get(name) == b.get(name):
            continue
        try:
            left = a[name].decode("utf-8").splitlines(keepends=True) if name in a else []
            right = b[name].decode("utf-8").splitlines(keepends=True) if name in b else []
        except UnicodeDecodeError:
            out.append(f"Binary file {label}/{name} differs\n")
            continue
        out += difflib.unified_diff(
            left,
            right,
            f"a/{label}/{name}" if name in a else "/dev/null",
            f"b/{label}/{name}" if name in b else "/dev/null",
        )
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
    if len(out) > MAX_DIFF_LINES:
        out = out[:MAX_DIFF_LINES] + [f"... {len(out) - MAX_DIFF_LINES} more lines\n"]
    return "".join(out)


@dataclass
class Destination:
    key: str
    path: Path
    existing: dict | None  # its lockfile entry, when it replaces one
    diff: str = ""
    same: bool = False  # already holds exactly these files


@dataclass
class Plan:
    entry: Resolved
    picked: Picked
    evidence: Evidence
    hash: str
    destinations: list[Destination]
    warnings: list[str] = field(default_factory=list)
    refused: str | None = None
    allowed: list[str] = field(default_factory=list)
    executable: bool = False

    @property
    def replaces(self) -> bool:
        return any(d.existing and not d.same for d in self.destinations)


def describe_source(entry: Resolved, proj: Project) -> dict:
    spec = entry.source.spec
    out = spec.describe()
    if spec.path is not None:
        p = spec.path.resolve()
        out["path"] = os.path.relpath(p, proj.root) if within(p, proj.root) else str(p)
    return out


def plan(
    lib: Library,
    proj: Project,
    lock: Lock,
    skill: str,
    variant: str | None = None,
    version: str | None = None,
    targets: list[str] | None = None,
    allow: list[str] | None = None,
    force: bool = False,
    exact: bool = False,
) -> Plan:
    """What installing skill would do. Without exact, a missing variant means the config's
    default variant for the skill, or the base."""
    if variant is None and not exact:
        variant = lib.default_variant(skill)
    entry = lib.get(skill, variant)
    picked = lib.pick(entry, version)
    report = check_folder(picked.folder, skill)
    if report.errors:
        raise LibraryError(
            f"{entry.copy.label} {picked.version} isn't a valid skill: {report.errors[0]}"
        )
    evidence = lib.evidence(entry, picked)
    allow = sorted(set(allow or []))
    refuse = [r for r in lib.config.refuse if r not in allow]
    p = Plan(entry, picked, evidence, hash_dir(picked.folder), [], allowed=allow)
    p.executable = report.executable
    label = f"{entry.copy.label} {picked.version}"
    if evidence.blocked(refuse):
        what = (
            evidence.verdict if evidence.applies and evidence.verdict in refuse else evidence.state
        )
        p.refused = (
            f"{label} is refused: its evidence says {what}"
            + (f" ({evidence.note})" if evidence.note else "")
            + f". Pass --allow {what} to install it anyway."
        )
    elif evidence.state == "unmeasured":
        p.warnings.append(f"{label} has no card, so nothing says whether it helps.")
    elif evidence.state == "stale":
        p.warnings.append(
            f"{label} has a card that says {evidence.verdict}, but it was made for other files."
        )
    elif evidence.state == "cases-changed":
        p.warnings.append(f"{label}: {evidence.note}.")
    if picked.tag is None:
        p.warnings.append(f"{label} has no release tag, so it was read at the source's ref.")
    if not entry.source.pinned:
        p.warnings.append(
            f"source {entry.source.spec.name!r} isn't a Git repository, so this "
            "install isn't pinned to a commit."
        )
    if p.executable:
        p.warnings.append(
            f"{skill} includes scripts or executable files. Mordecai never runs them, but your AI "
            "tool may run them with your permissions when it uses the skill. Read them first."
        )
    for w in report.warnings:
        p.warnings.append(f"{skill}: {w}")
    names = targets or ["agents"]
    if not proj.user and all(ALIASES.get(t, t) == "agents" for t in names):
        p.warnings.append(
            "Claude Code reads .claude/skills, not .agents/skills; add --target "
            "claude to install it there too."
        )
    seen = set()
    for t in names:
        path = target_dir(proj, t) / skill
        key = key_for(proj, path)
        if key in seen:
            continue
        seen.add(key)
        existing = lock.entries.get(key)
        d = Destination(key, path, existing)
        if path.is_symlink():
            raise LibraryError(
                f"{key} is a symbolic link (perhaps from another tool); Mordecai won't replace it"
            )
        if path.exists():
            if existing is None:
                raise LibraryError(
                    f"{key} already exists and Mordecai didn't install it. Remove it, or "
                    "pick another target."
                )
            current = hash_dir(path) if path.is_dir() else None
            if current != existing["hash"] and not force:
                raise LibraryError(
                    f"{key} has changed since Mordecai installed it (or another tool replaced "
                    "it). Pass --force to replace it anyway."
                )
            d.same = current == p.hash
            if not d.same:
                d.diff = diff(path, picked.folder, key)
        elif existing is not None:
            d.existing = None
        p.destinations.append(d)
    return p


def _copy(src: Path, dest: Path) -> None:
    files, errors, _ = walk(src)
    if errors:
        raise LibraryError(f"{src}: {errors[0]}")
    dest.mkdir()
    for rel in files:
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        data = (src / rel).read_bytes()
        fd = os.open(
            out,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o755 if os.stat(src / rel).st_mode & 0o111 else 0o644,
        )
        with os.fdopen(fd, "wb") as f:
            f.write(data)


def apply(p: Plan, proj: Project, lock: Lock) -> list[str]:
    """Write the plan's folders and the lockfile. Returns the keys written."""
    if p.refused:
        raise LibraryError(p.refused)
    written = []
    for d in p.destinations:
        if d.same:
            written.append(d.key)
            _record(p, proj, lock, d)
            continue
        parent = d.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        _no_links(proj.root, parent)
        tmp = Path(tempfile.mkdtemp(prefix=f".mordecai-{p.entry.copy.skill}-", dir=parent))
        try:
            staged = tmp / p.entry.copy.skill
            _copy(p.picked.folder, staged)
            if hash_dir(staged) != p.hash:
                raise LibraryError(
                    f"the copy for {d.key} doesn't match its source; nothing was installed"
                )
            old = None
            if d.path.exists():
                old = tmp / "old"
                os.replace(d.path, old)
            os.replace(staged, d.path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if hash_dir(d.path) != p.hash:
            raise LibraryError(f"{d.key} doesn't match its source after writing")
        _record(p, proj, lock, d)
        written.append(d.key)
    lock.save()
    return written


def _record(p: Plan, proj: Project, lock: Lock, d: Destination) -> None:
    e = p.evidence
    lock.entries[d.key] = {
        "skill": p.entry.copy.skill,
        "variant": p.entry.copy.variant,
        "version": str(p.picked.version),
        "tag": p.picked.tag,
        "source": describe_source(p.entry, proj),
        "commit": p.picked.commit,
        "path": p.entry.copy.folder,
        "hash": p.hash,
        "verdict": e.label,
        "evidence": e.state,
        "allowed": [a for a in p.allowed if e.blocked([a])],
    }


@dataclass
class Removal:
    key: str
    path: Path
    entry: dict


def plan_uninstall(
    proj: Project, lock: Lock, skill: str, targets: list[str] | None = None, force: bool = False
) -> list[Removal]:
    entries = lock.for_skill(skill)
    if targets:
        keys = {key_for(proj, target_dir(proj, t) / skill) for t in targets}
        entries = {k: e for k, e in entries.items() if k in keys}
    if not entries:
        raise LibraryError(
            f"Mordecai's lockfile has no install of {skill}"
            + (" in those targets" if targets else "")
        )
    out = []
    for key, entry in entries.items():
        path = proj.root / key
        if not within(path, proj.root):
            raise LibraryError(f"the lockfile entry {key!r} leads outside {proj.root}")
        _no_links(proj.root, path.parent)
        if path.is_symlink():
            raise LibraryError(f"{key} is a symbolic link; Mordecai won't remove it")
        if path.exists() and not force and hash_dir(path) != entry["hash"]:
            raise LibraryError(
                f"{key} has changed since Mordecai installed it. Pass --force to remove it anyway."
            )
        out.append(Removal(key, path, entry))
    return out


def apply_uninstall(removals: list[Removal], lock: Lock) -> list[str]:
    for r in removals:
        if r.path.exists():
            shutil.rmtree(r.path)
        lock.entries.pop(r.key, None)
    lock.save()
    return [r.key for r in removals]


@dataclass
class Update:
    key: str
    entry: dict
    plan: Plan | None = None
    problem: str | None = None

    @property
    def available(self) -> bool:
        return self.plan is not None and self.plan.replaces


def plan_updates(
    lib: Library, proj: Project, lock: Lock, skill: str | None = None, force: bool = False
) -> list[Update]:
    """For each locked install (of skill, if given), the plan that would bring it to the newest
    release of the same copy."""
    out = []
    for key, entry in sorted(lock.entries.items()):
        if skill and entry["skill"] != skill:
            continue
        u = Update(key, entry)
        try:
            target = str(Path(key).parent)
            p = plan(
                lib,
                proj,
                lock,
                entry["skill"],
                entry["variant"],
                None,
                [target],
                entry.get("allowed"),
                force,
                exact=True,
            )
            if not p.destinations or p.destinations[0].key != key:
                raise LibraryError(f"{key} isn't where {entry['skill']} would install")
            u.plan = p
        except LibraryError as e:
            u.problem = str(e)
        out.append(u)
    return out
