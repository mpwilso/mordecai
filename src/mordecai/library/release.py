"""Author commands, run in the library's own repository: release a copy, and fork a variant.

release moves the Unreleased notes under a new version heading, updates the copy's version
stamps if it has them, commits the copy's folder, and creates an annotated tag on that commit.
It refuses if anything outside the copy's folder has uncommitted changes, so the release commit
holds only that copy. It never pushes.
"""

import datetime
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mordecai.library import LibraryError, gitio
from mordecai.library import changelog as cl
from mordecai.library.skillmd import check_folder, set_stamps
from mordecai.library.store import Copy, check_copy, copy_path, read_changelog
from mordecai.library.versions import BUMPS, check_name, parse_version, tag_name


@dataclass(frozen=True)
class Released:
    tag: str
    commit: str
    version: str


def _repo_and_library(library_dir: Path) -> tuple[Path, str]:
    if not library_dir.is_dir():
        raise LibraryError(f"{library_dir} isn't a folder")
    if not gitio.is_repo(library_dir):
        raise LibraryError(f"{library_dir} isn't in a Git repository")
    repo = gitio.toplevel(library_dir).resolve()
    rel = os.path.relpath(library_dir.resolve(), repo)
    if rel.startswith(".."):
        raise LibraryError(f"{library_dir} isn't inside its repository")
    return repo, Path(rel).as_posix()


def _copy(library: str, skill: str, variant: str | None, repo: Path) -> Copy:
    check_name(skill)
    if variant is not None:
        check_name(variant, "variant")
    copy = Copy(skill, variant, copy_path(library, skill, variant))
    if not (repo / copy.folder / "SKILL.md").is_file():
        raise LibraryError(f"{copy.folder}/SKILL.md doesn't exist")
    return copy


def _dirty_outside(repo: Path, inside: str) -> list[str]:
    out = gitio.git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    paths = []
    items = out.split("\0")
    i = 0
    while i < len(items):
        item = items[i]
        i += 1
        if len(item) < 4:
            continue
        status, path = item[:2], item[3:]
        if status[0] in "RC":
            i += 1  # the rename's source path follows
        if not (path == inside or path.startswith(inside + "/")):
            paths.append(path)
    return paths


def release(
    library_dir: Path,
    skill: str,
    variant: str | None,
    bump: str,
    based_on: str | None = None,
    notes: list[str] | None = None,
    message: str | None = None,
    today: datetime.date | None = None,
) -> Released:
    if bump not in BUMPS:
        raise LibraryError(f"--bump should be one of {', '.join(BUMPS)}")
    if based_on and variant is None:
        raise LibraryError("--based-on is only for variants")
    repo, library = _repo_and_library(library_dir)
    copy = _copy(library, skill, variant, repo)
    dirty = _dirty_outside(repo, copy.path)
    if dirty:
        raise LibraryError(
            f"commit or stash changes outside {copy.path} first: {', '.join(dirty[:5])}"
        )
    log = read_changelog(repo, copy)
    version = log.version.bump(bump)
    tag = tag_name(skill, variant, version)
    if gitio.git(repo, "tag", "--list", tag).strip():
        raise LibraryError(f"the tag {tag} already exists")
    lineage = None
    base_log = None
    if variant is not None:
        base_log = read_changelog(repo, Copy(skill, None, copy_path(library, skill, None)))
        lineage = parse_version(based_on) if based_on else log.based_on
        if lineage is None or base_log.release(lineage) is None:
            raise LibraryError(f"base {skill} has no release {lineage}; pass --based-on")
    date = (today or datetime.date.today()).isoformat()
    new_log = cl.cut_release(log, version, date, lineage, notes or [])
    log_path = repo / copy.path / "CHANGELOG.md"
    md_path = repo / copy.folder / "SKILL.md"
    old_log, old_md = log_path.read_bytes(), md_path.read_bytes()
    report = check_folder(repo / copy.folder, skill)
    try:
        log_path.write_text(cl.render(new_log), encoding="utf-8", newline="\n")
        if report.stamps:
            stamps = {"mordecai-version": str(version)}
            if variant:
                stamps["mordecai-variant"] = variant
                stamps["mordecai-based-on"] = f"{skill}@{lineage}"
            md_path.write_text(
                set_stamps(old_md.decode("utf-8"), stamps), encoding="utf-8", newline="\n"
            )
        checked = check_copy(repo, copy, base_log)
        if checked.all_errors:
            raise LibraryError(f"{copy.id} wouldn't be valid: {checked.all_errors[0]}")
    except BaseException:
        log_path.write_bytes(old_log)
        md_path.write_bytes(old_md)
        raise
    subject = f"Release {tag}"
    body = "\n".join(new_log.releases[0].notes)
    gitio.git(repo, "add", "-A", "--", copy.path)
    args = ["commit", "--quiet", "-m", subject, "-m", body]
    if message:
        args += ["-m", message]
    gitio.git(repo, *args, "--", copy.path)
    commit = gitio.resolve(repo, "HEAD")
    gitio.git(repo, "tag", "-a", tag, "-m", f"{copy.id} {version}\n\n{body}", commit)
    return Released(tag, commit, str(version))


def fork(library_dir: Path, skill: str, variant: str) -> Path:
    """Create variants/<variant>/ from the base's newest release. Writes files; commits nothing."""
    repo, library = _repo_and_library(library_dir)
    base = _copy(library, skill, None, repo)
    check_name(variant, "variant")
    dest = repo / copy_path(library, skill, variant)
    if dest.exists() or dest.is_symlink():
        raise LibraryError(f"{dest.relative_to(repo).as_posix()} already exists")
    log = read_changelog(repo, base)
    if not log.releases:
        raise LibraryError(f"base {skill} has no release to fork from; release it first")
    version = log.version
    tag = tag_name(skill, None, version)
    commit = next((t.commit for t in gitio.library_tags(repo) if t.name == tag), None)
    if commit is None:
        raise LibraryError(f"the tag {tag} doesn't exist, so the release can't be read")
    with tempfile.TemporaryDirectory() as tmp:
        gitio.materialize(repo, commit, base.folder, Path(tmp), [gitio.MAX_TREE_BYTES])
        src = Path(tmp) / base.folder
        report = check_folder(src, skill)
        if report.errors:
            raise LibraryError(f"base {skill} {version} isn't valid: {report.errors[0]}")
        dest.mkdir(parents=True)
        shutil.copytree(src, dest / skill)
    md = dest / skill / "SKILL.md"
    if report.stamps:
        stamps = {
            "mordecai-version": "0.0.0",
            "mordecai-variant": variant,
            "mordecai-based-on": f"{skill}@{version}",
        }
        md.write_text(
            set_stamps(md.read_text(encoding="utf-8"), stamps), encoding="utf-8", newline="\n"
        )
    new_log = cl.new(version, [f"- Forked from base {version}."])
    (dest / "CHANGELOG.md").write_text(cl.render(new_log), encoding="utf-8", newline="\n")
    return dest
