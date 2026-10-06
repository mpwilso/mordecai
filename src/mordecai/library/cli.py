"""mordecai library: keep, release and install skills from a library, with each version's verdict.
mordecai mcp: serve the same operations to MCP clients over stdio.

Exit codes follow the engine's: 0 for a clean result, 1 for what a command checks for (validate
errors, a status report, a refused install, a pending update), and 2 for input Mordecai can't
read or won't use.
"""

import argparse
import json
import sys
from pathlib import Path

from mordecai.library import LibraryError, catalog
from mordecai.library import install as inst
from mordecai.library.export import export_marketplace, export_skills
from mordecai.library.lock import Lock
from mordecai.library.release import fork, release
from mordecai.library.sources import Library, load_config
from mordecai.library.store import check_copy, scan
from mordecai.library.versions import BUMPS
from mordecai.render import clean


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mordecai library", description="Keep, release and install skills, with evidence."
    )
    sub = p.add_subparsers(dest="command", required=True)

    def consumer(name: str, help: str) -> argparse.ArgumentParser:
        c = sub.add_parser(name, help=help)
        c.add_argument("--config", type=Path, help="the library config (mordecai-library.toml)")
        return c

    def where(c: argparse.ArgumentParser) -> None:
        c.add_argument("--project", type=Path, help="the project to install into (default: here)")
        c.add_argument("--user", action="store_true", help="install under your home folder")

    def author(name: str, help: str) -> argparse.ArgumentParser:
        c = sub.add_parser(name, help=help)
        c.add_argument(
            "--library",
            type=Path,
            default=Path("library"),
            help="the library folder (default: ./library)",
        )
        return c

    author("validate", help="check every copy in a library folder")
    c = consumer("list", help="every skill, its copies, versions and verdicts")
    c.add_argument("--json", action="store_true")
    for name, help in (
        ("show", "one copy: its text, files, version and verdict"),
        ("history", "one copy's releases, notes and verdicts"),
    ):
        c = consumer(name, help)
        c.add_argument("skill")
        c.add_argument("--variant")
        if name == "show":
            c.add_argument("--version")
        c.add_argument("--json", action="store_true")
    c = author("release", help="release a copy: changelog, commit and a local tag; never pushes")
    c.add_argument("skill")
    c.add_argument("--variant")
    c.add_argument("--bump", required=True, choices=BUMPS)
    c.add_argument("--based-on", help="for a variant: the base release it is now based on")
    c.add_argument("--note", action="append", default=[], help="a changelog line (repeatable)")
    c.add_argument("--message", help="extra text for the release commit")
    c = author("fork", help="create a variant from the base's newest release")
    c.add_argument("skill")
    c.add_argument("--variant", required=True)
    c = consumer(
        "status",
        help="variants behind base, unreleased changes, missing, stale, broken "
        "or refused cards, and installs that changed",
    )
    where(c)
    c.add_argument("--json", action="store_true")
    c = consumer("install", help="copy a skill into a tool's skills folder and lock it")
    c.add_argument("skill")
    c.add_argument("--variant")
    c.add_argument("--version")
    c.add_argument(
        "--target",
        action="append",
        help="agents (default), claude, github, cursor, or a folder; repeatable",
    )
    where(c)
    c.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="VERDICT",
        help="install even though the policy refuses this verdict or state",
    )
    c.add_argument(
        "--force",
        action="store_true",
        help="replace a folder that changed since Mordecai installed it",
    )
    c.add_argument("--yes", action="store_true", help="replace an installed copy after the diff")
    c = consumer("update", help="show what newer releases would change; apply with --yes")
    c.add_argument("skill", nargs="?")
    where(c)
    c.add_argument("--yes", action="store_true")
    c.add_argument("--force", action="store_true")
    c = consumer("uninstall", help="remove an installed skill recorded in the lockfile")
    c.add_argument("skill")
    c.add_argument("--target", action="append")
    where(c)
    c.add_argument("--force", action="store_true")
    c = consumer("export", help="write the resolved library as a marketplace or a skills folder")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--marketplace", type=Path, help="write a Claude Code plugin marketplace here")
    g.add_argument("--skills", type=Path, help="write plain <skill>/ folders here")
    c.add_argument("--name", default="skills", help="the marketplace's name")
    c.add_argument("--owner", default="", help="the marketplace owner's name")
    return p


def _p(out, text: str = "") -> None:
    out.write(clean(text) + "\n")


def _verdict(e: dict | None) -> str:
    if not e:
        return "?"
    if e["state"] == "stale":
        return f"stale (card says {e.get('cardVerdict')})"
    if e["state"] == "cases-changed":
        return f"{e['verdict']} (cases changed)"
    return e["verdict"]


