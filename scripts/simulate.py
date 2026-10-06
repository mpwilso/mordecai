"""Tests the verdict rules on simulated skills whose true effect is known, and writes the
recalibration section of docs/simulation.md.

    uv run python scripts/simulate.py                    both settings, written to the doc
    uv run python scripts/simulate.py --agreement 0.94   print one setting, write nothing

No model is called. Each simulated suite has cases of mixed difficulty: a case passes without
the skill with probability p (0.2, 0.4 or 0.6, picked per case), and with the skill with
probability p plus the skill's true gain. A placebo has a gain of zero. Every run is scored
pass or fail, as a single regex or test grader would score it. Seeds are fixed, so the output is
the same every time.

Two ways to draw a case's runs:

- independent: every run is its own coin flip, so three runs agree only about a third of the
  time. This is the setting the first simulation used (the table at the top of the doc,
  written at f43421b with the 0.1.0 rules and kept as it was).
- agreement A: each case has one outcome per side, drawn once, and shared by both sides
  unless the skill changes it. Each run then repeats that outcome, flipping with a small
  probability chosen so that all three runs of a side agree with probability A. The planted
  skills check measured A = 0.94.

This checks the rules, not the eval: it says nothing about whether real graders, prompts or
models behave like either setting.
"""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

from builder import make_result  # noqa: E402

from mordecai import __version__  # noqa: E402
from mordecai.result import parse  # noqa: E402
from mordecai.verdict import DEFAULT_RULES, read  # noqa: E402

TRIALS = 200
SEED = 20261005
CONFIGS = [(gain, cases) for gain in (0.0, 0.2, 0.4) for cases in (5, 10, 15)]
OBSERVED_AGREEMENT = 0.94
MARKER = "<!-- Everything below this line is written by scripts/simulate.py. -->"


def flip_rate(agreement: float, runs: int = 3) -> float:
    """The per-run flip probability e with (1 - e)^runs + e^runs = agreement, by bisection."""
    lo, hi = 0.0, 0.5
    for _ in range(60):
        e = (lo + hi) / 2
        if (1 - e) ** runs + e**runs > agreement:
            lo = e
        else:
            hi = e
    return (lo + hi) / 2


def independent_case(p, gain, runs, rng):
    w = [1 if rng.random() < min(1.0, p + gain) else 0 for _ in range(runs)]
    b = [1 if rng.random() < p else 0 for _ in range(runs)]
    return w, b


def agreement_case(p, gain, runs, rng, e):
    base = 1 if rng.random() < p else 0
    # The skill turns a failing case into a passing one with probability gain / (1 - p), so
    # a case passes with the skill with probability p + gain, as in the independent setting.
    with_ = 1 if base or rng.random() < gain / (1 - p) else 0

    def runs_of(outcome):
        return [outcome if rng.random() >= e else 1 - outcome for _ in range(runs)]

    return runs_of(with_), runs_of(base)


def simulate(gain, n_cases, runs, rng, e=None):
    counts: dict[str, int] = {}
    cells = agreed = 0
    for _ in range(TRIALS):
        cases = []
        for i in range(n_cases):
            p = rng.choice((0.2, 0.4, 0.6))
            if e is None:
                w, b = independent_case(p, gain, runs, rng)
            else:
                w, b = agreement_case(p, gain, runs, rng, e)
            cells += 2
            agreed += (len(set(w)) == 1) + (len(set(b)) == 1)
            cases.append({"name": f"c{i}", "with": w, "without": b, "fired": [True] * runs})
        v = read(parse(make_result(cases))).verdict
        counts[v] = counts.get(v, 0) + 1
    return counts, agreed / cells


def pct(n: int) -> str:
    return f"{round(100 * n / TRIALS)}%"


