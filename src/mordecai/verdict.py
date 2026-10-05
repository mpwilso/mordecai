"""Decides what an eval result lets a skill claim. Code decides, not a model.

The order is fixed, and the first rule that applies wins:

1. Invalid: the eval stopped early, hit a usage or rate limit, skipped its judge graders, or
   has no baseline to compare against. Nothing can be read from it.
2. Never fired: the skill didn't fire in any run where it should have.
3. Inconclusive: fewer cases were compared than the rules need.
4. Hurts: the whole interval for the change is below zero.
5. Helps: the whole interval is above zero, and the change is at least the minimum effect.
6. Already handled: the model scores at least the ceiling without the skill, and the interval
   rules out both a gain and a loss as big as the minimum effect.
7. Inconclusive: the model scores at least the ceiling without the skill, but the interval
   doesn't rule out a loss as big as the minimum effect.
8. No effect: the interval sits inside plus or minus the minimum effect.
9. Inconclusive: anything else. The interval is too wide to call.

Rules 6 and 7 changed in 0.2.0. Before, Already handled checked only for a gain, and in the
planted skills check it gave a skill that did harm whenever it fired a calm label
(docs/planted-skills-results.md, suite 3). The change was designed after seeing that result.

Cases that check the skill does *not* fire (a Skill grader with max: 0) are left out of the
change and reported as misfires instead, since the run without the skill passes them by
construction.
"""

import random
import re
from dataclasses import dataclass, field

from mordecai.result import Case, Suite

VERDICTS = (
    "helps",
    "hurts",
    "already-handled",
    "no-effect",
    "inconclusive",
    "never-fired",
    "invalid",
)

# Errors that mean the run says nothing about the skill. The docs warn that a run which hits
# a limit is still graded, usually scores 0, and doesn't mark the suite partial.
LIMIT_ERROR = re.compile(
    r"rate.?limit|usage limit|quota|overloaded|\b429\b|\b529\b|credit balance", re.IGNORECASE
)


@dataclass(frozen=True)
class Rules:
    min_cases: int = 5
    min_effect: float = 0.10  # ten points on a 0 to 100 scale
    ceiling: float = 0.90
    confidence: float = 0.90
    resamples: int = 2000
    seed: int = 0


DEFAULT_RULES = Rules()