def cmd_validate(args, out) -> int:
    root = args.library.resolve().parent
    lib = args.library.resolve().name
    copies, problems = scan(root, lib)
    if not copies and problems:
        print(f"mordecai: {clean(problems[0])}", file=sys.stderr)
        return 2
    errors = list(problems)
    warnings = []
    logs = {}
    for c in copies:
        if c.variant is None:
            base = check_copy(root, c)
            logs[c.skill] = base.log
    for skill in sorted({c.skill for c in copies if c.variant} - set(logs)):
        warnings.append(
            f"{skill}: no base in this library, so its variants' lineage is checked "
            "only against the base another source provides"
        )
    for c in copies:
        checked = check_copy(root, c, logs.get(c.skill) if c.variant else None)
        errors += [f"{c.id}: {e}" for e in checked.all_errors]
        warnings += [f"{c.id}: {w}" for w in checked.report.warnings]
    _p(
        out,
        f"{args.library}: {len(copies)} copies of {len({c.skill for c in copies})} skills, "
        f"{len(errors)} error(s), {len(warnings)} warning(s)",
    )
    for e in errors:
        _p(out, f"  error: {e}")
    for w in warnings:
        _p(out, f"  warning: {w}")
    return 1 if errors else 0


def cmd_list(lib, args, out) -> int:
    items = catalog.listing(lib)
    if args.json:
        out.write(json.dumps(items, indent=2) + "\n")
        return 0
    for item in items:
        _p(
            out,
            item["skill"] + (f"  (default variant: {item['default']})" if item["default"] else ""),
        )
        for c in item["copies"]:
            name = f"variant {c['variant']}" if c["variant"] else "base"
            if "error" in c:
                _p(out, f"  {name:<22} error: {c['error']}")
                continue
            ver = c["version"] + ("" if c["tag"] else " (untagged)")
            extra = []
            if c.get("basedOn"):
                extra.append(f"based on {c['basedOn']}")
            if c.get("behindBase"):
                extra.append(f"behind base {c['behindBase']}")
            if c["shadows"]:
                extra.append(f"shadows {', '.join(c['shadows'])}")
            _p(
                out,
                f"  {name:<22} {ver:<18} {_verdict(c.get('evidence')):<26} "
                f"{c['source']}" + (f"  ({'; '.join(extra)})" if extra else ""),
            )
    for p in lib.problems:
        _p(out, f"problem: {p}")
    return 0


def cmd_show(lib, args, out) -> int:
    d = catalog.show(lib, args.skill, args.variant, args.version)
    if args.json:
        out.write(json.dumps(d, indent=2) + "\n")
        return 0
    _p(
        out,
        f"{d['id']} {d['version']}"
        + ("" if d["tag"] else " (untagged)")
        + f": {_verdict(d.get('evidence'))}",
    )
    e = d.get("evidence") or {}
    if e.get("note"):
        _p(out, f"  {e['note']}")
    if e.get("model"):
        _p(out, f"  Measured on {e['model']}")
    _p(
        out,
        f"  Source {d['source']}, {d['path']}" + (f" at {d['commit'][:12]}" if d["commit"] else ""),
    )
    if d.get("basedOn"):
        _p(
            out,
            f"  Based on base {d['basedOn']}"
            + (f"; the base is at {d['behindBase']}" if d.get("behindBase") else ""),
        )
    _p(out, f"  Files: {', '.join(d['files'])}")
    for w in d["problems"] + d["warnings"]:
        _p(out, f"  ! {w}")
    _p(out)
    for line in d["text"].splitlines():
        _p(out, line)
    return 0


def cmd_history(lib, args, out) -> int:
    d = catalog.history(lib, args.skill, args.variant)
    if args.json:
        out.write(json.dumps(d, indent=2) + "\n")
        return 0
    _p(out, f"{d['id']} from {d['source']}")
    if d["unreleased"]:
        _p(out, "  Unreleased")
        for n in d["unreleased"]:
            _p(out, f"    {n}")
    for v in d["versions"]:
        if "date" not in v:
            _p(out, f"  {v['version']}  {v['tag']}  {v['note']}")
            continue
        tag = v["tag"] or "no tag"
        lineage = f"  based on base {v['basedOn']}" if v.get("basedOn") else ""
        _p(out, f"  {v['version']}  {v['date']}  {tag}  {_verdict(v['evidence'])}{lineage}")
        for n in v["notes"]:
            _p(out, f"    {n}")
    return 0


def cmd_release(args, out) -> int:
    r = release(
        args.library, args.skill, args.variant, args.bump, args.based_on, args.note, args.message
    )
    _p(out, f"Released {r.tag} at {r.commit[:12]}. The tag is local; nothing was pushed.")
    return 0


def cmd_fork(args, out) -> int:
    dest = fork(args.library, args.skill, args.variant)
    _p(out, f"Created {dest}. Edit it, add notes under Unreleased, then release it.")
    return 0


