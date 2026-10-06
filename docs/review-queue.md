# Review queue: the planted skills check, stage 3

Written 2026-10-06. **All eight steps are done, and no stop condition was hit.** Everything is committed and nothing is pushed. Details for every run: [planted-skills-results.md](planted-skills-results.md). Predictions: [planted-skills.md](planted-skills.md) for the first set and holdouts, and [validation-skills.md](validation-skills.md) for V1 to V3 and H1.

## Scorecard: every suite so far

All on Claude Haiku 4.5 unless marked. Each suite compares 9 cases, with 3 runs per side.

| Suite | Rules | Predicted | Actual | | Better / same / worse | Fired |
|---|---|---|---|---|---|---|
| 1 Made-up convention | 0.1.0 | Helps | Helps (+100) | Match | 9 / 0 / 0 | 27 of 27 |
| 2 Conventional Commits | 0.1.0 | Already handled | Helps (+78) | Miss (wrong premise) | 9 / 0 / 0 | 27 of 27 |
| 3 Outdated rule | 0.1.0 | Hurts | Already handled (-15) | Miss | 1 / 6 / 2 | 6 of 27 |
| 4 Vague description | 0.1.0 | Never fired | Never fired | Match | 0 / 9 / 0 | 0 of 27 |
| 5a Twin placebo | 0.1.0 | Not Helps or Hurts | Already handled | Match | 0 / 9 / 0 | 15 of 27 |
| 5b Filler placebo | 0.1.0 | Not Helps or Hurts | No effect | Match | 0 / 9 / 0 | 27 of 27 |
| V1 Outdated rule meant to fire | 0.2.0 | Hurts | Inconclusive (-11) | Miss | 0 / 7 / 2 | 1 of 27 |
| V2 Not-inert "placebo" | 0.2.0 | Not Helps or Hurts | Hurts (-37) | Design defect | 0 / 3 / 6 | 27 of 27 |
| **V3 Inert placebo** | 0.2.0 | Not Helps or Hurts | Inconclusive (-11) | **Match** | 2 / 3 / 4 | 27 of 27 |
| **Holdout 6 Changelog format** | 0.2.0 | Helps | Helps (+100) | **Match** | 9 / 0 / 0 | 27 of 27 |
| **Holdout 7 Filler placebo** | 0.2.0 | Not Helps or Hurts | No effect | **Match**, caveat below | 0 / 9 / 0 | 27 of 27 |
| **H1 Conflicting convention** | 0.2.0 | Hurts | Hurts (-100) | **Match** | 0 / 0 / 9 | 27 of 27 |
| 1 on Sonnet 5.5 | 0.1.0 | (drift demo) | Helps (+100) | Unchanged | 9 / 0 / 0 | 27 of 27 |
| **2 on Sonnet 5.5** | 0.2.0 | Helps | Helps (+100) | **Match**, but the baseline moved the wrong way | 9 / 0 / 0 | 27 of 27 |

Bold rows ran in this stage.

- **First set:** 3 of 5 skills matched, so the check failed on its own criterion.
- **This stage:** all 5 runs matched their predictions: V3, both sealed holdouts, H1, and suite 2 on Sonnet.
- **Holdout 7's caveat:** its text isn't inert. A note committed before it ran says its baseline at 0% leaves that text no way to change the score. So its No effect shows only that the rules don't invent a gain on a floor.

## False positives

**No placebo has been called Helps or Hurts on noise.**

- **V3 is the test that counts.** It ran on the same cases as V2, and its skill held only three unrelated facts about the team. It fired in all 27 runs, and runs disagreed often: all 3 agreed in 16 of 24 case-and-side cells, against 94% in the first set. Its card says Inconclusive, -11 (interval -33 to +11). 2 cases got better and 4 got worse, so it moved both ways with no verdict.
- **The negative lean (-11) is unexplained.** It could be noise. It could also be a small effect of opening any skill, since runs with the skill took 2.5 turns against 1.3. One suite can't separate the two.
- **The other placebos (5a, 5b and holdout 7) had no noise**, because every run agreed. They show only that the rules don't invent an effect from nothing.
- **V2's Hurts was a real effect, not a false call.** Its text told the model to "Say what changed in plain words", and it did.

## Hurts detection

- **When the harmful skill fired every time (H1), the rules called Hurts:** 0% with the skill, 100% without.
- **When it fired in 6 of 27 runs (suite 3) or 1 of 27 (V1), they didn't:** Already handled under 0.1.0, Inconclusive under 0.2.0.
- **So Hurts detection depends on the skill being opened.** The README says so.

