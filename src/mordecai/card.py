"""The card: a verdict, the numbers behind it, and the hashes that say what it was measured on.

A card is written as JSON with sorted keys, so the same result always writes the same bytes.
Its paths are relative, so a card holds no local directory names and still checks after the
repository is cloned somewhere else: the skill directory is relative to the directory the card
is written in, and the cases' root is relative to the skill directory.
"""

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from mordecai import __version__
from mordecai.provenance import hash_cases, hash_skill, sha256, skill_names
from mordecai.result import Suite
from mordecai.verdict import DEFAULT_RULES, Reading, Rules, read

CARD_VERSION = 1


@dataclass(frozen=True)
class Card:
    plugin: str
    version: str | None
    skills: tuple[str, ...]
    reading: Reading
    model: str | None
    judge_model: str | None
    claude_version: str | None
    started_at: str | None
    skill_hash: str | None
    cases_hash: str | None
    result_hash: str
    skill_dir: str | None
    cases_root: str | None
    case_dirs: tuple[str, ...]
    rules: Rules

    @property
    def title(self) -> str:
        return f"{self.plugin} {self.version}" if self.version else self.plugin


def build(
    suite: Suite, result_bytes: bytes, skill_dir: Path | None = None, rules: Rules = DEFAULT_RULES
) -> Card:
    plugin = suite.plugins[0] if suite.plugins else None
    if skill_dir is None and plugin and plugin.path:
        skill_dir = Path(plugin.path)
    case_dirs = [c.dir for c in suite.cases if c.dir]
    found = skill_dir is not None and skill_dir.is_dir()
    if found:
        skill_dir = skill_dir.resolve()
    names = skill_names(skill_dir) if found else []
    root = Path(suite.root) if suite.root else None
    cases_root = root.resolve() if root and root.is_dir() else skill_dir
    reading = read(suite, names + ([plugin.name] if plugin else []), rules)
    cases_hash = hash_cases(cases_root, case_dirs) if cases_root and case_dirs else None
    missing = []
    if not found:
        missing.append("the skill's files")
    if cases_hash is None:
        missing.append("the eval cases")
    if missing:
        reading = _with_warning(
            reading,
            f"Couldn't find {' or '.join(missing)} on disk, so this card can't be checked "
            "for staleness. Pass --skill with the plugin directory.",
        )
    return Card(
        plugin=plugin.name if plugin else "unnamed",
        version=plugin.version if plugin else None,
        skills=tuple(names),
        reading=reading,
        model=suite.model,
        judge_model=suite.judge_model,
        claude_version=suite.claude_version,
        started_at=suite.started_at,
        skill_hash=hash_skill(skill_dir, case_dirs) if found else None,
        cases_hash=cases_hash,
        result_hash=sha256(result_bytes),
        skill_dir=str(skill_dir) if found else None,
        cases_root=str(cases_root) if cases_hash else None,
        case_dirs=tuple(case_dirs),
        rules=rules,
    )


def _with_warning(reading: Reading, text: str) -> Reading:
    return replace(reading, warnings=(*reading.warnings, text))


def _rel(path: str | None, base: Path) -> str | None:
    return None if path is None else Path(os.path.relpath(path, base)).as_posix()


def to_json(card: Card, base: Path | None = None) -> str:
    """The card as JSON. base is the directory the card file will be written in; paths are
    stored relative to it. It defaults to the current directory."""
    base = (base or Path.cwd()).resolve()
    r = card.reading
    doc = {
        "card": CARD_VERSION,
        "mordecai": __version__,
        "subject": {"plugin": card.plugin, "version": card.version, "skills": list(card.skills)},
        "verdict": r.verdict,
        "reason": r.reason,
        "numbers": {
            "casesCompared": r.cases_compared,
            "improved": r.improved,
            "flat": r.flat,
            "worse": r.worse,
            "withScore": r.with_score,
            "withoutScore": r.without_score,
            "change": r.change,
            "interval": list(r.interval) if r.interval else None,
            "fired": list(r.fired) if r.fired else None,
            "misfired": list(r.misfired) if r.misfired else None,
            "costPerRunWith": r.cost_with,
            "costPerRunWithout": r.cost_without,
            "turnsPerRunWith": r.turns_with,
            "turnsPerRunWithout": r.turns_without,
        },
        "warnings": list(r.warnings),
        "tested": {
            "model": card.model,
            "judgeModel": card.judge_model,
            "claudeVersion": card.claude_version,
            "startedAt": card.started_at,
        },
        "hashes": {"skill": card.skill_hash, "cases": card.cases_hash, "result": card.result_hash},
        "paths": {
            "skill": _rel(card.skill_dir, base),
            "casesRoot": _rel(card.cases_root, Path(card.skill_dir)) if card.skill_dir else None,
            "caseDirs": list(card.case_dirs),
            "relativeTo": {"skill": "the card's directory", "casesRoot": "the skill directory"},
        },
        "rules": asdict(card.rules),
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


class CardError(Exception):
    pass


def check(
    doc: dict,
    card_dir: Path = Path("."),
    skill_dir: Path | None = None,
    cases_root: Path | None = None,
    model: str | None = None,
) -> list[str]:
    """What has changed since the card was written. An empty list means it's current.
    card_dir is the directory the card file is in; the card's paths are relative to it.
    Older cards with absolute paths still check, since joining an absolute path keeps it.
    With model, a card measured on a different model is stale too."""
    if not isinstance(doc, dict) or doc.get("card") != CARD_VERSION:
        raise CardError(f"not a Mordecai card, version {CARD_VERSION}")
    hashes, paths = doc.get("hashes") or {}, doc.get("paths") or {}
    case_dirs = paths.get("caseDirs") or []
    changes = []
    skill = skill_dir or (card_dir / paths["skill"] if paths.get("skill") else None)
    if not hashes.get("skill") or skill is None:
        changes.append("The card has no skill hash, so it can't be checked.")
    elif not skill.is_dir():
        changes.append(f"The skill directory {paths.get('skill')} is missing.")
    elif hash_skill(skill, case_dirs) != hashes["skill"]:
        changes.append("The skill's files changed since the card was written.")
    root = cases_root
    if root is None and paths.get("casesRoot") and skill is not None:
        root = skill / paths["casesRoot"]
    if not hashes.get("cases") or root is None:
        changes.append("The card has no cases hash, so it can't be checked.")
    elif hash_cases(root, case_dirs) != hashes["cases"]:
        changes.append("The eval cases changed since the card was written.")
    tested = (doc.get("tested") or {}).get("model")
    if model and tested != model:
        changes.append(f"The card was measured on {tested or 'an unrecorded model'}, not {model}.")
    return changes