@dataclass(frozen=True)
class Reading:
    verdict: str
    reason: str
    cases_compared: int
    improved: int
    flat: int
    worse: int
    with_score: float | None
    without_score: float | None
    change: float | None
    interval: tuple[float, float] | None
    fired: tuple[int, int] | None  # runs where it fired, runs where it should have
    misfired: tuple[int, int] | None  # runs where it fired, runs where it shouldn't have
    cost_with: float | None  # mean agent cost per run, list price
    cost_without: float | None
    turns_with: float | None
    turns_without: float | None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _mean(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _pts(x: float) -> str:
    return f"{round(x * 100):+d}"


def case_change(case: Case) -> float:
    return _mean(r.score for r in case.with_runs) - _mean(r.score for r in case.without_runs)


def interval(cases: list[Case], rules: Rules) -> tuple[float, float]:
    """A bootstrap interval for the mean change. Each resample draws cases with replacement,
    then runs with replacement inside each arm of each case, so it carries both the spread
    between cases and the spread between runs. A fixed seed makes it repeatable."""
    rng = random.Random(rules.seed)
    n = len(cases)
    arms = [([r.score for r in c.with_runs], [r.score for r in c.without_runs]) for c in cases]
    means = []
    for _ in range(rules.resamples):
        total = 0.0
        for _ in range(n):
            w, b = arms[rng.randrange(n)]
            total += sum(rng.choice(w) for _ in w) / len(w)
            total -= sum(rng.choice(b) for _ in b) / len(b)
        means.append(total / n)
    means.sort()
    tail = (1 - rules.confidence) / 2
    lo = means[int(tail * rules.resamples)]
    hi = means[min(rules.resamples - 1, int((1 - tail) * rules.resamples))]
    return round(lo, 4), round(hi, 4)


def _problems(suite: Suite) -> list[str]:
    problems = []
    if suite.partial:
        problems.append(f"The eval stopped early ({suite.partial_reason or 'no reason given'}).")
    runs = [r for c in suite.cases for r in c.with_runs + c.without_runs]
    limited = sum(1 for r in runs if r.error and LIMIT_ERROR.search(r.error))
    if limited:
        problems.append(f"{limited} of {len(runs)} runs hit a usage or rate limit.")
    skipped = sum(1 for r in runs if r.skipped_paid)
    if skipped:
        problems.append(f"{skipped} of {len(runs)} runs skipped their judge graders.")
    if not any(c.compared for c in suite.cases):
        problems.append("No case ran without the skill, so there is nothing to compare.")
    return problems


def case_warnings(
    cases: list[Case], effect: list[Case], run_counts: list[int], skill_names: list[str]
) -> list[str]:
    """Warnings about the cases themselves, which `mordecai lint` also runs on case files
    before an eval. run_counts holds the runs per side for each effect case."""
    warnings = []
    few = sorted({n for n in run_counts if n < 3})
    if few:
        warnings.append(
            f"Some cases ran {few[0]} time(s) per side. The interval leans on repeat runs; "
            "use at least 3."
        )
    if not any(c.trigger == "should-not-fire" for c in cases):
        warnings.append(
            "No case checks that the skill stays quiet when it isn't needed. Add one with a "
            "tool_used Skill grader, min: 0, max: 0 and arm: both."
        )
    if not any(c.trigger == "should-fire" for c in effect):
        warnings.append(
            "No case checks that the skill fired, so a change can't be tied to the skill. "
            "Add a tool_used grader on the Skill tool."
        )
    named = []
    for c in effect:
        prompt = c.prompt.lower()
        for s in skill_names:
            if s and (s.lower() in prompt or s.lower().replace("-", " ") in prompt):
                named.append(c.name)
                break
    if named:
        warnings.append(
            f"{len(named)} case prompt(s) name the skill ({', '.join(named[:3])}). That tests "
            "whether the model follows an instruction, not whether it finds the skill."
        )
    return warnings


def _warnings(suite: Suite, effect: list[Case], skill_names: list[str], rules: Rules):
    warnings = []
    model = suite.model or ""
    if not model.startswith("claude-"):
        shown = model or "Claude Code's default"
        warnings.append(
            f"The model was {shown}, not a pinned model ID, so a later model can change "
            "this result without anything in the card changing. Pass --model with a full ID."
        )
    runs = [r for c in suite.cases for r in c.with_runs + c.without_runs]
    errored = sum(1 for r in runs if r.error and not LIMIT_ERROR.search(r.error))
    if errored:
        warnings.append(
            f"{errored} of {len(runs)} runs ended with an error. They were graded on what "
            "they produced."
        )
    # Counted from the runs themselves: --runs overrides the case's own runs setting.
    counts = [min(len(c.with_runs), len(c.without_runs)) for c in effect]
    warnings += case_warnings(suite.cases, effect, counts, skill_names)
    return warnings


def read(
    suite: Suite, skill_names: list[str] | None = None, rules: Rules = DEFAULT_RULES
) -> Reading:
    effect = [c for c in suite.cases if c.compared and c.trigger != "should-not-fire"]
    quiet = [c for c in suite.cases if c.trigger == "should-not-fire"]

    fire_runs = [r for c in effect for r in c.with_runs if r.fired is not None]
    fired = (sum(1 for r in fire_runs if r.fired), len(fire_runs)) if fire_runs else None
    quiet_runs = [r for c in quiet for r in c.with_runs if r.misfired is not None]
    misfired = (sum(1 for r in quiet_runs if r.misfired), len(quiet_runs)) if quiet_runs else None

    changes = [case_change(c) for c in effect]
    with_runs = [r for c in effect for r in c.with_runs]
    without_runs = [r for c in effect for r in c.without_runs]
    base = dict(
        cases_compared=len(effect),
        improved=sum(1 for d in changes if d >= rules.min_effect),
        worse=sum(1 for d in changes if d <= -rules.min_effect),
        flat=sum(1 for d in changes if -rules.min_effect < d < rules.min_effect),
        with_score=_mean(_mean(r.score for r in c.with_runs) for c in effect),
        without_score=_mean(_mean(r.score for r in c.without_runs) for c in effect),
        change=_mean(changes),
        fired=fired,
        misfired=misfired,
        cost_with=_mean(r.cost_usd for r in with_runs),
        cost_without=_mean(r.cost_usd for r in without_runs),
        turns_with=_mean(r.turns for r in with_runs),
        turns_without=_mean(r.turns for r in without_runs),
        warnings=tuple(_warnings(suite, effect, skill_names or [], rules)),
    )

    def verdict(name, reason, iv=None):
        return Reading(verdict=name, reason=reason, interval=iv, **base)

    problems = _problems(suite)
    if problems:
        return verdict("invalid", " ".join(problems))
    if fired and fired[0] == 0:
        return verdict(
            "never-fired",
            f"The skill didn't fire in any of the {fired[1]} runs where it should have.",
        )
    if len(effect) < rules.min_cases:
        return verdict(
            "inconclusive",
            f"Only {len(effect)} case(s) were compared; the rules need at least {rules.min_cases}.",
        )

    lo, hi = iv = interval(effect, rules)
    span = f"{_pts(lo)} to {_pts(hi)} points"
    conf = f"{round(rules.confidence * 100)}%"
    change = base["change"]
    if hi < 0:
        return verdict("hurts", f"The skill lowered the score: {conf} interval {span}.", iv)
    if lo > 0 and change >= rules.min_effect:
        return verdict("helps", f"The skill raised the score: {conf} interval {span}.", iv)
    if base["without_score"] >= rules.ceiling and hi < rules.min_effect:
        scored = f"The model scored {round(base['without_score'] * 100)}% without the skill"
        if lo > -rules.min_effect:
            return verdict(
                "already-handled",
                f"{scored}, and the {conf} interval ({span}) rules out a gain or a loss of "
                f"{round(rules.min_effect * 100)} points.",
                iv,
            )
        return verdict(
            "inconclusive",
            f"{scored}, but the {conf} interval ({span}) doesn't rule out a loss of "
            f"{round(rules.min_effect * 100)} points.",
            iv,
        )
    if lo > -rules.min_effect and hi < rules.min_effect:
        return verdict(
            "no-effect",
            f"The {conf} interval ({span}) stays inside plus or minus "
            f"{round(rules.min_effect * 100)} points.",
            iv,
        )
    return verdict("inconclusive", f"The {conf} interval runs {span}, too wide to call.", iv)
