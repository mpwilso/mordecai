# How Mordecai was tested

The verdict rules were checked on planted skills run for real, on two model comparisons, on simulated skills and with unit tests. This page moved here from the README; the README keeps the short version.

## Planted skills, run for real

Each planted skill has a known intended effect, and every prediction was committed before its suite ran. **Only some of the suites were blind.** The first set of five skills and the two sealed holdouts were written and predicted before any result existed: their predictions are in commit bd92b23 ([planted-skills.md](planted-skills.md)), and the first results start at commit 15da64f. Everything after that (V1, V2, V3, H1 and both Sonnet reruns) was designed or predicted after seeing earlier results. Each suite has 12 cases: 9 compared, and 3 where the skill should stay quiet. Every suite ran with 3 runs per side and regex or tool-use graders only. Details, cards and costs are in [planted-skills-results.md](planted-skills-results.md).

**First set, 0.1.0 rules, Claude Haiku 4.5: 3 of 5 skills got their predicted verdict.** The criterion written in advance was that every suite gets its predicted outcome, so the check as a whole failed.

| Suite | Predicted | Actual | |
|---|---|---|---|
| 1. A made-up convention | Helps | Helps (+100) | Match |
| 2. Conventional Commits | Already handled | Helps (+78) | Miss. Haiku rarely uses the format unprompted (5 of 27 runs), so the premise was wrong |
| 3. An outdated rule | Hurts | Already handled (-15) | Miss. The skill fired in 6 of 27 runs; see [the rule changes](verdicts.md#rule-changes) |
| 4. A vague description | Never fired | Never fired | Match |
| 5a. A twin placebo | Not Helps or Hurts | Already handled | Match. Every run agreed, so there was no noise to misread |
| 5b. A filler placebo | Not Helps or Hurts | No effect | Match. Every run agreed |

**Later suites, 0.2.0 rules, frozen at 64a7701.** V1, V2, V3 and H1 were written after the first results, so they are not blind. Holdouts 6 and 7 were written with the first set, before any result, and each ran once.

| Suite | Predicted | Actual | |
|---|---|---|---|
| V1. An outdated rule meant to fire | Hurts | Inconclusive (-11) | Miss. The skill fired in 1 of 27 runs. Rarely fired under the 0.4.0 rules, a rule designed after seeing this card |
| V2. Meant as a noisy placebo | Not Helps or Hurts | Hurts (-37) | Design defect. Its text ("Say what changed in plain words") changed behavior, and the rules read that real effect correctly |
| V3. An inert placebo on V2's cases | Not Helps or Hurts | Inconclusive (-11, interval -33 to +11) | Match. It fired in 27 of 27 runs, on noisy runs |
| Holdout 6. A made-up changelog format | Helps | Helps (+100) | Match |
| Holdout 7. A filler placebo | Not Helps or Hurts | No effect | Match, but weak evidence: its baseline was 0%, so it could only have shown a false gain, and its text isn't inert |
| H1. A made-up convention that conflicts with the graders | Hurts | Hurts (-100) | Match. It fired in 27 of 27 runs. Designed after seeing results, so that the skill would fire |

The tables report what each card said when its suite ran. Under the 0.5.0 rules (D22), 5a, 5b and holdout 7 read Inconclusive, since a null now needs 10 cases; [planted-skills-results.md](planted-skills-results.md) lists every card that moved.

What these show:

- **No placebo has been called Helps or Hurts, but only one placebo ran on noisy runs.** That was V3, which was not blind. Its skill fired every time, its runs disagreed often (all 3 runs agreed in 16 of 24 case-and-side cells), and its card said Inconclusive. The other placebos (5a, 5b and holdout 7) had no noise to misread. V2's Hurts was a real effect from an instruction in its text, not a false call.
- **Hurts was detected once, and it depends on the skill being opened.** The only Hurts on a harmful skill was H1, a suite designed after seeing results so that its skill would fire in every run. When a harmful skill fired in 6 of 27 runs (suite 3, blind) or 1 of 27 (V1), the rules didn't call Hurts. Those cards said Already handled and Inconclusive. This doesn't show that Hurts detection is reliable.
- **Real runs were much less noisy than the simulation assumed.** In the first set, all 3 runs of a side agreed in 94% of case-and-side cells.

Total cost of the planted runs: $22.11 at list price, across 16 runs, one of them a $0.25 pilot.

## Model comparisons

Two suites were rerun on Claude Sonnet 5.5 (`claude-sonnet-5-5`). Neither verdict moved, so no drift was caught. The first rerun had no written prediction; the second was predicted after seeing the Haiku card. Suite 1 stayed Helps (+100 on both models). Suite 2 stayed Helps, but its baseline went down, not up: Sonnet used a Conventional Commits prefix unprompted in 0 of 27 runs, against Haiku's 5. The change grew from +78 to +100. Both cards in each pair match the same skill and case files, so only the model tells them apart. `mordecai check --model` reports that difference in the record (see [usage.md](usage.md#a-worked-example)). It doesn't show that a verdict changed.

## Simulation

[simulation.md](simulation.md) runs the rules on simulated skills with a known effect, 200 suites per row. The first simulation treated every run as an independent coin flip, which makes 3 runs agree only about a third of the time. Real runs agreed 94% of the time, so that assumption didn't match. Rerun at 94% agreement:

- **A placebo was called Helps or Hurts in 0% of suites**, against up to 4% with coin flips.
- **A skill worth +20 points was called Helps in 13%, 36% and 56% of suites at 5, 10 and 15 cases.** That's almost the same as with coin flips (14%, 35% and 52%). The remaining uncertainty is between cases, not between runs: a +20 point skill changes the outcome of only some cases. In simulation, a moderate effect needs well over 15 cases to be called reliably. **This finding hasn't been tested on real runs:** no planted skill had a moderate effect.
- **A skill worth +40 points was called Helps in 80% of suites at 10 cases and 96% at 15.**

## Unit tests

Each verdict and warning has a test on a constructed result, along with hashing, staleness, relative card paths, `lint`, `check --model` and the command line. Others feed in hostile input: malformed results and cards, paths and links that lead outside the plugin, and names carrying terminal escapes or Markdown. One test is built from the real suite 3 result, and others check that the example cards in the README and [verdicts.md](verdicts.md) are what the tool prints. The library's tests cover every command, including hostile sources and targets (path traversal, links, malformed frontmatter, a name that doesn't match its folder, a card that doesn't match its version's files or its result), the byte-for-byte install, the seeded library, and the MCP server through the SDK's in-process client and over stdio. `uv run pytest` passes 217 tests without the library extra (the library's test files skip), and 413 with it (`uv sync --extra library --group spec`), as of 0.5.0. None call a model or reach the network. CI ([.github/workflows/ci.yml](../.github/workflows/ci.yml)) runs the tests, lint, the format check, `scripts/brand.py --check`, `scripts/planted.py --check` and the [GitHub Action](usage.md#github-action)'s identify step on Python 3.11, 3.12 and 3.13, on every push and on pull requests from forks. A second job runs the tests once more on Python 3.11 with the library extra, under `coverage`, and writes the coverage report to the job summary. Live eval runs are never part of CI: they call a model and cost money, and CI has no secrets. The result format comes from a real `claude plugin eval` run, not from the docs alone.

## What wasn't checked

- **Other models.** Everything ran on Claude Haiku 4.5, except two suites rerun on Claude Sonnet 5.5.
- **Judge-graded suites.** Every grader was a regex or a tool-use check, so judge disagreement was never in play.
- **Skills with a moderate real effect,** somewhere around +10 to +30 points. The changes measured on the planted cards were -100, -37, -15, -11, 0, +78 and +100.
- **A harmful skill that fires in some runs but not others.** The rules gave Already handled (0.1.0) or Inconclusive (0.2.0) in those cases. Since 0.4.0, under 10% is Rarely fired, and 10% to 50% only adds a warning.
- **Domains other than git workflow and Python project setup.**
- **Invalid and partial results from real runs.** No real run hit a cost cap or a rate limit, so those paths are tested only on constructed results.
- **Using `--fail-on` as a CI gate on a real repository.**

