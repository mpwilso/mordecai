# The verdicts in detail

The README lists the verdicts in a sentence. This page has the table, how the interval works, the warnings, how refusals are read, a second example card, and every change to the rules. The rules themselves are [src/mordecai/verdict.py](../src/mordecai/verdict.py), and each change has a decision in [decisions.md](decisions.md).

## The rules

Code decides, not a model. The rules run in this order, and the earliest one that applies wins.

| Verdict | When |
|---|---|
| Invalid | The eval stopped early, a run hit a usage or rate limit, judge graders were skipped, or nothing ran without the skill |
| Never fired | The skill didn't fire in any run where it should have |
| Rarely fired | The skill fired in under 10% of the runs where it should have |
| Inconclusive | Fewer than 5 cases were compared |
| Hurts | The whole 90% interval for the change is below zero |
| Helps | The whole interval is above zero, and the change is at least 10 points |
| Already handled | At least 10 cases, the model scores at least 90% without the skill, and the interval rules out both a 10-point gain and a 10-point loss |
| Inconclusive | The model scores at least 90% without the skill, but the interval doesn't rule out a 10-point loss |
| No effect | At least 10 cases, and the interval stays inside plus or minus 10 points |
| Inconclusive | Anything else: the interval is too wide to call |

Warnings never change the verdict.

## The interval

The interval is a bootstrap over cases, and over runs inside each case, with a fixed seed, so the same result always gives the same card. When every case has the same change and every run agrees, the bootstrap can only return that one number, so the card says "9 of 9 cases" instead, with an exact binomial bound on how many cases like these could differ (23% for 9 cases at 90%). The card's JSON records this as `numbers.agreement`, with `interval` null. A No effect or Already handled card with fewer than 10 cases is Inconclusive. Cases that check the skill stays quiet are left out of the change and reported as misfires.

## Warnings

Every card also lists warnings that don't change the verdict: a skill that fired in at least 10% but under half of the runs where it should have (the change then mostly reflects runs that didn't use it), a model alias instead of a pinned ID, runs that ended with an error other than a usage or rate limit, runs that had a tool call refused by permissions (with how many on each side), fewer than 3 runs per side, no case that checks the skill stays quiet, no case that checks it fired, and case prompts that name the skill (which tests whether the model follows an instruction, not whether it finds the skill). `mordecai lint` runs the last four checks on case files before an eval.

## Refused tool calls

A refused tool call leaves the run's `error` empty, and the result JSON has no field for it, so Mordecai reads it from each run's trace (`tracePath`): the `permission_denials` list in the trace's result message. It reads a trace only if it is inside the current directory or the `--skill` directory, as with every other path a result names. If the run had the tool and the refused call aimed inside the run's own working folder or the skill's folder, the setup decided the run, not the skill, and the card is Invalid; a refusal anywhere else is a warning. `claude plugin eval` writes traces to a temporary folder by default, so a card made after that folder is gone can't see refusals, and it says so: without the traces a card can't tell a refused tool call from a skill that did badly. A refusal outside those folders never changes the verdict; whether it should is [open question 4](open-questions.md#open-question-4-runs-that-say-nothing-about-the-skill).

## One case is not evidence

This is a one-case eval of a tiny skill, run once while building Mordecai to capture the result format ([tests/fixtures/probe-result.json](../tests/fixtures/probe-result.json), skill and case in [tests/fixtures/probe/](../tests/fixtures/probe/)). The skill went from 0% to 100%, and the card still won't call it Helps. Its warnings are cut here.

```
$ uv run mordecai identify tests/fixtures/probe-result.json --skill tests/fixtures/probe
schema-probe 0.0.1: Inconclusive
Only 1 case(s) were compared; the rules need at least 5.

  With 100% · Without 0% · Change +100 pts
  Cases 1: 1 better, 0 same, 0 worse
  Fired in 2 of 2 runs that needed it
  Cost per run $0.019 with, $0.015 without (+23%) · Turns 3.0 with, 1.0 without
  Tested on haiku · judge haiku · Claude Code 2.1.289 · 2026-10-05
  Skill sha256:c9b400d7538f · Cases sha256:a5b22319b5ee · Result sha256:997d5873c70a
```

## Rule changes

**The two Already handled rows changed in 0.2.0.** Under the original rules, Already handled only checked that the interval ruled out a 10-point gain. In the planted check, that hid harm. An outdated skill (suite 3) gave the wrong answer in 5 of the 6 runs where it fired, and the card still said Already handled, with an interval of -41 to +7. The rules never flagged that skill as Hurts, and the new rules don't either, because its interval reaches +7. They now call it Inconclusive. The change was designed after seeing that result, so suite 3 can't count as evidence for it. Of the seven cards recorded before the change, it moves only suite 3.

**Rarely fired was added in 0.4.0** ([D21](decisions.md)). When the model barely opened the skill, the interval compares two arms that mostly ran without it, so no interval verdict says much about the skill. V1's skill fired in 1 of 27 runs, and its card moved from Inconclusive to Rarely fired; no other recorded card moves. The rule was designed after seeing V1, so V1 can't count as evidence for it.

**0.5.0 counts agreeing cases, and a null needs 10 of them** ([D22](decisions.md)). 8 of the 13 planted cards with an interval showed a single point such as "+100 to +100", and in simulation a placebo with 5 agreeing cases came out No effect or Already handled 59% of the time. Three recorded cards move from a null verdict to Inconclusive: 5a (Already handled), 5b and holdout 7 (No effect), each with 9 cases. No Helps or Hurts card moves. The rule was chosen after seeing those cards, so they can't count as evidence for it. [planted-skills-results.md](planted-skills-results.md) lists every card that moved.
