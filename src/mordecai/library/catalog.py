"""What the library holds, as plain data: listing, one copy's details, its history, a search, and
the status report. The command line prints these and the MCP server returns them, so both say
the same thing.
"""

import re

from mordecai.library import LibraryError
from mordecai.library.evidence import Evidence
from mordecai.library.lock import Lock
from mordecai.library.skillmd import check_folder, frontmatter
from mordecai.library.sources import Library, Resolved
from mordecai.library.store import check_copy
from mordecai.provenance import hash_dir


def _evidence(e: Evidence) -> dict:
    out = {"verdict": e.label, "state": e.state}
    if e.verdict and not e.applies:
        out["cardVerdict"] = e.verdict
    if e.model:
        out["model"] = e.model
    if e.note:
        out["note"] = e.note
    return out


def _base_version(lib: Library, skill: str):
    base = lib.entries.get((skill, None))
    return base.log.version if base is not None and base.log is not None else None


def summary(lib: Library, r: Resolved) -> dict:
    """One copy, at the version install would pick."""
    copy = r.copy
    out = {
        "id": copy.id,
        "skill": copy.skill,
        "variant": copy.variant,
        "source": r.source.spec.name,
        "shadows": list(r.shadowed),
    }
    log = r.log
    if log is None:
        out["error"] = r.error
        return out
    if copy.variant and log.based_on is not None:
        out["basedOn"] = str(log.based_on)
        base = _base_version(lib, copy.skill)
        if base is not None and log.based_on < base:
            out["behindBase"] = str(base)
    try:
        picked = lib.pick(r)
    except LibraryError as e:
        out["error"] = str(e)
        return out
    out["version"] = str(picked.version)
    out["tag"] = picked.tag
    out["evidence"] = _evidence(lib.evidence(r, picked))
    try:
        fields, _ = frontmatter((picked.folder / "SKILL.md").read_text(encoding="utf-8"))
        out["description"] = str(fields.get("description", ""))
    except (LibraryError, OSError, UnicodeDecodeError):
        out["description"] = ""
    return out


def listing(lib: Library) -> list[dict]:
    return [
        {
            "skill": skill,
            "default": lib.default_variant(skill),
            "copies": [summary(lib, r) for r in lib.copies(skill)],
        }
        for skill in lib.skills()
    ]


def search(lib: Library, query: str) -> list[dict]:
    """Copies whose skill name, variant or description contains every word of query."""
    words = [w for w in re.split(r"\W+", query.lower()) if w]
    if not words:
        raise LibraryError("give at least one word to search for")
    out = []
    for item in listing(lib):
        for c in item["copies"]:
            text = " ".join([c["skill"], c.get("variant") or "", c.get("description", "")]).lower()
            if all(w in text for w in words):
                out.append(c)
    return out


def show(lib: Library, skill: str, variant: str | None, version: str | None) -> dict:
    r = lib.get(skill, variant)
    picked = lib.pick(r, version)
    report = check_folder(picked.folder, skill)
    out = (
        summary(lib, r)
        if version is None
        else {
            "id": r.copy.id,
            "skill": skill,
            "variant": variant,
            "source": r.source.spec.name,
            "version": str(picked.version),
            "tag": picked.tag,
            "evidence": _evidence(lib.evidence(r, picked)),
        }
    )
    out.update(
        version=str(picked.version),
        tag=picked.tag,
        commit=picked.commit,
        path=r.copy.folder,
        files=report.files,
        problems=report.errors,
        warnings=report.warnings,
        executable=report.executable,
        text=(picked.folder / "SKILL.md").read_text(encoding="utf-8")
        if not report.errors or "SKILL.md" in report.files
        else "",
    )
    return out


def history(lib: Library, skill: str, variant: str | None) -> dict:
    r = lib.get(skill, variant)
    log = r.log
    if log is None:
        raise LibraryError(r.error or f"{r.copy.label} has no changelog")
    tags = {str(t.version): t for t in r.source.releases(r.copy)}
    versions = []
    for s in log.releases:
        v = str(s.version)
        row = {"version": v, "date": s.date, "notes": list(s.notes)}
        if s.based_on is not None:
            row["basedOn"] = str(s.based_on)
        t = tags.get(v)
        if t is None:
            row["tag"] = None
            row["evidence"] = {"verdict": "untagged", "state": "untagged"}
        else:
            row.update(tag=t.tag, commit=t.commit, tagDate=t.date)
            try:
                row["evidence"] = _evidence(lib.evidence(r, lib.pick(r, v)))
            except LibraryError as e:
                row["evidence"] = {"verdict": "broken", "state": "broken", "note": str(e)}
        versions.append(row)
    for v in sorted(set(tags) - {str(s.version) for s in log.releases}):
        versions.append(
            {
                "version": v,
                "tag": tags[v].tag,
                "commit": tags[v].commit,
                "note": "tagged, but not in the changelog",
            }
        )
    pending = list(log.unreleased.notes) if log.unreleased else []
    return {
        "id": r.copy.id,
        "skill": skill,
        "variant": variant,
        "source": r.source.spec.name,
        "unreleased": pending,
        "versions": versions,
    }


