"""Turns a card into text: plain for terminals and logs, Markdown for pull requests, and crawl
mode for fun.

Crawl mode only adds lines around the plain card's stat block, from fixed templates. It never
computes anything, so it can't show a different number or verdict. tests/test_card.py pins
that the stat block is identical in every mode.

Names, models, reasons and warnings can carry text from a result someone else wrote. Every mode
prints them through clean(), so they can't send terminal escapes or start a new line.
"""

from dataclasses import replace

from mordecai.card import Card

DOT = " " + chr(0xB7) + " "  # a middle dot between facts on one line

LABEL = {
    "helps": "Helps",
    "hurts": "Hurts",
    "already-handled": "Already handled",
    "no-effect": "No effect",
    "inconclusive": "Inconclusive",
    "never-fired": "Never fired",
    "invalid": "Invalid",
}

NEXT = {
    "helps": "Keep it.",
    "hurts": "Remove it, or find the cases it breaks and fix the skill.",
    "already-handled": "Remove it, or add cases where the model fails without it.",
    "no-effect": "It isn't changing results on these cases. Decide whether it's worth the context.",
    "inconclusive": "Add cases or runs, then measure again.",
    "never-fired": "Rewrite the skill's description so the model knows when to use it.",
    "invalid": "Fix the problem above and run the eval again.",
}


# Control characters, and the Unicode marks that reorder text or break a line. clean() prints
# them as escapes such as \x1b, so a crafted name can't move the cursor, recolor or clear the
# screen, add a line that looks like a verdict, or reverse what follows it.
UNSAFE = frozenset(
    [*range(0x20), *range(0x7F, 0xA0), 0x061C, 0x200E, 0x200F, 0x2028, 0x2029]
    + [*range(0x202A, 0x202F), *range(0x2066, 0x206A)]
)


def clean(text: str) -> str:
    """text with every unsafe character written as a visible escape. Safe to apply twice."""
    return "".join(
        (f"\\x{ord(c):02x}" if ord(c) < 0x100 else f"\\u{ord(c):04x}") if ord(c) in UNSAFE else c
        for c in text
    )


def _clean_or_none(text: str | None) -> str | None:
    return None if text is None else clean(text)


def _safe(card: Card) -> Card:
    """The card with every field that can come from a result made printable."""
    r = card.reading
    return replace(
        card,
        plugin=clean(card.plugin),
        version=_clean_or_none(card.version),
        skills=tuple(clean(s) for s in card.skills),
        model=_clean_or_none(card.model),
        judge_model=_clean_or_none(card.judge_model),
        claude_version=_clean_or_none(card.claude_version),
        started_at=_clean_or_none(card.started_at),
        reading=replace(r, reason=clean(r.reason), warnings=tuple(clean(w) for w in r.warnings)),
    )


def _pct(x: float | None) -> str:
    return "?" if x is None else f"{round(x * 100)}%"


def _pts(x: float) -> str:
    return f"{round(x * 100):+d}"


def _usd(x: float | None) -> str:
    return "?" if x is None else f"${x:.3f}"


def _short(h: str | None) -> str:
    return "none" if not h else h[:19]


def stat_block(card: Card) -> list[str]:
    """The facts, the same in every mode."""
    card = _safe(card)
    r = card.reading
    lines = []
    if r.change is not None:
        line = f"With {_pct(r.with_score)}{DOT}Without {_pct(r.without_score)}"
        line += f"{DOT}Change {_pts(r.change)} pts"
        if r.interval:
            line += f" (90% interval {_pts(r.interval[0])} to {_pts(r.interval[1])})"
        lines.append(line)
        lines.append(
            f"Cases {r.cases_compared}: {r.improved} better, {r.flat} same, {r.worse} worse"
        )
    trigger = []
    if r.fired:
        trigger.append(f"Fired in {r.fired[0]} of {r.fired[1]} runs that needed it")
    if r.misfired:
        trigger.append(f"fired in {r.misfired[0]} of {r.misfired[1]} runs that didn't")
    if trigger:
        lines.append(", ".join(trigger))
    if r.cost_with is not None and r.cost_without is not None:
        cost = f"Cost per run {_usd(r.cost_with)} with, {_usd(r.cost_without)} without"
        if r.cost_without:
            cost += f" ({round((r.cost_with / r.cost_without - 1) * 100):+d}%)"
        if r.turns_with is not None and r.turns_without is not None:
            cost += f"{DOT}Turns {r.turns_with:.1f} with, {r.turns_without:.1f} without"
        lines.append(cost)
    tested = [f"Tested on {card.model or 'the default model'}"]
    if card.judge_model:
        tested.append(f"judge {card.judge_model}")
    if card.claude_version:
        tested.append(f"Claude Code {card.claude_version}")
    if card.started_at:
        tested.append(card.started_at[:10])
    lines.append(DOT.join(tested))
    lines.append(
        f"Skill {_short(card.skill_hash)}{DOT}Cases {_short(card.cases_hash)}"
        f"{DOT}Result {_short(card.result_hash)}"
    )
    return lines