## Haiku vs Sonnet

Both comparisons kept the verdict:

- **Suite 1:** Helps, +100 on both models.
- **Suite 2:** Helps on both. Sonnet's baseline was 0% against Haiku's 19%, the opposite of the predicted direction, so the change grew from +78 to +100.

Both cards in each pair match the same files. `mordecai check --model claude-sonnet-5-5` now reports the Haiku card as stale, and a test pins that.

## Spend

| Stage | Cost |
|---|---|
| 1. First set and suite 1 on Sonnet | $10.83 |
| 2. V2 pilot, V1, V2 | $3.02 |
| 3. V3 $1.24, holdout 6 $1.28, holdout 7 $1.30, H1 $1.24, suite 2 on Sonnet $1.69 | $6.75 |
| **Total** | **$20.60** of the $22.83 ceiling ($2.23 left) |

No run hit a cap, went partial or came out Invalid. Claude Code updated itself from 2.1.289 to 2.1.290 between V2 and V3. The cards record each version.

## Step 6: the rule gap for skills that rarely fire (not applied)

V1's skill fired in 1 of 27 runs, and its card said Inconclusive, the same word used for "the interval is too wide". The actionable message is different: the skill is almost never used, so fix its description before measuring anything else.

Fire rates on the 14 recorded cards: 100% on 10 cards, 56% (5a), 22% (suite 3), 4% (V1) and 0% (suite 4, already Never fired).

| Proposal | What it does | Cards it changes |
|---|---|---|
| A. A verdict, "Rarely fired", when the skill fires in under 10% of the runs that needed it, checked right after Never fired | Replaces the verdict | V1 only: Inconclusive becomes Rarely fired |
| B. The same verdict at under 25% | Replaces the verdict | V1, and suite 3 (Already handled under 0.1.0, Inconclusive under 0.2.0) becomes Rarely fired |
| C. A warning, not a verdict, under 50%: "Fired in only N of M runs; the change mostly reflects runs where the skill wasn't used" | Adds a warning | Suite 3 and V1 get the warning; no verdict changes. 5a (56%) does not |

**Recommendation: A and C together, plus a "when it fired" line on the card.**
- Under 10%, there's too little skill use to read any change, and the fix is the description, so a distinct verdict says the right thing. That changes V1 only.
- Between 10% and 50%, the card should keep its verdict and warn. Suite 3 is the reason: the skill did real harm in 5 of the 6 runs where it fired, and B's verdict would hide that behind "rarely fired".
- The line would read, for example, "When it fired: 1 of 6 runs passed. When it didn't: 20 of 21." It's diagnostic only, because the skill fires on particular cases.
- Cost: code and tests, $0.
- **Caveat: the proposal was designed after seeing V1.** Test it on new suites before trusting it, as with 0.2.0.

## Open decisions

1. **Apply the step 6 proposal (A and C)? Recommendation: yes, as 0.3.0, in its own commit.** Recorded cards stay as they are, with a post-hoc section like the 0.2.0 one. $0. Its real test needs a new suite where a skill fires rarely, about $1.30 (cap $3), which needs a little more than the $2.23 left, so it needs a new ceiling.
2. **A moderate-effect planted skill,** to check the simulation's +20 point finding on real runs. No planted skill has had a true effect between +10 and +30. **Recommendation: yes, if the README's simulation claims matter to you.** About $1.30 a suite on Haiku. It needs a new ceiling.
3. **More models. Recommendation: not now.** Two Sonnet comparisons gave no verdict change. Judge-graded suites would test more than another model would.
4. **Old absolute paths in git history. Recommendation: leave them.**
   - They are 7 lines, the `casesRoot` field in the cards committed in ea8021a through 2c991f4.
   - They name the local username and folder layout, nothing secret. Your name is already in LICENSE.
   - Rewriting would change every commit hash from ea8021a on, and the docs cite those hashes (6c37ff9, 03d2619, f848767, ef49573, 337397d, b434b9a) as the record that predictions came before results.
   - The other options: rewrite and update every cited hash (about an hour, and the order becomes your word rather than the hashes'), or squash to one commit (loses the record).

## Ready to push?

**Yes, once you've decided on item 4.** I recommend leaving the history as it is.

- 52 tests pass, and lint, the brand check and the planted-fixture check pass.
- No tracked file contains a local path, token or key.
- The README states only what the docs show, with no "v0.1" and no "not yet checked against real runs".
- Raw eval results, traces and kept temporary directories are under `evals/results/`, which git ignores.

There is no remote yet. Creating the GitHub repository and pushing is yours to do.
