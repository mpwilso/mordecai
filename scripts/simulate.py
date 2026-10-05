"""Tests the verdict rules on simulated skills whose true effect is known, and writes
docs/simulation.md.

    uv run python scripts/simulate.py

No model is called. Each simulated suite has cases of mixed difficulty: a case passes a run
without the skill with probability p (0.2, 0.4 or 0.6, picked per case), and with the skill
with probability p plus the skill's true gain. A placebo has a gain of zero. Every run is
scored pass or fail, as a single regex or test grader would score it. The seed is fixed, so
the file is the same every time.

This checks the rules, not the eval: it says nothing about whether real graders, prompts or
models behave like coin flips.
"""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

from builder import make_result  # noqa: E402

from mordecai.result import parse  # noqa: E402
from mordecai.verdict import DEFAULT_RULES, read  # noqa: E402

TRIALS = 200
SEED = 20261005
CONFIGS = [(gain, cases) for gain in (0.0, 0.2, 0.4) for cases in (5, 10, 15)]


def simulate(gain: float, n_cases: int, runs: int, rng: random.Random) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _ in range(TRIALS):
        cases = []
        for i in range(n_cases):
            p = rng.choice((0.2, 0.4, 0.6))
            w = [1 if rng.random() < min(1.0, p + gain) else 0 for _ in range(runs)]
            b = [1 if rng.random() < p else 0 for _ in range(runs)]
            cases.append({"name": f"c{i}", "with": w, "without": b, "fired": [True] * runs})
        v = read(parse(make_result(cases))).verdict
        counts[v] = counts.get(v, 0) + 1
    return counts


def pct(n: int) -> str:
    return f"{round(100 * n / TRIALS)}%"


def main() -> int:
    rng = random.Random(SEED)
    rows = []
    for gain, n in CONFIGS:
        c = simulate(gain, n, 3, rng)
        rows.append(
            f"| {'placebo' if gain == 0 else f'+{round(gain * 100)} points'} | {n} | "
            f"{pct(c.get('helps', 0))} | {pct(c.get('hurts', 0))} | "
            f"{pct(c.get('inconclusive', 0))} | "
            f"{pct(TRIALS - c.get('helps', 0) - c.get('hurts', 0) - c.get('inconclusive', 0))} |"
        )
        print(rows[-1], flush=True)
    r = DEFAULT_RULES
    text = f"""# Simulation: the verdict rules on skills with a known effect

Written by `scripts/simulate.py` (seed {SEED}, {TRIALS} simulated suites per row, 3 runs per
side per case). No model was called. Rerun the script to reproduce it exactly.

Each case passes a run without the skill with probability 0.2, 0.4 or 0.6, picked per case,
and with the skill with that probability plus the skill's true gain. A placebo's gain is
zero, so any Helps or Hurts for a placebo is a false call.

Rules: at least {r.min_cases} cases, a {round(r.confidence * 100)}% bootstrap interval, a
minimum effect of {round(r.min_effect * 100)} points.

| True effect | Cases | Helps | Hurts | Inconclusive | Other |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## What it says

- A placebo is called Helps or Hurts only a few times in a hundred. The rules rarely claim an
  effect that isn't there.
- The price is that real effects are often called Inconclusive. With pass or fail graders
  and 3 runs per side, a skill worth +20 points needs well over 15 cases to be called Helps
  reliably. A card that says Inconclusive is usually saying "measure more", not "it doesn't
  work".
- No effect is almost never reached here, because pass or fail runs are too noisy to prove
  an effect is near zero. Graders that give partial credit, or more runs, narrow the interval.

## What it doesn't say

Real runs aren't coin flips. Cases share causes (one bad instruction can fail several),
judges disagree with themselves, and a model update moves everything at once. The planted
skills check, run against real evals, is what tests the rules against that.
"""
    (ROOT / "docs" / "simulation.md").write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
