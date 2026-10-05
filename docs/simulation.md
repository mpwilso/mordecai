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

<!-- Everything below this line is written by scripts/simulate.py. -->

## Recalibration: the rules on runs that agree like real runs

Written by `scripts/simulate.py` with the 0.2.0 rules (at least 5 cases, a
90% interval, a 10-point minimum effect), 200
simulated suites per row, 3 runs per side per case. The table at the top of this file is kept
as it was; its "rerun the script" note refers to the script at 519708f, and the independent
rows below reproduce it with the current script and rules.

The planted skills check ([planted-skills-results.md](planted-skills-results.md)) found that
all three runs of a side agreed in 94% of case-and-side cells. Independent coin flips agree far
less often. So this section runs both settings with the current rules:

- **Independent runs**, as above, rerun with the 0.2.0 rules. Simulated agreement:
  40%.
- **94% agreement**: each case has one outcome per side, and each run repeats it, flipping with
  probability 0.0204. A placebo's two sides share the same outcome. Simulated agreement:
  94%.

### Independent runs, 0.2.0 rules

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

### 94% run agreement, 0.2.0 rules

| True effect | Cases | Helps | Hurts | Inconclusive | Other |
|---|---|---|---|---|---|
| placebo | 5 | 0% | 0% | 41% | 59% |
| placebo | 10 | 0% | 0% | 73% | 27% |
| placebo | 15 | 0% | 0% | 36% | 64% |
| +20 points | 5 | 13% | 0% | 68% | 20% |
| +20 points | 10 | 36% | 0% | 59% | 4% |
| +20 points | 15 | 56% | 0% | 44% | 1% |
| +40 points | 5 | 40% | 0% | 56% | 4% |
| +40 points | 10 | 80% | 0% | 20% | 0% |
| +40 points | 15 | 96% | 0% | 4% | 0% |

## What the recalibration says

- **Which assumption real runs matched:** the 94% agreement setting. The first simulation's
  independent coin flips agree about a third of the time; real runs agreed 94% of the time.
- **The +20 point finding survives.** A skill worth +20 points is called Helps in
  13%, 36% and 56% of suites at 5, 10 and 15
  cases with 94% agreement, against 14%, 35% and
  52% with independent runs. Making runs agree barely moves it, because the
  uncertainty that remains is between cases: a +20 point skill changes the outcome of only
  some cases, and the interval is drawn over cases.
- **Placebos get fewer false calls when runs agree.** The most Helps or Hurts calls for a
  placebo at any size was 0% with 94% agreement and
  4% with independent runs. With agreeing runs, a placebo often comes out
  No effect or Already handled (the Other column) rather than Inconclusive: 59%,
  27% and 64% of suites at 5, 10 and 15 cases.
- **Large effects are still found:** +40 points is called Helps in 80% of
  suites at 10 cases and 96% at 15 with 94% agreement.
