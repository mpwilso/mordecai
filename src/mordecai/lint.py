"""Runs Mordecai's case-quality warnings on a plugin's eval case files, before any eval runs.

It reads the same files `claude plugin eval` reads: <plugin>/evals/<case>/prompt.md, its
graders/*.md, and case.yaml when present. Only the fields the checks need are read.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from mordecai.provenance import skill_names
from mordecai.result import Case, skill_graders
from mordecai.verdict import DEFAULT_RULES, case_warnings

SKIP = {"results", "mocks"}


def frontmatter(text: str) -> tuple[dict, str]:
    """A small reader for the flat YAML frontmatter these files use: key: value pairs,
    [a, b] lists, quoted strings, integers, and | blocks. Returns the fields and the body."""
    if not text.startswith("---"):
        return {}, text
    head, _, body = text[3:].partition("\n---")
    fields: dict = {}
    lines = head.strip("\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line[0] in " \t#":
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value in ("|", ">", "|-", ">-"):
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                block.append(lines[i].strip())
                i += 1
            fields[key.strip()] = "\n".join(block).strip()
            continue
        fields[key.strip()] = _value(value)
    return fields, body[1:] if body.startswith("\n") else body


def _value(v: str):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [_value(x.strip()) for x in v[1:-1].split(",") if x.strip()]
    try:
        return int(v)
    except ValueError:
        return v


@dataclass(frozen=True)
class CaseFile:
    case: Case
    runs: int
    model: str | None
    scored: bool  # has a grader other than "the skill fired"


def read_case(path: Path) -> CaseFile:
    prompt_md = path / "prompt.md"
    fields, body = (
        frontmatter(prompt_md.read_text(encoding="utf-8")) if prompt_md.exists() else ({}, "")
    )
    graders = []
    for g in sorted((path / "graders").glob("*.md")):
        gf, _ = frontmatter(g.read_text(encoding="utf-8"))
        config = {k: v for k, v in gf.items() if k not in ("type", "weight", "arm")}
        graders.append({"name": g.stem, "type": gf.get("type"), "config": config})
    fire, silent = skill_graders({"graders": graders})
    trigger = "should-not-fire" if silent else "should-fire" if fire else "unmeasured"
    case = Case(
        name=str(fields.get("name") or path.name),
        dir=path.as_posix(),
        prompt=body.strip(),
        trigger=trigger,
        with_runs=(),
        without_runs=(),
    )
    return CaseFile(
        case=case,
        runs=int(fields.get("runs") or 3),
        model=fields.get("model"),
        scored=any(g["name"] not in fire for g in graders),
    )


def plugin_name(plugin: Path) -> str:
    for manifest in (plugin / ".claude-plugin" / "plugin.json", plugin / "plugin.json"):
        if manifest.exists():
            return json.loads(manifest.read_text(encoding="utf-8")).get("name") or plugin.name
    return plugin.name


def lint(plugin: Path, rules=DEFAULT_RULES) -> tuple[list[CaseFile], list[str]]:
    evals = plugin / "evals"
    dirs = (
        sorted(
            p
            for p in evals.iterdir()
            if p.is_dir()
            and p.name not in SKIP
            and ((p / "prompt.md").exists() or (p / "case.yaml").exists())
        )
        if evals.is_dir()
        else []
    )
    files = [read_case(d) for d in dirs]
    cases = [f.case for f in files]
    effect = [f for f in files if f.case.trigger != "should-not-fire"]
    names = skill_names(plugin) + [plugin_name(plugin)]
    warnings = []
    if not files:
        warnings.append(f"No eval cases found under {evals}.")
    if len(effect) < rules.min_cases:
        warnings.append(
            f"Only {len(effect)} case(s) would be compared; the rules need at least "
            f"{rules.min_cases}."
        )
    warnings += case_warnings(cases, [f.case for f in effect], [f.runs for f in effect], names)
    unscored = [f.case.name for f in effect if not f.scored]
    if unscored:
        warnings.append(
            f"{len(unscored)} case(s) only check that the skill fired ({', '.join(unscored[:3])}). "
            "With nothing else to score, the eval scores that check in both arms, and the "
            "baseline can never pass it."
        )
    aliases = sorted({f.model for f in files if f.model and not str(f.model).startswith("claude-")})
    if aliases:
        warnings.append(
            f"Some cases set the model to an alias ({', '.join(aliases)}), not a pinned ID."
        )
    empty = [f.case.name for f in files if not f.case.prompt]
    if empty:
        warnings.append(f"{len(empty)} case(s) have an empty prompt ({', '.join(empty[:3])}).")
    return files, warnings
