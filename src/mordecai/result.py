"""Reads the JSON result that `claude plugin eval --json` writes (schemaVersion 1).

Only the fields Mordecai uses are read. Unknown fields are ignored, as the format's docs ask,
so a newer Claude Code that adds fields still parses. tests/fixtures/probe-result.json is a
real result from Claude Code 2.1.289.

A result may come from someone else, so every field Mordecai uses is checked before it's used.
A field of the wrong type, a score outside 0 to 1, or a cost or turn count that isn't a finite
number at least zero is refused with a ResultError, never read as something else.
"""

import json
import math
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

# Far larger than any real result. A bigger file is refused rather than read into memory.
MAX_BYTES = 64 * 1024 * 1024


class ResultError(Exception):
    """The file isn't an eval result Mordecai can read."""


@dataclass(frozen=True)
class Run:
    score: float
    error: str | None
    skipped_paid: bool
    cost_usd: float | None
    turns: float | None
    # With-arm only: did every "the skill fired" grader pass? None when the case has none.
    fired: bool | None
    # Did any "the skill must not fire" grader fail? None when the case has none.
    misfired: bool | None
    # The run's trace file, as the result names it (tracePath).
    trace: str | None = None
    # Did the trace list a tool call that permissions refused? None until a trace is read.
    denied: bool | None = None


@dataclass(frozen=True)
class Case:
    name: str
    dir: str
    prompt: str
    # "should-fire", "should-not-fire" or "unmeasured", from the case's Skill graders.
    trigger: str
    with_runs: tuple[Run, ...]
    without_runs: tuple[Run, ...]

    @property
    def compared(self) -> bool:
        return bool(self.with_runs) and bool(self.without_runs)


@dataclass(frozen=True)
class Plugin:
    name: str
    version: str | None
    path: str | None


@dataclass(frozen=True)
class Suite:
    claude_version: str | None
    started_at: str | None
    partial: bool
    partial_reason: str | None
    model: str | None
    judge_model: str | None
    root: str | None
    plugins: tuple[Plugin, ...]
    cases: tuple[Case, ...]
    # Runs whose traces show the setup refusing them inside their own folder (D19). Set from
    # the traces when a card is made, and from the card when the library checks it.
    blocked_runs: int = 0


def _get(raw: dict, key: str, kind, where: str):
    """raw[key] if it is missing, null or of the given kind; otherwise a ResultError."""
    value = raw.get(key)
    if value is not None and not isinstance(value, kind):
        raise ResultError(f"{where}: {key} should be {_KIND[kind]}")
    return value


_KIND = {str: "a string", dict: "an object", list: "a list", bool: "true or false"}


def _items(raw: dict, key: str, where: str) -> list[dict]:
    """raw[key] as a list of objects; missing or null is an empty list."""
    items = _get(raw, key, list, where) or []
    if not all(isinstance(x, dict) for x in items):
        raise ResultError(f"{where}: every entry of {key} should be an object")
    return items


def _finite(value: int | float) -> bool:
    """Whether value is finite as a float. An integer too big for a float isn't, and would
    otherwise raise OverflowError."""
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _number(raw: dict, key: str, where: str, high: float | None = None) -> float | None:
    """raw[key] as a finite number from 0 (to high, if given), or None if missing or null."""
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or not _finite(value):
        raise ResultError(f"{where}: {key} should be a number, not {json.dumps(value)[:40]}")
    if value < 0 or (high is not None and value > high):
        span = f"from 0 to {high:g}" if high is not None else "at least 0"
        raise ResultError(f"{where}: {key} is {value:g}; it should be {span}")
    return float(value)


def skill_graders(case: dict) -> tuple[set[str], set[str]]:
    """Names of the case's tool_used graders on the Skill tool: those that expect it to fire,
    and those that expect it not to (max: 0)."""
    fire, silent = set(), set()
    for g in _items(case, "graders", f"case {case.get('name')!r}"):
        config = _get(g, "config", dict, "a grader") or {}
        name = _get(g, "name", str, "a grader")
        if g.get("type") != "tool_used" or config.get("tool") != "Skill":
            continue
        if config.get("max") == 0:
            silent.add(name)
        else:
            fire.add(name)
    return fire, silent