def _warnings(card: Card) -> list[str]:
    if not card.reading.warnings:
        return []
    return ["", "Warnings"] + [f"  - {w}" for w in card.reading.warnings]


def plain(card: Card) -> str:
    card = _safe(card)
    r = card.reading
    lines = [f"{card.title}: {LABEL[r.verdict]}", r.reason, ""]
    lines += ["  " + s for s in stat_block(card)]
    lines += _warnings(card)
    lines += ["", f"Next: {NEXT[r.verdict]}"]
    return "\n".join(lines) + "\n"


def markdown(card: Card) -> str:
    card = _safe(card)
    r = card.reading
    lines = [f"### {card.title}: {LABEL[r.verdict]}", "", r.reason, "", "```"]
    lines += stat_block(card)
    lines += ["```"]
    if r.warnings:
        lines += ["", "**Warnings**", ""] + [f"- {w}" for w in r.warnings]
    lines += ["", f"**Next:** {NEXT[r.verdict]}"]
    return "\n".join(lines) + "\n"


# Crawl mode ------------------------------------------------------------------------------------

RARITY = {
    "helps": "ENCHANTED ({pts})",
    "hurts": "CURSED ({pts})",
    "already-handled": "VENDOR TRASH",
    "no-effect": "PLACEBO",
    "inconclusive": "UNIDENTIFIED",
    "never-fired": "NEVER EQUIPPED",
    "invalid": "CORRUPTED",
}

# (achievement title, what the dungeon says, what Mordecai says). Only {n}, {runs} and {pts}
# may appear, and they come from the same reading as the stat block.
CRAWL = {
    "helps": (
        "Actually Useful",
        "You found a skill that does what it says on the box. Savor it. It won't happen often.",
        "Keep it. It earned its slot: {pts} points over {n} cases.",
    ),
    "hurts": (
        "Self-Inflicted",
        "You equipped a skill that made things worse. The dungeon didn't even have to try.",
        "Take it off before it costs you anything else.",
    ),
    "already-handled": (
        "Paperweight",
        "The model handles these cases fine without it. You're carrying this for the aesthetic.",
        "Drop it, or go find the cases where the model fails without it.",
    ),
    "no-effect": (
        "Sugar Pill",
        "Equipping this skill changed nothing anyone could measure. Placebo is not a stat.",
        "It isn't hurting you. It isn't helping you. Decide if it's worth the slot.",
    ),
    "inconclusive": (
        "Results May Vary",
        "The dungeon can't tell what this thing does yet. Neither can you.",
        "Not enough to go on. More cases, more runs, then bring it back to me.",
    ),
    "never-fired": (
        "Left in the Bag",
        "You carried this skill through {runs} runs and never once took it out.",
        "Your description isn't doing its job. Fix it so the model knows when to reach for this.",
    ),
    "invalid": (
        "Corrupted Save",
        "Something broke before anything could be measured. Congratulations?",
        "This reading's no good. Fix what broke and run it again.",
    ),
}


# ANSI colors for the rarity, used only when writing to a terminal that allows color.
COLOR = {
    "helps": "1;33",  # bold yellow: loot worth keeping
    "hurts": "1;35",  # bold magenta: cursed
    "already-handled": "2",  # dim: vendor trash
    "no-effect": "2",
    "inconclusive": "1;36",  # bold cyan: unidentified
    "never-fired": "2",
    "invalid": "1;31",  # bold red: corrupted
}


def crawl(card: Card, width: int = 64, color: bool = False) -> str:
    card = _safe(card)
    r = card.reading
    pts = _pts(r.change) if r.change is not None else "+0"
    fields = {"n": r.cases_compared, "runs": r.fired[1] if r.fired else 0, "pts": pts}
    title, blurb, quote = CRAWL[r.verdict]
    rarity = RARITY[r.verdict].format(**fields)
    dots = "." * max(3, width - len(card.title) - len(rarity) - 2)
    lines = [f"NEW ACHIEVEMENT! {title}.", blurb.format(**fields), r.reason, ""]
    shown = f"\033[{COLOR[r.verdict]}m{rarity}\033[0m" if color else rarity
    lines += [f"  {card.title} {dots} {shown}"]
    lines += ["  " + s for s in stat_block(card)]
    lines += _warnings(card)
    lines += ["", f'Mordecai: "{quote.format(**fields)}"']
    return "\n".join(lines) + "\n"
