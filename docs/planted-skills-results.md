# The planted skills check: results

The predictions, the pass criterion and the frozen rules are in [planted-skills.md](planted-skills.md), committed in 6c37ff9 before any suite ran. Each card below is what `mordecai identify` wrote, unedited, and is saved in [planted-results/](planted-results/). On 2026-10-05, after the drift demo, all seven cards were rewritten by `mordecai identify` from the same raw results so that they store relative paths instead of absolute local ones. Only the `paths` field changed. Every verdict, count, interval and hash is byte-for-byte the same. Raw eval results stay in `evals/results/`, which git ignores.

Every run: `claude plugin eval <suite> --model <pinned ID> --judge-model <same ID> --no-publish --max-cost-usd <cap> --scaffold -j 2 --threshold 0`, 3 runs per side, temporary files kept inside the repo so the traces could be checked. Costs are Claude Code's list-price estimates (`costUsd` in the result).

## Spend

The ceiling for this check is $35. Before each run, the spend so far plus that run's cap must stay under it. The second stage (runs 8 onward) has its own ceiling of $12 on top of the first stage's $10.83, so the running total must stay under $22.83.

| Run | Suite | Model | Cap | Cost | Spent so far |
|---|---|---|---|---|---|
| 1 | 1-convention (pilot) | claude-haiku-4-5-20251001 | $3 | $1.47 | $1.47 |
| 2 | 5a-twin | claude-haiku-4-5-20251001 | $3 | $1.26 | $2.72 |
| 3 | 5b-filler | claude-haiku-4-5-20251001 | $3 | $1.45 | $4.17 |
| 4 | 2-commits | claude-haiku-4-5-20251001 | $3 | $1.32 | $5.49 |
| 5 | 3-outdated | claude-haiku-4-5-20251001 | $5 | $1.58 | $7.07 |
| 6 | 4-vague | claude-haiku-4-5-20251001 | $3 | $1.99 | $9.06 |
| 7 | 1-convention (drift demo) | claude-sonnet-5-5 | $6 | $1.77 | $10.83 |
| 8 | V2 pilot (no skill, 1 run per case, `--ablation none`) | claude-haiku-4-5-20251001 | $0.30 | $0.25 | $11.08 |

Not counted above: the one-case run on 2026-10-05 that captured the result format ($0.07, before this check).

## Results

| Suite | Predicted | Actual | Match | Better / same / worse | With / without | Fired | Cost | Run (UTC) |
|---|---|---|---|---|---|---|---|---|
| 1-convention | Helps | Helps | Match | 9 / 0 / 0 | 100% / 0% | 27 of 27; 0 of 9 quiet | $1.47 | 2026-10-05 22:13 |
| 5a-twin | Not Helps, not Hurts (acceptable: No effect, Inconclusive) | Already handled | False-positive test: pass. Acceptable set: miss | 0 / 9 / 0 | 100% / 100% | 15 of 27; 0 of 9 quiet | $1.26 | 2026-10-05 22:18 |
| 5b-filler | Not Helps, not Hurts (acceptable: No effect, Inconclusive) | No effect | Match | 0 / 9 / 0 | 0% / 0% | 27 of 27; 0 of 9 quiet | $1.45 | 2026-10-05 22:21 |
| 2-commits | Already handled | Helps | Miss | 9 / 0 / 0 | 96% / 19% | 27 of 27; 0 of 9 quiet | $1.32 | 2026-10-05 22:26 |
| 3-outdated | Hurts | Already handled | Miss | 1 / 6 / 2 | 78% / 93% | 6 of 27; 0 of 9 quiet | $1.58 | 2026-10-05 22:31 |
| 4-vague | Never fired | Never fired | Match | 0 / 9 / 0 | 0% / 0% | 0 of 27; 0 of 9 quiet | $1.99 | 2026-10-05 22:36 |

## Pilot sanity checks (suite 1)

- **Model:** the result records `claude-haiku-4-5-20251001`, and every one of the 335 model messages in the kept traces names the same ID.
- **Cost per run:** $0.0182 with the skill and $0.0226 without, against $0.0186 and $0.0152 in tests/fixtures/probe-result.json: 0.98x and 1.49x, inside the 2x limit.
- **Validity:** not partial, no run errors, card not Invalid.

All three held, so the main set continued.

## Suite notes

**1-convention: Helps, a match.** Every with-skill run passed and every without-skill run failed, on all 9 cases. The skill fired in all 27 runs that needed it and in none of the 9 quiet runs. The interval collapsed to a point (+100 to +100), the bootstrap's known optimism when every run agrees. [Card](planted-results/1-convention.card.json).

