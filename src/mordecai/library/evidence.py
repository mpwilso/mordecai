"""What a version's card says, and whether it is about that version's files.

A card and the result it was made from sit in <copy>/evidence/<X.Y.Z>/. The verdict written in
the card is never trusted: the engine reruns its rules on the stored result, and that verdict is
used only if it agrees. The card's skill hash must equal the engine's hash of the version's skill
folder. The cases are checked where the card says they are, if the source has them.

The states:

    current          the card is about these files, and its result gives its verdict
    cases-changed    as current, but the eval cases changed since, or aren't in the source
    stale            the card was made for other files
    unmeasured       no card
    broken           the card or its result can't be read, the result isn't the one the card
                     was made from, or it gives a different verdict
"""

import os
from dataclasses import dataclass, fields
from pathlib import Path

from mordecai.card import CardError, _validate
from mordecai.provenance import PathError, hash_cases, hash_skill, sha256, within
from mordecai.result import ResultError, parse, read_json
from mordecai.verdict import VERDICTS, Rules, read

STATES = ("current", "cases-changed", "stale", "unmeasured", "broken")
DEFAULT_REFUSE = ("hurts", "invalid", "broken")
APPLIES = ("current", "cases-changed")


@dataclass(frozen=True)
class Evidence:
    state: str
    verdict: str | None = None  # the engine's verdict, when state is in APPLIES or stale
    model: str | None = None
    note: str | None = None

    @property
    def applies(self) -> bool:
        return self.state in APPLIES

    @property
    def label(self) -> str:
        """The verdict if it applies to these files, otherwise the state."""
        return self.verdict if self.applies and self.verdict else self.state

    def blocked(self, refuse) -> bool:
        return self.state in refuse or (self.applies and self.verdict in refuse)


def _rules(raw) -> Rules:
    names = {f.name for f in fields(Rules)}
    if not isinstance(raw, dict) or set(raw) != names:
        raise CardError("the card's rules aren't the engine's rule fields")
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, int | float):
            raise CardError(f"the card's rule {k} isn't a number")
    return Rules(**raw)


def cases_dir(card_dir: Path) -> Path | None:
    """Where the card in card_dir says its cases are, without checking anything else, so the
    caller can fetch them first. None if the card doesn't say or can't be read."""
    try:
        doc, _ = read_json(card_dir / "card.json", "a card")
        _, paths, _ = _validate(doc)
    except (ResultError, CardError, OSError):
        return None
    if not (paths.get("skill") and paths.get("casesRoot")):
        return None
    return Path(os.path.normpath(card_dir / paths["skill"] / paths["casesRoot"]))


def assess(card_dir: Path, version_folder: Path, source_root: Path) -> Evidence:
    """The evidence in card_dir for the skill folder version_folder. The card's cases path is
    read relative to the card's own skill path, and only inside source_root."""
    card_path, result_path = card_dir / "card.json", card_dir / "result.json"
    if not card_path.exists() and not card_path.is_symlink():
        return Evidence("unmeasured")
    try:
        if card_path.is_symlink() or result_path.is_symlink():
            raise CardError("the card or its result is a link")
        doc, _ = read_json(card_path, "a card")
        hashes, paths, tested = _validate(doc)
        if not result_path.is_file():
            raise CardError("the result it was made from isn't beside it")
        result_doc, result_bytes = read_json(result_path, "an eval result")
        if sha256(result_bytes) != hashes.get("result"):
            raise CardError("result.json isn't the result this card was made from")
        suite = parse(result_doc)
        subject = doc.get("subject") if isinstance(doc.get("subject"), dict) else {}
        names = [s for s in subject.get("skills") or [] if isinstance(s, str)]
        names += [p.name for p in suite.plugins[:1] if p.name]
        verdict = read(suite, names, _rules(doc.get("rules"))).verdict
        if verdict != doc.get("verdict"):
            raise CardError(
                f"the card says {doc.get('verdict')!r}, but its result gives {verdict!r}"
            )
        case_dirs = paths.get("caseDirs") or []
        model = tested.get("model")
    except (ResultError, CardError, PathError, OSError) as e:
        return Evidence("broken", note=str(e))
    assert verdict in VERDICTS
    try:
        skill_ok = hashes.get("skill") == hash_skill(version_folder, case_dirs)
    except PathError as e:
        return Evidence("broken", note=str(e))
    if not skill_ok:
        return Evidence("stale", verdict, model, "the card was made for other files")
    note = None
    cases = cases_dir(card_dir)
    try:
        if cases is None or not within(cases, source_root) or not cases.is_dir():
            note = "the eval cases aren't in the source, so only the skill was checked"
        elif hash_cases(cases, case_dirs) != hashes.get("cases"):
            note = "the eval cases changed since the card was made"
    except PathError as e:
        note = f"the eval cases couldn't be checked: {e}"
    if note:
        return Evidence("cases-changed", verdict, model, note)
    return Evidence("current", verdict, model)
