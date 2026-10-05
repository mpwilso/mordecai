"""Reads the JSON result that `claude plugin eval --json` writes (schemaVersion 1).

Only the fields Mordecai uses are read. Unknown fields are ignored, as the format's docs ask,
so a newer Claude Code that adds fields still parses. tests/fixtures/probe-result.json is a
real result from Claude Code 2.1.289.
"""

import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1


class ResultError(Exception):
    """The file isn't an eval result Mordecai can read."""


@dataclass(frozen=True)
class Run:
    score: float
    error: str | None
    aborted: bool
    skipped_paid: bool
    cost_usd: float | None
    turns: int | None
    # With-arm only: did every "the skill fired" grader pass? None when the case has none.
    fired: bool | None
    # Did any "the skill must not fire" grader fail? None when the case has none.
    misfired: bool | None


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
    cost_usd: float | None
    partial: bool
    partial_reason: str | None
    ablation: str | None
    model: str | None
    judge_model: str | None
    root: str | None
    plugins: tuple[Plugin, ...]
    cases: tuple[Case, ...]


def _skill_graders(case: dict) -> tuple[set[str], set[str]]:
    """Names of the case's tool_used graders on the Skill tool: those that expect it to fire,
    and those that expect it not to (max: 0)."""
    fire, silent = set(), set()
    for g in case.get("graders") or []:
        config = g.get("config") or {}
        if g.get("type") != "tool_used" or config.get("tool") != "Skill":
            continue
        if config.get("max") == 0:
            silent.add(g.get("name"))
        else:
            fire.add(g.get("name"))
    return fire, silent


def _run(raw: dict, fire: set[str], silent: set[str], arm: str) -> Run:
    if not isinstance(raw.get("score"), int | float):
        raise ResultError("a run has no numeric score")
    results = {g.get("name"): g.get("passed") for g in raw.get("graders") or []}
    fired = None
    if arm == "with" and fire and all(n in results for n in fire):
        fired = all(results[n] is True for n in fire)
    misfired = None
    if silent and all(n in results for n in silent):
        misfired = any(results[n] is False for n in silent)
    return Run(
        score=float(raw["score"]),
        error=raw.get("error"),
        aborted=bool(raw.get("aborted")),
        skipped_paid=bool(raw.get("skippedPaidGraders")),
        cost_usd=raw.get("costUsd"),
        turns=raw.get("turns"),
        fired=fired,
        misfired=misfired,
    )


def _case(raw: dict) -> Case:
    if not raw.get("name"):
        raise ResultError("a case has no name")
    fire, silent = _skill_graders(raw)
    trigger = "should-not-fire" if silent else "should-fire" if fire else "unmeasured"
    arms = raw.get("arms") or {}
    return Case(
        name=raw["name"],
        dir=raw.get("dir") or "",
        prompt=raw.get("promptMarkdown") or "",
        trigger=trigger,
        with_runs=tuple(_run(r, fire, silent, "with") for r in arms.get("with") or []),
        without_runs=tuple(_run(r, fire, silent, "without") for r in arms.get("without") or []),
    )


def parse(doc: dict) -> Suite:
    if not isinstance(doc, dict) or doc.get("schemaVersion") != SCHEMA_VERSION:
        raise ResultError(f"not a claude plugin eval result with schemaVersion {SCHEMA_VERSION}")
    suite = doc.get("suite") or {}
    return Suite(
        claude_version=doc.get("claudeVersion"),
        started_at=doc.get("startedAt"),
        cost_usd=doc.get("costUsd"),
        partial=bool(doc.get("partial")),
        partial_reason=doc.get("partialReason"),
        ablation=suite.get("ablation"),
        model=suite.get("modelOverride"),
        judge_model=suite.get("judgeModel"),
        root=suite.get("root"),
        plugins=tuple(
            Plugin(name=p.get("name") or "", version=p.get("version"), path=p.get("path"))
            for p in suite.get("plugins") or []
        ),
        cases=tuple(_case(c) for c in doc.get("cases") or []),
    )


def load(path: Path) -> tuple[Suite, bytes]:
    """The parsed suite, and the file's exact bytes, which the card hashes."""
    try:
        data = path.read_bytes()
    except OSError as e:
        raise ResultError(f"can't read {path}: {e.strerror}") from e
    try:
        doc = json.loads(data)
    except json.JSONDecodeError as e:
        raise ResultError(f"{path} isn't JSON: {e.msg} at line {e.lineno}") from e
    return parse(doc), data