**5a-twin: Already handled. Passes the false-positive test, misses the acceptable set.** This is the outcome flagged in planted-skills.md before the run. With skill 1's text in the system prompt, every run passed on both sides, so the change was exactly 0 and the baseline was 100%, which the rules call Already handled. That reading is correct for the numbers. The twin fired in only 15 of 27 runs, since the model often used the rule already in its prompt. As a placebo this was a weak test: with no run-to-run variation at all, there was no noise for the rules to mistake for an effect. [Card](planted-results/5a-twin.card.json).

**5b-filler: No effect, a match.** The filler skill fired in all 27 runs that needed it, and every run failed on both sides, so the change was exactly 0 at a 0% baseline. Like the twin, it gave the rules no noise to misread. Two baseline runs (pr-1777 and pr-913, without the skill) hit the 4-turn cap. They scored 0, as every baseline run of those cases did, and the card lists the errors as a warning. [Card](planted-results/5b-filler.card.json).

**2-commits: Helps, a miss.** Predicted Already handled. The card says the skill raised the score by 78 points (interval +59 to +96), with every case better. [Card](planted-results/2-commits.card.json).

Diagnosis: **case design problem**, specifically a wrong premise about the model, not run noise and not a rule problem. The skill was planted as "something the model already does", but Haiku 4.5 doesn't default to Conventional Commits. Without the skill it wrote a clean imperative summary and no type prefix in 22 of 27 runs, for example "Rename getUser to fetchUser" (commit-1, all three runs), "Remove unused legacy_auth module" (commit-7, all three) and "Fix typo in login failure error message" (commit-9, all three). Only 5 of 27 baseline runs used a type prefix (commit-2, commit-4 twice, commit-5, commit-6). The rules read those numbers correctly: a 19% baseline is nowhere near the 90% ceiling, and every case improved. The prediction in planted-skills.md named this risk. One with-skill failure was the grader being strict rather than the model being wrong: commit-6 run 3 wrote `test(date parsing): ...`, with a space in the scope, which the scope pattern `[\w./-]+` doesn't allow. That cost one run out of 27 and doesn't change the verdict.

**3-outdated: Already handled, a miss.** Predicted Hurts. The card says the model scored 93% without the skill and 78% with it, a change of -15 points with an interval of -41 to +7. [Card](planted-results/3-outdated.card.json).

Diagnosis: **two causes, a case design problem and a verdict rule problem, plus a little run noise.**

- **Case design: the skill rarely fired.** It fired in 6 of 27 runs that needed it, all on the three dependency cases: repo-add-dep 3 of 3, repo-add-dev-dep 2 of 3, repo-install 1 of 3. On the other six cases (tests, lint, format, autofix, one-file, python) it never fired. The model read the README, Makefile and pyproject.toml and answered from them. The prompts start "Look at the project in the current directory", which points the model at the files rather than at the skill.
- **When it fired, it did harm.** In 5 of the 6 runs where it fired, the model gave the outdated answer. repo-add-dep, all three with-skill runs: "Add `requests` to requirements.txt, then run `pip install -r requirements.txt`". All three baseline runs: `uv add requests`. repo-add-dev-dep, the two runs where it fired: "Add `pytest-cov` to `requirements-dev.txt`, then run `pip install -r requirements-dev.txt`". The third with-skill run didn't fire, and answered `uv add --group dev pytest-cov`. The one fired run that passed was repo-install run 2, which answered `uv sync`, trusting the repo over the skill. So: 1 of 6 fired runs passed, against 25 of 27 baseline runs on the same nine cases.
- **Verdict rule problem.** The Already handled rule checks only that the interval rules out a gain of 10 points (+7 < +10). It doesn't check that the interval rules out a loss. Here the interval runs down to -41, two of nine cases went from always right to mostly wrong, and the card still uses a calm label. Its advice ("Remove it, or add cases where the model fails without it") happens to be right, but the label hides the harm. Hurts was correctly not called: the interval reaches +7, so the whole interval isn't below zero. A proposed change is in the review queue, to be tested only on the holdouts.
- **Run noise:** repo-one-file is the one "better" case. Both arms split between `pytest tests/test_tally.py` and `uv run pytest tests/test_tally.py`, and the skill never fired there. With 2 of 3 against 1 of 3, it counts as better by chance.