def cmd_status(lib, args, out) -> int:
    proj = inst.project(args.project, args.user)
    lock = Lock(proj.lock_path)
    found = catalog.status(lib, proj, lock)
    if args.json:
        out.write(json.dumps(found, indent=2) + "\n")
    elif not found:
        _p(out, "Nothing to report.")
    else:
        for f in found:
            _p(out, f"{f['kind']:<16} {f['message']}")
    return 1 if found else 0


def _print_plan(p: inst.Plan, out) -> None:
    for w in p.warnings:
        _p(out, f"warning: {w}")
    for d in p.destinations:
        if d.diff:
            _p(out, f"{d.key} would change:")
            for line in d.diff.splitlines():
                _p(out, f"  {line}")


def cmd_install(lib, args, out) -> int:
    proj = inst.project(args.project, args.user)
    lock = Lock(proj.lock_path)
    p = inst.plan(
        lib, proj, lock, args.skill, args.variant, args.version, args.target, args.allow, args.force
    )
    label = f"{p.entry.copy.label} {p.picked.version}"
    if p.refused:
        _p(out, f"Refused: {p.refused}")
        return 1
    _print_plan(p, out)
    if p.replaces and not args.yes:
        _p(out, "That would replace an installed copy. Run again with --yes to apply.")
        return 1
    keys = inst.apply(p, proj, lock)
    _p(out, f"Installed {label} ({p.evidence.label}) into {', '.join(keys)}.")
    _p(
        out,
        f"Locked in {proj.lock_path}"
        + (f" at commit {p.picked.commit[:12]}" if p.picked.commit else "")
        + ".",
    )
    return 0


def cmd_update(lib, args, out) -> int:
    proj = inst.project(args.project, args.user)
    lock = Lock(proj.lock_path)
    updates = inst.plan_updates(lib, proj, lock, args.skill, args.force)
    if not updates:
        _p(out, "Nothing is installed.")
        return 0
    pending = 0
    for u in updates:
        if u.problem:
            _p(out, f"{u.key}: {u.problem}")
            pending += 1
        elif u.plan.refused:
            _p(out, f"{u.key}: {u.plan.refused}")
            pending += 1
        elif not u.available:
            _p(out, f"{u.key}: up to date ({u.entry['version']}).")
        else:
            pending += 1
            _p(
                out,
                f"{u.key}: {u.entry['version']} -> {u.plan.picked.version} "
                f"({u.plan.evidence.label})",
            )
            _print_plan(u.plan, out)
            if args.yes:
                inst.apply(u.plan, proj, lock)
                _p(out, f"Updated {u.key}.")
                pending -= 1
    if pending and not args.yes:
        _p(out, "Nothing was changed. Run again with --yes to apply.")
    return 1 if pending else 0


def cmd_uninstall(args, out) -> int:
    proj = inst.project(args.project, args.user)
    lock = Lock(proj.lock_path)
    removed = inst.apply_uninstall(
        inst.plan_uninstall(proj, lock, args.skill, args.target, args.force), lock
    )
    _p(out, f"Removed {', '.join(removed)}.")
    return 0


def cmd_export(lib, args, out) -> int:
    if args.marketplace:
        r = export_marketplace(lib, args.marketplace, args.name, args.owner or "Mordecai library")
        where = args.marketplace
    else:
        r = export_skills(lib, args.skills)
        where = args.skills
    for row in r.written:
        _p(
            out,
            f"  {row['skill']:<20} {(row['variant'] or 'base'):<12} {row['version']:<8} "
            f"{row['verdict']}",
        )
    for s in r.skipped:
        _p(out, f"  left out: {s}")
    _p(out, f"Wrote {len(r.written)} skill(s) to {where}.")
    return 0


CONSUMER = {
    "list": cmd_list,
    "show": cmd_show,
    "history": cmd_history,
    "status": cmd_status,
    "install": cmd_install,
    "update": cmd_update,
    "export": cmd_export,
}
AUTHOR = {
    "validate": cmd_validate,
    "release": cmd_release,
    "fork": cmd_fork,
    "uninstall": cmd_uninstall,
}


def main(argv: list[str], out=None) -> int:
    """argv starts with "library" or "mcp"."""
    out = out or sys.stdout
    if argv[0] == "mcp":
        from mordecai.library.server import main as serve

        return serve(argv[1:])
    args = _parser().parse_args(argv[1:])
    try:
        if args.command in AUTHOR:
            return AUTHOR[args.command](args, out)
        with Library(load_config(args.config)) as lib:
            return CONSUMER[args.command](lib, args, out)
    except (LibraryError, OSError) as e:
        print(f"mordecai: {clean(str(e))}", file=sys.stderr)
        return 2