def _run(raw: dict, fire: set[str], silent: set[str], arm: str, where: str) -> Run:
    score = _number(raw, "score", where, high=1)
    if score is None:
        raise ResultError(f"{where}: the run has no score")
    graders = _items(raw, "graders", where)
    results = {_get(g, "name", str, f"{where}, a grader"): g.get("passed") for g in graders}
    fired = None
    if arm == "with" and fire and all(n in results for n in fire):
        fired = all(results[n] is True for n in fire)
    misfired = None
    if silent and all(n in results for n in silent):
        misfired = any(results[n] is False for n in silent)
    return Run(
        score=score,
        error=_get(raw, "error", str, where),
        skipped_paid=bool(_get(raw, "skippedPaidGraders", bool, where)),
        cost_usd=_number(raw, "costUsd", where),
        turns=_number(raw, "turns", where),
        fired=fired,
        misfired=misfired,
        trace=_get(raw, "tracePath", str, where),
    )


def _case(raw: dict) -> Case:
    name = _get(raw, "name", str, "a case")
    if not name:
        raise ResultError("a case has no name")
    where = f"case {name!r}"
    fire, silent = skill_graders(raw)
    trigger = "should-not-fire" if silent else "should-fire" if fire else "unmeasured"
    arms = _get(raw, "arms", dict, where) or {}

    def runs(arm):
        at = f"{where}, {arm} arm"
        return tuple(
            _run(r, fire, silent, arm, f"{at}, run {i + 1}")
            for i, r in enumerate(_items(arms, arm, at))
        )

    return Case(
        name=name,
        dir=_get(raw, "dir", str, where) or "",
        prompt=_get(raw, "promptMarkdown", str, where) or "",
        trigger=trigger,
        with_runs=runs("with"),
        without_runs=runs("without"),
    )


def parse(doc: dict) -> Suite:
    if not isinstance(doc, dict) or doc.get("schemaVersion") != SCHEMA_VERSION:
        raise ResultError(f"not a claude plugin eval result with schemaVersion {SCHEMA_VERSION}")
    top = "the result"
    suite = _get(doc, "suite", dict, top) or {}
    return Suite(
        claude_version=_get(doc, "claudeVersion", str, top),
        started_at=_get(doc, "startedAt", str, top),
        partial=bool(_get(doc, "partial", bool, top)),
        partial_reason=_get(doc, "partialReason", str, top),
        model=_get(suite, "modelOverride", str, "suite"),
        judge_model=_get(suite, "judgeModel", str, "suite"),
        root=_get(suite, "root", str, "suite"),
        plugins=tuple(
            Plugin(
                name=_get(p, "name", str, "a plugin") or "",
                version=_get(p, "version", str, "a plugin"),
                path=_get(p, "path", str, "a plugin"),
            )
            for p in _items(suite, "plugins", "suite")
        ),
        cases=tuple(_case(c) for c in _items(doc, "cases", top)),
    )


@dataclass(frozen=True)
class Refusals:
    total: int  # tool calls permissions refused
    blocked: int  # of those, refused on a tool the run had, aimed inside its folder (D19)


def _target(tool: str, tool_input: dict, cwd: str) -> str | None:
    """The absolute path a refused call aimed at: a Glob's pattern up to its first wildcard,
    under its path; a Grep's path; otherwise the call's file or path argument."""
    if not isinstance(tool_input, dict):
        return None
    base = tool_input.get("path") if isinstance(tool_input.get("path"), str) else "."
    if tool == "Glob":
        pattern = tool_input.get("pattern")
        if not isinstance(pattern, str):
            return None
        fixed = re.split(r"[*?\[{]", pattern, maxsplit=1)[0] or "."
        return posixpath.normpath(posixpath.join(cwd, base, fixed))
    if tool == "Grep":
        return posixpath.normpath(posixpath.join(cwd, base))
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return posixpath.normpath(posixpath.join(cwd, value))
    return None


