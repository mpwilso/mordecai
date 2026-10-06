"""mordecai mcp: the skill library over MCP, on stdio, with the official MCP Python SDK.

It reads the same config and writes the same lockfile as the command line, through the same
code. Two tools change files: install_skill and uninstall_skill. They write only inside the
targets the config's [install] targets lists, under the project the server was started for,
and say so in their descriptions so a client can ask the user first. Neither can override the
install policy; that takes the command line. No tool writes to GitHub or runs a skill's scripts.

A skill installed into a tool's skills folder is loaded from its description, the way it was
measured. Reading one over MCP is the fallback for a client without native skills.
"""

import argparse
import functools
import tempfile
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from mordecai import __version__
from mordecai.library import LibraryError, catalog
from mordecai.library import install as inst
from mordecai.library.lock import Lock
from mordecai.library.sources import Library, load_config

INSTRUCTIONS = (
    "Mordecai keeps a library of Agent Skills, each with a base and named variants, and says "
    "for each version whether a measured eval shows it helps. Prefer installing a skill "
    "(install_skill) over reading it: an installed skill is loaded by the client from its "
    "description. install_skill and uninstall_skill change files in the user's project; ask "
    "the user before calling them."
)
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=True)
WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=True
)


MAX_TEXT = 200  # the longest query or version a tool takes


def _scrub(text: str, project_dir: Path) -> str:
    """text with this machine's folders replaced, so an error names no local path."""
    for path, label in (
        (str(project_dir), "<project>"),
        (tempfile.gettempdir(), "<tmp>"),
        (str(Path.home()), "~"),
    ):
        if path and path != "/":
            text = text.replace(path, label)
    return text