def status(lib: Library, proj=None, lock: Lock | None = None) -> list[dict]:
    """Everything worth acting on: variants behind their base, unreleased or untagged changes,
    versions with no card or a stale, broken or refused one, shadowed copies, layout problems,
    and installs that changed or have an update."""
    found = [{"kind": "layout", "message": p} for p in lib.problems]

    def add(kind: str, r: Resolved, message: str) -> None:
        found.append(
            {"kind": kind, "copy": r.copy.id, "source": r.source.spec.name, "message": message}
        )

    for skill in lib.skills():
        base = lib.entries.get((skill, None))
        for r in lib.copies(skill):
            if r.shadowed:
                add(
                    "shadowed",
                    r,
                    f"{r.copy.label} from {r.source.spec.name!r} shadows the copy "
                    f"in {', '.join(repr(s) for s in r.shadowed)}",
                )
            checked = check_copy(
                r.source.root, r.copy, base.log if base and r.copy.variant else None
            )
            for e in checked.all_errors:
                add("invalid", r, e)
            log = r.log
            if log is None:
                continue
            s = summary(lib, r)
            if "behindBase" in s:
                add(
                    "behind-base",
                    r,
                    f"{r.copy.label} is based on base {s['basedOn']}; the base "
                    f"is at {s['behindBase']}",
                )
            releases = r.source.releases(r.copy)
            tagged = {str(t.version) for t in releases}
            for sec in log.releases:
                if r.source.pinned and str(sec.version) not in tagged:
                    add(
                        "untagged",
                        r,
                        f"{r.copy.label} {sec.version} is in the changelog but has no tag",
                    )
            if releases:
                newest = lib.pick(r)
                if hash_dir(newest.folder) != hash_dir(r.source.root / r.copy.folder):
                    add("unreleased", r, f"{r.copy.label} has changes since {newest.version}")
            if "error" in s:
                add("broken", r, s["error"])
                continue
            e = s["evidence"]
            refused = lib.config.refuse
            label = f"{r.copy.label} {s['version']}"
            if e["state"] == "unmeasured":
                add("unmeasured", r, f"{label} has no card")
            elif e["state"] == "stale":
                add(
                    "stale",
                    r,
                    f"{label}: the card says {e.get('cardVerdict')}, but it was made "
                    "for other files",
                )
            elif e["state"] == "broken":
                add("broken", r, f"{label}: {e.get('note')}")
            elif e["state"] == "cases-changed":
                add("cases-changed", r, f"{label}: {e.get('note')}")
            if e["verdict"] in refused or e["state"] in refused:
                add("blocked", r, f"{label} can't be installed: {e['verdict']}")
    if proj is not None and lock is not None:
        for key, entry in sorted(lock.entries.items()):
            path = proj.root / key
            where = {
                "kind": "",
                "copy": entry["skill"] + (f".{entry['variant']}" if entry["variant"] else ""),
                "installed": key,
            }
            if not path.is_dir() or path.is_symlink():
                found.append(
                    {
                        **where,
                        "kind": "install-missing",
                        "message": f"{key} is in the lockfile but isn't on disk",
                    }
                )
            elif hash_dir(path) != entry["hash"]:
                found.append(
                    {
                        **where,
                        "kind": "install-changed",
                        "message": f"{key} has changed since Mordecai installed it",
                    }
                )
            r = lib.entries.get((entry["skill"], entry["variant"]))
            if r is not None and r.log is not None:
                try:
                    newest = lib.pick(r)
                except LibraryError:
                    continue
                if (
                    str(newest.version) != entry["version"]
                    or hash_dir(newest.folder) != entry["hash"]
                ):
                    found.append(
                        {
                            **where,
                            "kind": "update",
                            "message": f"{key}: {entry['version']} is installed; "
                            f"{newest.version} is available",
                        }
                    )
    return found