def table(e, seed):
    rng = random.Random(seed)
    rows, rates, counts = [], [], {}
    for gain, n in CONFIGS:
        c, agree = simulate(gain, n, 3, rng, e)
        counts[(gain, n)] = c
        rates.append(agree)
        other = TRIALS - c.get("helps", 0) - c.get("hurts", 0) - c.get("inconclusive", 0)
        rows.append(
            f"| {'placebo' if gain == 0 else f'+{round(gain * 100)} points'} | {n} | "
            f"{pct(c.get('helps', 0))} | {pct(c.get('hurts', 0))} | "
            f"{pct(c.get('inconclusive', 0))} | {pct(other)} |"
        )
        print(rows[-1], flush=True)
    header = (
        "| True effect | Cases | Helps | Hurts | Inconclusive | Other |\n"
        "|---|---|---|---|---|---|\n"
    )
    return header + "\n".join(rows), sum(rates) / len(rates), counts


def main(argv: list[str]) -> int:
    if "--agreement" in argv:
        a = float(argv[argv.index("--agreement") + 1])
        table(flip_rate(a), SEED + 1)
        return 0
    e = flip_rate(OBSERVED_AGREEMENT)
    independent, ind_rate, ind = table(None, SEED)
    agreeing, agr_rate, agr = table(e, SEED + 1)

    def helps(c, gain, n):
        return pct(c[(gain, n)].get("helps", 0))

    def other(c, n):
        k = c[(0.0, n)]
        return pct(TRIALS - k.get("helps", 0) - k.get("hurts", 0) - k.get("inconclusive", 0))

    def false_calls(c):
        return max(c[(0.0, n)].get("helps", 0) + c[(0.0, n)].get("hurts", 0) for n in (5, 10, 15))

    r = DEFAULT_RULES
    section = f"""{MARKER}

## Recalibration: the rules on runs that agree like real runs

Written by `scripts/simulate.py` with the {__version__} rules (at least {r.min_cases} cases, a
{round(r.confidence * 100)}% interval, a {round(r.min_effect * 100)}-point minimum effect), {TRIALS}
simulated suites per row, 3 runs per side per case. The table at the top of this file is kept
as it was; its "rerun the script" note refers to the script at f43421b, and the independent
rows below reproduce it with the current script and rules.

The planted skills check ([planted-skills-results.md](planted-skills-results.md)) found that
all three runs of a side agreed in 94% of case-and-side cells. Independent coin flips agree far
less often. So this section runs both settings with the current rules:

- **Independent runs**, as above, rerun with the {__version__} rules. Simulated agreement:
  {round(ind_rate * 100)}%.
- **94% agreement**: each case has one outcome per side, and each run repeats it, flipping with
  probability {e:.4f}. A placebo's two sides share the same outcome. Simulated agreement:
  {round(agr_rate * 100)}%.

### Independent runs, {__version__} rules

{independent}

### 94% run agreement, {__version__} rules

{agreeing}

## What the recalibration says

- **Which assumption real runs matched:** the 94% agreement setting. The first simulation's
  independent coin flips agree about a third of the time; real runs agreed 94% of the time.
- **The +20 point finding survives.** A skill worth +20 points is called Helps in
  {helps(agr, 0.2, 5)}, {helps(agr, 0.2, 10)} and {helps(agr, 0.2, 15)} of suites at 5, 10 and 15
  cases with 94% agreement, against {helps(ind, 0.2, 5)}, {helps(ind, 0.2, 10)} and
  {helps(ind, 0.2, 15)} with independent runs. Making runs agree barely moves it, because the
  uncertainty that remains is between cases: a +20 point skill changes the outcome of only
  some cases, and the interval is drawn over cases.
- **Placebos get fewer false calls when runs agree.** The most Helps or Hurts calls for a
  placebo at any size was {pct(false_calls(agr))} with 94% agreement and
  {pct(false_calls(ind))} with independent runs. With agreeing runs, a placebo often comes out
  No effect or Already handled (the Other column) rather than Inconclusive: {other(agr, 5)},
  {other(agr, 10)} and {other(agr, 15)} of suites at 5, 10 and 15 cases.
- **Large effects are still found:** +40 points is called Helps in {helps(agr, 0.4, 10)} of
  suites at 10 cases and {helps(agr, 0.4, 15)} at 15 with 94% agreement.
"""
    doc = ROOT / "docs" / "simulation.md"
    text = doc.read_text(encoding="utf-8")
    head = text.split(MARKER)[0].rstrip("\n") + "\n\n"
    doc.write_text(head + section, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
