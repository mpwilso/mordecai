"""Export the resolved library, one copy per skill, for tools that read other layouts.

--marketplace writes a Claude Code plugin marketplace an organization can host as a repository
and restrict and auto-install through managed settings: one plugin per skill, holding the copy
install would pick, byte for byte. --skills writes the same copies as plain <dir>/<skill>/
folders, the layout npx skills and APM read first.

Each copy is the one install would pick (the config's default variant, or the base) at its
newest release, and the install policy applies: a refused copy is left out and reported.
Both write mordecai-export.json beside the copies, with each one's source, commit, version and
verdict. A folder is written only if it is empty or holds a previous export.
"""

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from mordecai.library import LibraryError
from mordecai.library.install import _copy
from mordecai.library.skillmd import check_folder
from mordecai.library.sources import Library
from mordecai.provenance import hash_dir

EXPORT_NAME = "mordecai-export.json"
MARKETPLACE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
RESERVED_MARKETPLACES = {"claude-plugins-official", "agent-skills", "anthropic-agent-skills"}
RESERVED_PLUGIN_PREFIXES = ("claude-", "anthropic-")


@dataclass
class Exported:
    written: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _prepare(out: Path) -> None:
    if out.is_symlink():
        raise LibraryError(f"{out} is a symbolic link; Mordecai won't write through it")
    if out.exists():
        if not out.is_dir():
            raise LibraryError(f"{out} isn't a folder")
        names = set(os.listdir(out)) - {".git"}
        if names and EXPORT_NAME not in names:
            raise LibraryError(f"{out} isn't empty and doesn't hold a previous export")
        for name in names:
            path = out / name
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    out.mkdir(parents=True, exist_ok=True)


def _resolved(lib: Library, plugin_names: bool) -> tuple[list[tuple], list[str]]:
    picks, skipped = [], []
    for skill in lib.skills():
        variant = lib.default_variant(skill)
        try:
            if plugin_names and skill.startswith(RESERVED_PLUGIN_PREFIXES):
                raise LibraryError(f"{skill}: plugin names can't start with claude- or anthropic-")
            entry = lib.get(skill, variant)
            picked = lib.pick(entry)
            report = check_folder(picked.folder, skill)
            if report.errors:
                raise LibraryError(f"{entry.copy.label} isn't valid: {report.errors[0]}")
            evidence = lib.evidence(entry, picked)
            if evidence.blocked(lib.config.refuse):
                raise LibraryError(
                    f"{entry.copy.label} {picked.version} is refused: its "
                    f"evidence says {evidence.label}"
                )
        except LibraryError as e:
            skipped.append(str(e))
            continue
        picks.append((entry, picked, evidence, report))
    return picks, skipped


def _record(entry, picked, evidence, where: str) -> dict:
    return {
        "skill": entry.copy.skill,
        "variant": entry.copy.variant,
        "version": str(picked.version),
        "tag": picked.tag,
        "source": entry.source.spec.name,
        "commit": picked.commit,
        "verdict": evidence.label,
        "evidence": evidence.state,
        "hash": hash_dir(picked.folder),
        "path": where,
    }


def _description(entry, picked, evidence, report) -> str:
    text = str(report.fields.get("description", "")).strip()
    return f"{text} (Mordecai: {evidence.label}, {entry.copy.id} {picked.version})"


def _write_manifest(out: Path, kind: str, rows: list[dict], skipped: list[str]) -> None:
    doc = {"export": kind, "mordecaiExport": 1, "skills": rows, "skipped": skipped}
    (out / EXPORT_NAME).write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def export_skills(lib: Library, out: Path) -> Exported:
    picks, skipped = _resolved(lib, plugin_names=False)
    _prepare(out)
    result = Exported(skipped=skipped)
    for entry, picked, evidence, _ in picks:
        _copy(picked.folder, out / entry.copy.skill)
        result.written.append(_record(entry, picked, evidence, entry.copy.skill))
    _write_manifest(out, "skills", result.written, skipped)
    return result


def export_marketplace(lib: Library, out: Path, name: str, owner: str) -> Exported:
    if (
        not MARKETPLACE_NAME.fullmatch(name)
        or ".." in name
        or name in RESERVED_MARKETPLACES
        or name.startswith("claudeai-")
    ):
        raise LibraryError(f"{name!r} can't be a marketplace name")
    if not owner.strip():
        raise LibraryError("the marketplace needs an owner name")
    picks, skipped = _resolved(lib, plugin_names=True)
    _prepare(out)
    result = Exported(skipped=skipped)
    plugins = []
    for entry, picked, evidence, report in picks:
        skill = entry.copy.skill
        root = out / "plugins" / skill
        (root / ".claude-plugin").mkdir(parents=True)
        (root / "skills").mkdir()
        _copy(picked.folder, root / "skills" / skill)
        description = _description(entry, picked, evidence, report)
        manifest = {"name": skill, "version": str(picked.version), "description": description}
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        plugins.append(
            {
                "name": skill,
                "source": f"./plugins/{skill}",
                "description": description,
                "version": str(picked.version),
            }
        )
        result.written.append(_record(entry, picked, evidence, f"plugins/{skill}/skills/{skill}"))
    market = {
        "name": name,
        "owner": {"name": owner},
        "description": "Skills exported from a Mordecai library, with each version's verdict.",
        "plugins": plugins,
    }
    (out / ".claude-plugin").mkdir()
    (out / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(market, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    _write_manifest(out, "marketplace", result.written, skipped)
    return result
