# Review queue: the planted skills check

Written 2026-10-05, after the main set and the drift demo. The holdouts have not run. Details for every suite: [planted-skills-results.md](planted-skills-results.md). The predictions, committed before any run: [planted-skills.md](planted-skills.md) (6c37ff9).

## 1. Scorecard

All on `claude-haiku-4-5-20251001`, 9 compared cases and 3 quiet cases per suite, 3 runs per side.

| Skill | Predicted | Actual | | Better / same / worse | With / without |
|---|---|---|---|---|---|
| 1. Made-up convention | Helps | Helps | Match | 9 / 0 / 0 | 100% / 0% |
| 2. Conventional Commits | Already handled | Helps (+78, interval +59 to +96) | **Miss** | 9 / 0 / 0 | 96% / 19% |
| 3. Outdated rule | Hurts | Already handled (-15, interval -41 to +7) | **Miss** | 1 / 6 / 2 | 78% / 93% |
| 4. Vague description | Never fired | Never fired (0 of 27) | Match | 0 / 9 / 0 | 0% / 0% |
| 5a. Twin placebo | Not Helps or Hurts | Already handled | Match on the hard rule; outside your acceptable set | 0 / 9 / 0 | 100% / 100% |
| 5b. Filler placebo | Not Helps or Hurts | No effect | Match | 0 / 9 / 0 | 0% / 0% |

**3 of the 5 skills matched, and 2 missed. By the criterion written in advance, the check fails.**

- **Miss 2 is a prediction miss, not a rule miss.** Without the skill, Haiku writes "Rename getUser to fetchUser", not "refactor: ...". It used a type prefix in only 5 of 27 baseline runs. Helps is the correct reading.
- **Miss 3 is two things.**
  - *Case design:* the skill fired in only 6 of 27 runs, because the prompts sent the model to the repo's files.
  - *Rule weakness:* when the skill did fire, 5 of 6 runs gave the outdated answer, for example `pip install -r requirements.txt` instead of `uv add requests`. Already handled only checks that the interval rules out a gain, not a loss, so the card used a calm label for a −15 estimate whose interval reaches −41.

## 2. False positives on the placebos

Neither placebo was called Helps or Hurts. But both were weak tests:

- **Twin (5a):** every run passed on both sides.
- **Filler (5b):** every run failed on both sides.

So the change was exactly 0 with no variation at all, and there was no noise for the rules to mistake for an effect. **What we know:** the rules don't invent an effect from nothing. **What we don't know yet:** whether they hold steady on a placebo whose runs disagree.

The twin landed on Already handled, which I flagged before it ran: its baseline had the convention in the system prompt.

## 3. Spend

$10.83 of the $35 ceiling. No run hit its cap, and no card was partial or Invalid.

| Suite | Model | Cap | Cost |
|---|---|---|---|
| 1-convention | Haiku 4.5 | $3 | $1.47 |
| 5a-twin | Haiku 4.5 | $3 | $1.26 |
| 5b-filler | Haiku 4.5 | $3 | $1.45 |
| 2-commits | Haiku 4.5 | $3 | $1.32 |
| 3-outdated | Haiku 4.5 | $5 | $1.58 |
| 4-vague | Haiku 4.5 | $3 | $1.99 |
| 1-convention, drift demo | Sonnet 5.5 (`claude-sonnet-5-5`) | $6 | $1.77 |

**Haiku vs Sonnet on suite 1:** the verdict didn't move at all. Both cards say Helps, 100% vs 0%, +100, 9 better, fired 27 of 27. That's expected for a made-up convention no model can know, so suite 1 was the wrong suite for a drift demo.

The demo did show a real gap: `mordecai check` still called the Haiku card "Current" after the Sonnet run, because it compares only file hashes, never the model.

## 4. The simulation's +20 point finding

**No, it didn't show up. This check didn't test it.**

- No planted skill had an effect anywhere near +20. The effects were +100, +78, 0, 0, 0 and −15.
- Real runs were far less noisy than the simulation assumes. All 3 runs agreed in 94% of case-and-side cells (136 of 144), against about 36% for the simulation's coin flips.
- Verdicts were decided by how many cases changed, not by run-to-run noise. In 4 of the 6 cards with an interval, the interval collapsed to a single point.
- The one moderate effect, −15 on suite 3, was not confirmed. Its interval of −41 to +7 was wide because 2 cases flipped completely while 6 didn't move, not because runs disagreed.

So the simulation's warning about moderate effects probably still holds, but for a different reason than it models: spread between cases, not coin-flip noise. It needs a planted skill with a real moderate effect to check.

## 5. Decisions for you