def _errors(project_dir: Path):
    """Report the library's refusals to the client as tool errors carrying their message, with
    local folders removed, rather than as crashes the SDK would hide. Anything else is the
    SDK's generic error, which names only the tool."""

    def wrap(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for value in (*args, *kwargs.values()):
                if isinstance(value, str) and len(value) > MAX_TEXT:
                    raise ToolError(f"an argument is over {MAX_TEXT} characters")
            try:
                return fn(*args, **kwargs)
            except (LibraryError, OSError) as e:
                raise ToolError(_scrub(str(e), project_dir)) from None

        return wrapper

    return wrap


def build(config: Path | None = None, project_dir: Path | None = None) -> MCPServer:
    project_dir = (project_dir or Path.cwd()).resolve()
    server = MCPServer(name="mordecai", version=__version__, instructions=INSTRUCTIONS)
    _guarded = _errors(project_dir)

    def library() -> Library:
        return Library(load_config(config, project_dir))

    def project() -> inst.Project:
        return inst.project(project_dir)

    def allowed_target(lib: Library, target: str) -> str:
        name = inst.ALIASES.get(target, target)
        if name not in lib.config.targets:
            raise LibraryError(
                f"target {target!r} isn't allowed; the config allows "
                f"{', '.join(lib.config.targets)}"
            )
        return name

    @server.tool(
        annotations=READ,
        description="Every skill in the library: its base and variants, "
        "the version install would pick, its verdict, its source and its lineage.",
    )
    @_guarded
    def list_skills() -> dict:
        with library() as lib:
            return {"skills": catalog.listing(lib), "problems": lib.problems}

    @server.tool(
        annotations=READ,
        description="Skills whose name, variant or description "
        "contains every word of the query. Plain text matching, no model.",
    )
    @_guarded
    def search_skills(query: str) -> dict:
        with library() as lib:
            return {"matches": catalog.search(lib, query)}

    @server.tool(
        annotations=READ,
        description="One skill copy's SKILL.md text, file list, "
        "version, lineage and verdict. Leave variant empty for the base, and version "
        "empty for the newest release.",
    )
    @_guarded
    def get_skill(skill: str, variant: str | None = None, version: str | None = None) -> dict:
        with library() as lib:
            return catalog.show(lib, skill, variant, version)

    @server.tool(
        annotations=READ,
        description="One skill copy's releases, newest first, with "
        "each one's date, tag, changelog notes, lineage and verdict.",
    )
    @_guarded
    def skill_history(skill: str, variant: str | None = None) -> dict:
        with library() as lib:
            return catalog.history(lib, skill, variant)

    @server.tool(
        annotations=READ,
        description="Skills installed in this project that have a "
        "newer release, with its verdict, and installs that changed on disk. Changes "
        "nothing.",
    )
    @_guarded
    def check_updates() -> dict:
        proj = project()
        lock = Lock(proj.lock_path)
        with library() as lib:
            rows = []
            for u in inst.plan_updates(lib, proj, lock):
                row = {
                    "installed": u.key,
                    "skill": u.entry["skill"],
                    "variant": u.entry["variant"],
                    "version": u.entry["version"],
                }
                if u.problem:
                    row["problem"] = u.problem
                else:
                    row.update(
                        available=str(u.plan.picked.version),
                        update=u.available,
                        verdict=u.plan.evidence.label,
                    )
                    if u.plan.refused:
                        row["refused"] = u.plan.refused
                rows.append(row)
            return {"installs": rows}

    @server.tool(
        annotations=WRITE,
        description="CHANGES FILES in the user's project: copies a "
        "skill into a configured skills folder (target: agents, claude, github or "
        "cursor, if the config allows it) and records it in mordecai-lock.json. Refuses "
        "a version whose evidence the policy refuses, such as Hurts. If it would replace "
        "an installed copy it changes nothing and returns the diff; call again with "
        "confirm_replace true after the user has seen it. Ask the user before calling.",
    )
    @_guarded
    def install_skill(
        skill: str,
        variant: str | None = None,
        version: str | None = None,
        target: str = "agents",
        confirm_replace: bool = False,
    ) -> dict:
        proj = project()
        lock = Lock(proj.lock_path)
        with library() as lib:
            name = allowed_target(lib, target)
            p = inst.plan(lib, proj, lock, skill, variant, version, [name])
            out = {
                "skill": skill,
                "variant": p.entry.copy.variant,
                "version": str(p.picked.version),
                "verdict": p.evidence.label,
                "evidence": p.evidence.state,
                "warnings": p.warnings,
            }
            if p.refused:
                return {
                    **out,
                    "installed": False,
                    "refused": f"{p.refused} Only a person can override that, at the command "
                    f"line: mordecai library install {skill}"
                    + (f" --variant {p.entry.copy.variant}" if p.entry.copy.variant else "")
                    + f" --allow {p.refused_as}.",
                }
            if p.replaces and not confirm_replace:
                return {
                    **out,
                    "installed": False,
                    "needsConfirmation": True,
                    "diff": "".join(d.diff for d in p.destinations),
                }
            return {
                **out,
                "installed": True,
                "paths": inst.apply(p, proj, lock),
                "commit": p.picked.commit,
            }

    @server.tool(
        annotations=WRITE,
        description="CHANGES FILES in the user's project: removes a "
        "skill that Mordecai installed, from the configured skills folders, and its "
        "lockfile entry. Refuses a folder that changed since it was installed. Ask the "
        "user before calling.",
    )
    @_guarded
    def uninstall_skill(skill: str, target: str | None = None) -> dict:
        proj = project()
        lock = Lock(proj.lock_path)
        with library() as lib:
            names = [allowed_target(lib, target)] if target else list(lib.config.targets)
        removals = inst.plan_uninstall(proj, lock, skill, names)
        return {"removed": inst.apply_uninstall(removals, lock)}

    return server


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mordecai mcp", description="Serve the skill library to MCP clients over stdio."
    )
    p.add_argument("--config", type=Path, help="the library config (mordecai-library.toml)")
    p.add_argument("--project", type=Path, help="the project installs go into (default: here)")
    return p


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    build(args.config, args.project).run("stdio")
    return 0
