# Simulation: the verdict rules on skills with a known effect

Written by `scripts/simulate.py` (seed 20261005, 200 simulated suites per row, 3 runs per
side per case). No model was called. Rerun the script to reproduce it exactly.

Each case passes a run without the skill with probability 0.2, 0.4 or 0.6, picked per case,
and with the skill with that probability plus the skill's true gain. A placebo's gain is
zero, so any Helps or Hurts for a placebo is a false call.

Rules: at least 5 cases, a 90% bootstrap interval, a
minimum effect of 10 points.

| True effect | Cases | Helps | Hurts | Inconclusive | Other |
|---|---|---|---|---|---|
| placebo | 5 | 1% | 2% | 98% | 0% |
| placebo | 10 | 2% | 0% | 97% | 0% |
| placebo | 15 | 2% | 2% | 96% | 0% |
| +20 points | 5 | 14% | 0% | 86% | 0% |
| +20 points | 10 | 35% | 0% | 65% | 0% |
| +20 points | 15 | 52% | 0% | 48% | 0% |
| +40 points | 5 | 66% | 0% | 34% | 0% |
| +40 points | 10 | 94% | 0% | 6% | 0% |
| +40 points | 15 | 99% | 0% | 1% | 0% |

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