def _inside(path: str, roots: list[str]) -> bool:
    return any(path == r or path.startswith(r.rstrip("/") + "/") for r in roots)


def trace_refusals(path: Path) -> Refusals | None:
    """The tool calls permissions refused in a run, from the run's trace: the JSON Lines
    stream Claude Code writes, where each message of type "result" lists the calls refused
    since the one before it in permission_denials. A trace can hold more than one, as when a
    run hits its turn limit and goes on, so they are added up. The result JSON itself has no
    such field.

    A refusal is blocked (D19) when the tool is one the run had (the init message's tools)
    and it aimed inside the run's working folder (init cwd) or a plugin folder the run
    loaded. Then the setup, not the model, stopped it. Without an init message nothing
    counts as blocked. None when the trace is missing, isn't a regular file, is over
    MAX_BYTES, or has no readable result message."""
    try:
        if not path.is_file():
            return None
        with open(path, "rb") as f:
            data = f.read(MAX_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_BYTES:
        return None
    found, tools, roots = None, set(), []
    for line in data.splitlines():
        init = b'"subtype":"init"' in line or b'"subtype": "init"' in line
        if not init and b'"permission_denials"' not in line:
            continue
        try:
            message = json.loads(line, parse_constant=_no_constant)
        except (ValueError, RecursionError):
            continue
        if not isinstance(message, dict):
            continue
        if message.get("type") == "system" and message.get("subtype") == "init":
            cwd = message.get("cwd")
            if isinstance(cwd, str) and cwd.startswith("/"):
                plugins = message.get("plugins") if isinstance(message.get("plugins"), list) else []
                folders = [p.get("path") for p in plugins if isinstance(p, dict)]
                roots = [posixpath.normpath(cwd)]
                roots += [
                    posixpath.normpath(f)
                    for f in folders
                    if isinstance(f, str) and f.startswith("/")
                ]
                tools = {t for t in message.get("tools") or [] if isinstance(t, str)}
            continue
        if message.get("type") != "result":
            continue
        denials = message.get("permission_denials")
        if not isinstance(denials, list):
            continue
        found = found or Refusals(0, 0)
        blocked = 0
        for d in denials:
            tool = d.get("tool_name") if isinstance(d, dict) else None
            if roots and tool in tools:
                target = _target(tool, d.get("tool_input"), roots[0])
                blocked += bool(target and _inside(target, roots))
        found = Refusals(found.total + len(denials), found.blocked + blocked)
    return found


def trace_denials(path: Path) -> int | None:
    """How many tool calls permissions refused in a run (see trace_refusals)."""
    found = trace_refusals(path)
    return None if found is None else found.total


def _no_constant(name: str):
    raise ValueError(f"{name} isn't a number JSON allows")


def read_json(path: Path, what: str):
    """The JSON document in path and the file's exact bytes. Refuses files over MAX_BYTES,
    invalid UTF-8, NaN and Infinity, and nesting too deep to parse."""
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_BYTES + 1)
    except OSError as e:
        raise ResultError(f"can't read {path}: {e.strerror or e}") from e
    if len(data) > MAX_BYTES:
        raise ResultError(f"{path} is over {MAX_BYTES // 2**20} MB, too big to be {what}")
    try:
        return json.loads(data, parse_constant=_no_constant), data
    except json.JSONDecodeError as e:
        raise ResultError(f"{path} isn't JSON: {e.msg} at line {e.lineno}") from e
    except UnicodeDecodeError as e:
        raise ResultError(f"{path} isn't UTF-8 text") from e
    except ValueError as e:
        raise ResultError(f"{path} isn't valid JSON: {e}") from e
    except RecursionError as e:
        raise ResultError(f"{path} is nested too deeply to read") from e


def load(path: Path) -> tuple[Suite, bytes]:
    """The parsed suite, and the file's exact bytes, which the card hashes."""
    doc, data = read_json(path, "an eval result")
    return parse(doc), data