**4-vague: Never fired, a match.** With the description "General notes.", the skill wasn't opened in any of the 27 runs that needed it, or in any of the 9 quiet runs. Both arms answered with ordinary version tags, such as `v1.0.0` in every run of tag-first-release, and scored 0. Two baseline runs (tag-second-release and tag-summer) hit the 4-turn cap and scored 0, as every baseline run of those cases did. This suite took 8.5 minutes and cost more per run than the others ($0.027 with, $0.029 without), though its runs averaged fewer turns. [Card](planted-results/4-vague.card.json).

## Drift demo: suite 1 on Haiku and on Sonnet

The same skill and the same cases (skill hash `sha256:f35f631cd4d5`, cases hash `sha256:417d28c8319e` on both cards), run once on `claude-haiku-4-5-20251001` and once on `claude-sonnet-5-5`. The Sonnet ID comes from the Claude API ID row of the models overview in the platform docs, which says dateless IDs are pinned snapshots.

| | Haiku 4.5 | Sonnet 5.5 |
|---|---|---|
| Verdict | Helps | Helps |
| With / without | 100% / 0% | 100% / 0% |
| Change (interval) | +100 (+100 to +100) | +100 (+100 to +100) |
| Better / same / worse | 9 / 0 / 0 | 9 / 0 / 0 |
| Fired | 27 of 27; 0 of 9 quiet | 27 of 27; 0 of 9 quiet |
| Cost per run, with / without | $0.0182 / $0.0226 | $0.0246 / $0.0246 |
| Suite cost | $1.47 | $1.77 |

**The verdict didn't move, by any amount.** That's the expected result for this skill: the convention is made up, so no model can know it without the skill. Suite 1 was the wrong suite to show drift. A skill restating something a stronger model might already do, like suite 2's Conventional Commits, is where a model change could move a verdict. [Sonnet card](planted-results/1-convention-sonnet.card.json).

**The demo did expose a gap.** After the Sonnet run, `mordecai check` on the Haiku card still printed "Current: ... matches the skill and cases it was measured on". The card records the model, but `check` compares only the skill and case hashes, so a model change never marks a card stale. The README lists this under known limits. The demo confirms it matters in practice.

## How noisy the real runs were

For each case, each side ran 3 times. Across the six Haiku suites, all 3 runs agreed in 136 of 144 case-and-side cells (94%): every cell in suites 1, 5a, 5b and 4, 19 of 24 in suite 2 and 21 of 24 in suite 3. The simulation in [simulation.md](simulation.md) draws each run as a coin flip with probability 0.2, 0.4 or 0.6, so 3 runs agree only about 36% of the time. These graders on this model were much closer to deterministic than the simulation assumed. What decided each verdict was how many cases changed, not run-to-run noise.

## Overall

Scored against the criterion in planted-skills.md: **4 of 6 suites matched** (1, 5a, 5b, 4) **and 2 missed** (2, 3), so **the check as a whole fails.** For 5a, the hard requirement passed (no Helps or Hurts), but it landed on Already handled rather than No effect or Inconclusive, as flagged before the run. No placebo was called Helps or Hurts. No card was Invalid or partial, and no run hit its cost cap.

Of the two misses, suite 2 is a prediction miss: the rules read the numbers correctly, and the model doesn't behave the way the plant assumed. Suite 3 is partly a case design problem (the skill rarely fired) and partly a rule problem (Already handled doesn't check for a loss). The rules are unchanged. Proposed changes are in [review-queue.md](review-queue.md).

## Post-hoc: the seven cards under the 0.2.0 rules

**This section was written after the results above, and the rule change it applies was designed after seeing them.** The recorded cards above are unchanged. They are what the frozen rules (6c37ff9) said.

In 0.2.0, Already handled also requires the interval to rule out a 10-point loss; otherwise the verdict is Inconclusive. Each verdict below comes from rerunning `mordecai identify` on the same raw result with the new rules.

| Card | Recorded (0.1.0 rules) | 0.2.0 rules |
|---|---|---|
| 1-convention (Haiku) | Helps | Helps |
| 5a-twin | Already handled | Already handled |
| 5b-filler | No effect | No effect |
| 2-commits | Helps | Helps |
| 3-outdated | Already handled | **Inconclusive** |
| 4-vague | Never fired | Never fired |
| 1-convention (Sonnet) | Helps | Helps |

Only suite 3 moves. Its new reason: "The model scored 93% without the skill, but the 90% interval (-41 to +7 points) doesn't rule out a loss of 10 points." The new rules still don't call it Hurts, since the interval reaches +7. Because the change was fitted to this result, suite 3 can't count as evidence for it. The validation suites below are the test.
