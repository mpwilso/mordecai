# The planted skills check: results

The predictions, the pass criterion and the frozen rules are in [planted-skills.md](planted-skills.md), committed in 6c37ff9 before any suite ran. Each card below is what `mordecai identify` wrote, unedited, and is saved in [planted-results/](planted-results/). Raw eval results stay in `evals/results/`, which git ignores.

Every run: `claude plugin eval <suite> --model <pinned ID> --judge-model <same ID> --no-publish --max-cost-usd <cap> --scaffold -j 2 --threshold 0`, 3 runs per side, temporary files kept inside the repo so the traces could be checked. Costs are Claude Code's list-price estimates (`costUsd` in the result).

## Spend

The ceiling for this check is $35. Before each run, the spend so far plus that run's cap must stay under it.

| Run | Suite | Model | Cap | Cost | Spent so far |
|---|---|---|---|---|---|
| 1 | 1-convention (pilot) | claude-haiku-4-5-20251001 | $3 | $1.47 | $1.47 |
| 2 | 5a-twin | claude-haiku-4-5-20251001 | $3 | $1.26 | $2.72 |

Not counted above: the one-case run on 2026-10-05 that captured the result format ($0.07, before this check).

## Results

| Suite | Predicted | Actual | Match | Better / same / worse | With / without | Fired | Cost | Run (UTC) |
|---|---|---|---|---|---|---|---|---|
| 1-convention | Helps | Helps | Match | 9 / 0 / 0 | 100% / 0% | 27 of 27; 0 of 9 quiet | $1.47 | 2026-10-05 22:13 |
| 5a-twin | Not Helps, not Hurts (acceptable: No effect, Inconclusive) | Already handled | False-positive test: pass. Acceptable set: miss | 0 / 9 / 0 | 100% / 100% | 15 of 27; 0 of 9 quiet | $1.26 | 2026-10-05 22:18 |

## Pilot sanity checks (suite 1)

- **Model:** the result records `claude-haiku-4-5-20251001`, and every one of the 335 model messages in the kept traces names the same ID.
- **Cost per run:** $0.0182 with the skill and $0.0226 without, against $0.0186 and $0.0152 in tests/fixtures/probe-result.json: 0.98x and 1.49x, inside the 2x limit.
- **Validity:** not partial, no run errors, card not Invalid.

All three held, so the main set continued.

## Suite notes

**1-convention: Helps, a match.** Every with-skill run passed and every without-skill run failed, on all 9 cases. The skill fired in all 27 runs that needed it and in none of the 9 quiet runs. The interval collapsed to a point (+100 to +100), the bootstrap's known optimism when every run agrees. [Card](planted-results/1-convention.card.json).

**5a-twin: Already handled. Passes the false-positive test, misses the acceptable set.** This is the outcome flagged in planted-skills.md before the run. With skill 1's text in the system prompt, every run passed on both sides, so the change was exactly 0 and the baseline was 100%, which the rules call Already handled. That reading is correct for the numbers. The twin fired in only 15 of 27 runs, since the model often used the rule already in its prompt. As a placebo this was a weak test: with no run-to-run variation at all, there was no noise for the rules to mistake for an effect. [Card](planted-results/5a-twin.card.json).