1. **Run the holdouts now? I'd recommend not yet.**
   - They are the two kinds the rules already got right with zero noise: a made-up convention and a filler placebo.
   - None of the proposed changes would alter their verdicts, so they can't test change 2.
   - Better: write and commit two more holdouts first. One is an outdated-rule skill whose description reliably fires; the other is a placebo on a noisy task (item 5). Then run all four holdouts once.
   - Cost: about $6 projected on Haiku, caps totaling $12–14.
   - Running the current two as they are would cost about $2.70 (caps $6), and it's a one-time run.
2. **Rule change: Already handled must also rule out a loss** (lower bound above −10). Otherwise the verdict falls through to Inconclusive.
   - Motivated by suite 3.
   - I checked it against all seven cards with a throwaway script; the frozen rules weren't changed. It changes only suite 3, from Already handled to Inconclusive. It still wouldn't call suite 3 Hurts.
   - Code and tests, $0. Needs a new holdout to test it (item 1).
3. **Card addition, not a verdict rule.**
   - A line for score when the skill fired against when it didn't. Suite 3: fired runs passed 1 of 6, unfired runs 20 of 21.
   - A warning when the skill fired in fewer than half the runs that needed it.
   - Diagnostic only, because the skill fires on particular cases, which confounds the comparison. $0.
4. **`mordecai check --model`:** mark a card stale when the model differs from the one it was measured on. Motivated by the drift demo. $0.
5. **Case design defects. I'd recommend no reruns.**
   - Suite 3's prompts steer the model away from the skill. Rerunning with new prompts to chase Hurts would be fitting the case to the prediction, so put that into a new holdout instead.
   - Suite 2 has no file defect; its premise was wrong for Haiku. Keep the result.
   - Minor: one commit run failed only because of a space in the scope (`test(date parsing):`).
   - Minor: 4 baseline runs hit the 4-turn cap; they would have scored 0 anyway. Use `max_turns: 6` in new suites.
   - New: a **noisy placebo**, the filler skill on suite 2's commit cases, where the baseline is 19% and runs disagree. About $1.30 (cap $3).
6. **More models: I'd recommend suite 2 on Sonnet 5.5** as the real drift demo. A stronger model might default to Conventional Commits, which would move the verdict toward Already handled. About $1.80 (cap $6). Opus isn't needed yet.

Doing all of 1, 5 (noisy placebo) and 6 would cost about $9.50 projected, with about $24 of the ceiling left.

## 6. README changes, drafted, not applied

**Replace the line under the tagline** with:

> v0.1: the verdict rules have been checked on six planted skills with real eval runs. Four got the predicted verdict; the two misses are written up.

**Replace the Status paragraph's last two sentences** with:

> It reads real eval results and writes a card. Its rules have been checked on simulated skills and on six planted skills run for real on Claude Haiku 4.5: four matched their predicted verdict and two missed. The misses, and what they say about the rules, are in [docs/planted-skills-results.md](docs/planted-skills-results.md).

**Add to "How it was tested":**

> - **Six planted skills, run for real**, with the predictions committed before any run ([docs/planted-skills.md](docs/planted-skills.md)). A made-up convention was called Helps, a skill with a vague description Never fired, and neither placebo was called Helps or Hurts. Two missed. A Conventional Commits skill was predicted Already handled and came out Helps, because Haiku 4.5 rarely uses the format unprompted (5 of 27 runs). An outdated-rule skill was predicted Hurts and came out Already handled: it gave the outdated answer in 5 of the 6 runs where it fired, but it fired in only 6 of 27. Total cost: $10.83.

**Replace "That last row is the main thing the simulation taught me..."** with:

> The simulation treats every run as a coin flip. Real runs weren't like that: in the planted check, all three runs agreed in 94% of cases. Verdicts turned on how many cases changed, not on noise between runs, and most intervals collapsed to a single point.

**In "Known limits", replace the first bullet** ("Not yet checked against real runs...") with:

> - **Already handled can hide harm.** It checks that a skill can't be adding 10 points, not that it isn't costing them. In the planted check, a skill that gave the wrong answer whenever it fired got Already handled, with an interval of -41 to +7.
> - **Checked on one small model, with regex graders only.** The planted check ran on Claude Haiku 4.5, plus one suite on Sonnet 5.5. Judge-graded suites haven't been tried.
> - **The placebos so far had no noise.** Every run agreed, so the rules haven't yet been tested on a placebo whose runs disagree.

**Strengthen the staleness bullet** with: "A rerun on Sonnet 5.5 left the Haiku card marked current."

**Stop claiming:**
- "and not yet on planted skills with real runs" (Status).
- What's next, item 2, "The planted skills check, run for real" (done). Replace it with "Run the holdout skills once, after any rule change is decided."
- "An Inconclusive card usually means 'measure more'." It comes from the simulation, and no real card was Inconclusive. Keep it only as the simulation's finding.
