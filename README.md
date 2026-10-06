<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/lockup-dark.svg">
    <img src="docs/brand/lockup-light.svg" alt="Mordecai: a potion flask on a round badge, filled above a dashed line across the bulb" height="72">
  </picture>
</p>

<p align="center"><b>Skill catalogs count downloads. Mordecai checks whether the skill helps.</b></p>

Status: A portfolio project, built to show how I design, test and judge an AI tool. Version 0.2.0. Its verdict rules have been checked on simulated skills and on 12 planted skill suites with real eval runs, almost all on one small model (Claude Haiku 4.5). Only the first set of five skills and two sealed holdouts were blind; on that first set, 3 of 5 got their predicted verdict. The later suites were designed after seeing those results. Every result is in [docs/planted-skills-results.md](docs/planted-skills-results.md), including the misses.

Mordecai is for teams that share Claude skills. Claude Code already runs a skill's test cases with and without the skill (`claude plugin eval`). Mordecai reads that result and decides what the skill can honestly claim: it helps, it hurts, the model already handles it, or there isn't enough to tell. The card it writes is tied to the exact skill, cases and model it was measured on, so a team can see when a claim has gone stale.

It sits beside [Loupe](https://github.com/mpwilso/loupe), [Parallax](https://github.com/mpwilso/parallax) and [ISR](https://github.com/mpwilso/isr), and has no dependency on any of them.

Jump to [an example card](#what-a-card-looks-like), [the verdicts](#the-verdicts), [crawl mode](#crawl-mode), [how it was tested](#how-it-was-tested), [the limits](#known-limits) or [setup](#setup).

## Why it exists

Many skills don't measurably help, and the usual tools don't flag it:

- In SWE-Skills-Bench, 39 of 49 skills gave no gain in pass rate, and 24 of them passed every task without the skill. Token use moved between -78% and +451% with the results unchanged.
- In SkillsBench, skills written by people added about 16 points on average, skills written by models about -1, and 16 of 84 tasks did worse with a skill.
- `claude plugin eval` reports the change with and without a plugin, but its docs say that change never affects the exit code. CI gates on the score alone, so a skill that passes everything with or without it passes the gate. A run that hits a rate limit usually scores 0 without marking the suite partial.

## What a card looks like

This is the card for a real result: a one-case eval of a tiny skill, run once while building Mordecai to capture the result format. Its result is [tests/fixtures/probe-result.json](tests/fixtures/probe-result.json), and the skill and case are in [tests/fixtures/probe/](tests/fixtures/probe/).

```
schema-probe 0.0.1: Inconclusive
Only 1 case(s) were compared; the rules need at least 5.

  With 100% · Without 0% · Change +100 pts
  Cases 1: 1 better, 0 same, 0 worse
  Fired in 2 of 2 runs that needed it
  Cost per run $0.019 with, $0.015 without (+23%) · Turns 3.0 with, 1.0 without
  Tested on haiku · judge haiku · Claude Code 2.1.289 · 2026-10-05
  Skill sha256:c9b400d7538f · Cases sha256:a5b22319b5ee · Result sha256:997d5873c70a

Warnings
  - The model was haiku, not a pinned model ID, so a later model can change this result without anything in the card changing. Pass --model with a full ID.
  - Some cases ran 2 time(s) per side. The interval leans on repeat runs; use at least 3.
  - No case checks that the skill stays quiet when it isn't needed. Add one with a tool_used Skill grader, min: 0, max: 0 and arm: both.

Next: Add cases or runs, then measure again.
```

The skill went from 0% to 100%, and the card still won't call it Helps. One case is not evidence.

## The verdicts

Code decides, not a model. The rules run in this order, and the first one that applies wins. They're written out in [src/mordecai/verdict.py](src/mordecai/verdict.py).

| Verdict | When |
|---|---|
| Invalid | The eval stopped early, a run hit a usage or rate limit, judge graders were skipped, or nothing ran without the skill |
| Never fired | The skill didn't fire in any run where it should have |
| Inconclusive | Fewer than 5 cases were compared |
| Hurts | The whole 90% interval for the change is below zero |
| Helps | The whole interval is above zero, and the change is at least 10 points |
| Already handled | The model scores at least 90% without the skill, and the interval rules out both a 10-point gain and a 10-point loss |
| Inconclusive | The model scores at least 90% without the skill, but the interval doesn't rule out a 10-point loss |
| No effect | The interval stays inside plus or minus 10 points |
| Inconclusive | Anything else: the interval is too wide to call |

The interval is a bootstrap over cases, and over runs inside each case, with a fixed seed, so the same result always gives the same card. Cases that check the skill stays quiet are left out of the change and reported as misfires.

Every card also lists warnings that don't change the verdict: a model alias instead of a pinned ID, fewer than 3 runs per side, no case that checks the skill stays quiet, no case that checks it fired, and case prompts that name the skill (which tests whether the model follows an instruction, not whether it finds the skill). `mordecai lint` runs the same checks on case files before an eval.

**The two Already handled rows changed in 0.2.0.** Under the original rules, Already handled only checked that the interval ruled out a 10-point gain. In the planted check, that hid harm. An outdated skill (suite 3) gave the wrong answer in 5 of the 6 runs where it fired, and the card still said Already handled, with an interval of -41 to +7. The rules never flagged that skill as Hurts, and the new rules don't either, because its interval reaches +7. They now call it Inconclusive. The change was designed after seeing that result, so suite 3 can't count as evidence for it. Of the seven cards recorded before the change, it moves only suite 3.

## Crawl mode

`--crawl`, or `MORDECAI_MODE=crawl`, prints the same card as loot, in honor of Matt Dinniman's *Dungeon Crawler Carl*. Helps is ENCHANTED, Hurts is CURSED, Already handled is VENDOR TRASH, and Mordecai has opinions. On a terminal, the box opens first.

<p align="center"><img src="docs/brand/crawl-card.svg" alt="Crawl mode: a pixel treasure chest shakes, opens and lifts out a red potion, beside the card mordecai identify --crawl prints for a demo skill that helps" width="900"></p>

<p align="center"><sub>A demo skill with simulated results. The text is printed by the same code as the command.</sub></p>

The jokes come from fixed templates around the plain card's stat block. They can't change a number or a verdict, and a test checks that every number in crawl mode is also in plain mode.

Crawl mode is a fan nod. It isn't affiliated with or endorsed by the author or publisher, and its text is original.

## How it was tested

### Planted skills, run for real

Each planted skill has a known intended effect, and every prediction was committed before its suite ran. **Only some of the suites were blind.** The first set of five skills and the two sealed holdouts were written and predicted before any result existed: their predictions are in commit bd92b23 ([docs/planted-skills.md](docs/planted-skills.md)), and the first results start at commit 15da64f. Everything after that (V1, V2, V3, H1 and both Sonnet reruns) was designed or predicted after seeing earlier results. Each suite has 12 cases: 9 compared, and 3 where the skill should stay quiet. Every suite ran with 3 runs per side and regex or tool-use graders only. Details, cards and costs are in [docs/planted-skills-results.md](docs/planted-skills-results.md).

**First set, 0.1.0 rules, Claude Haiku 4.5: 3 of 5 skills got their predicted verdict.** The criterion written in advance was that every suite gets its predicted outcome, so the check as a whole failed.

| Suite | Predicted | Actual | |
|---|---|---|---|
| 1. A made-up convention | Helps | Helps (+100) | Match |
| 2. Conventional Commits | Already handled | Helps (+78) | Miss. Haiku rarely uses the format unprompted (5 of 27 runs), so the premise was wrong |
| 3. An outdated rule | Hurts | Already handled (-15) | Miss. The skill fired in 6 of 27 runs; see the verdicts section |
| 4. A vague description | Never fired | Never fired | Match |
| 5a. A twin placebo | Not Helps or Hurts | Already handled | Match. Every run agreed, so there was no noise to misread |
| 5b. A filler placebo | Not Helps or Hurts | No effect | Match. Every run agreed |

**Later suites, 0.2.0 rules, frozen at 64a7701.** V1, V2, V3 and H1 were written after the first results, so they are not blind. Holdouts 6 and 7 were written with the first set, before any result, and each ran once.

| Suite | Predicted | Actual | |
|---|---|---|---|
| V1. An outdated rule meant to fire | Hurts | Inconclusive (-11) | Miss. The skill fired in 1 of 27 runs |
| V2. Meant as a noisy placebo | Not Helps or Hurts | Hurts (-37) | Design defect. Its text ("Say what changed in plain words") changed behavior, and the rules read that real effect correctly |
| V3. An inert placebo on V2's cases | Not Helps or Hurts | Inconclusive (-11, interval -33 to +11) | Match. It fired in 27 of 27 runs, on noisy runs |
| Holdout 6. A made-up changelog format | Helps | Helps (+100) | Match |
| Holdout 7. A filler placebo | Not Helps or Hurts | No effect | Match, but weak evidence: its baseline was 0%, so it could only have shown a false gain, and its text isn't inert |
| H1. A made-up convention that conflicts with the graders | Hurts | Hurts (-100) | Match. It fired in 27 of 27 runs. Designed after seeing results, so that the skill would fire |

What these show:

- **No placebo has been called Helps or Hurts, but only one placebo ran on noisy runs.** That was V3, which was not blind. Its skill fired every time, its runs disagreed often (all 3 runs agreed in 16 of 24 case-and-side cells), and its card said Inconclusive. The other placebos (5a, 5b and holdout 7) had no noise to misread. V2's Hurts was a real effect from an instruction in its text, not a false call.
- **Hurts was detected once, and it depends on the skill being opened.** The only Hurts on a harmful skill was H1, a suite designed after seeing results so that its skill would fire in every run. When a harmful skill fired in 6 of 27 runs (suite 3, blind) or 1 of 27 (V1), the rules didn't call Hurts. Those cards said Already handled and Inconclusive. This doesn't show that Hurts detection is reliable.
- **Real runs were much less noisy than the simulation assumed.** In the first set, all 3 runs of a side agreed in 94% of case-and-side cells.

Total cost of the planted runs: $20.60 at list price, across 15 runs, one of them a $0.25 pilot.

### Model comparisons

Two suites were rerun on Claude Sonnet 5.5 (`claude-sonnet-5-5`). Neither verdict moved, so no drift was caught. The first rerun had no written prediction; the second was predicted after seeing the Haiku card. Suite 1 stayed Helps (+100 on both models). Suite 2 stayed Helps, but its baseline went down, not up: Sonnet used a Conventional Commits prefix unprompted in 0 of 27 runs, against Haiku's 5. The change grew from +78 to +100. Both cards in each pair match the same skill and case files, so only the model tells them apart. `mordecai check --model` reports that difference in the record (see [setup](#setup)). It doesn't show that a verdict changed.

### Simulation

[docs/simulation.md](docs/simulation.md) runs the rules on simulated skills with a known effect, 200 suites per row. The first simulation treated every run as an independent coin flip, which makes 3 runs agree only about a third of the time. Real runs agreed 94% of the time, so that assumption didn't match. Rerun at 94% agreement:

- **A placebo was called Helps or Hurts in 0% of suites**, against up to 4% with coin flips.
- **A skill worth +20 points was called Helps in 13%, 36% and 56% of suites at 5, 10 and 15 cases.** That's almost the same as with coin flips (14%, 35% and 52%). The remaining uncertainty is between cases, not between runs: a +20 point skill changes the outcome of only some cases. In simulation, a moderate effect needs well over 15 cases to be called reliably. **This finding hasn't been tested on real runs:** no planted skill had a moderate effect.
- **A skill worth +40 points was called Helps in 80% of suites at 10 cases and 96% at 15.**

### Unit tests

Each verdict and warning has a test on a constructed result, along with hashing, staleness, relative card paths, `lint`, `check --model` and the command line. One test is built from the real suite 3 result. `uv run pytest` runs 52 tests, and none call a model. The result format comes from a real `claude plugin eval` run, not from the docs alone.

### What wasn't checked

- **Other models.** Everything ran on Claude Haiku 4.5, except two suites rerun on Claude Sonnet 5.5.
- **Judge-graded suites.** Every grader was a regex or a tool-use check, so judge disagreement was never in play.
- **Skills with a moderate real effect,** somewhere around +10 to +30 points. The changes measured on the planted cards were -100, -37, -15, -11, 0, +78 and +100.
- **A harmful skill that fires in some runs but not others.** The rules gave Already handled (0.1.0) or Inconclusive (0.2.0) in those cases, and there is no verdict for it.
- **Domains other than git workflow and Python project setup.**
- **Invalid and partial results from real runs.** No real run hit a cost cap or a rate limit, so those paths are tested only on constructed results.
- **Using `--fail-on` as a CI gate on a real repository.**

## Known limits

- **Hurts needs the skill to be opened.** A harmful skill that fires rarely gets Inconclusive, or Already handled under the 0.1.0 rules, not Hurts. Check the card's "Fired in" line.
- **A skill that rarely fires is reported as Inconclusive.** V1's skill fired in 1 of 27 runs, and its card says Inconclusive, the same word used for a wide interval. A fix is proposed in [docs/review-queue.md](docs/review-queue.md): a Rarely fired verdict under a 10% fire rate, and a warning under 50%. It isn't applied.
- **The bootstrap is optimistic when runs agree.** In 8 of the 13 planted cards that have an interval, it collapsed to a single point, such as +100 to +100.
- **Results come from one small model.** See [what wasn't checked](#what-wasnt-checked).
- **Only one plugin per result.** Cards name the first plugin in the suite.
- **Cost, not tokens.** The eval result reports each run's estimated cost at list price, not its tokens, so that's what the card compares.

## Setup

Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/mpwilso/mordecai
cd mordecai
uv sync
```

Check your cases, run your skill's eval with a pinned model, then read it:

```
uv run mordecai lint path/to/plugin
claude plugin eval path/to/plugin --model claude-sonnet-5-5 --json result.json --no-publish --max-cost-usd 5
uv run mordecai identify result.json --skill path/to/plugin --card card.json --markdown card.md
uv run mordecai check card.json --model claude-sonnet-5-5
```

- `lint` exits 1 if the case files would get any warning.
- `identify` prints the card, and can write it as JSON and as Markdown for a pull request. `--fail-on hurts,invalid` makes it exit 1 on those verdicts, for CI.
- `check` exits 1 when the skill or its cases have changed since the card was written. With `--model`, it also exits 1 when the card was measured on a different model.

Cards store paths relative to where the card is written, so a card still checks after the repository is cloned somewhere else.

A worked example from the planted check: suite 2's Haiku card still matches its files, but it is stale for Sonnet.

```
$ uv run mordecai check docs/planted-results/2-commits.card.json --model claude-sonnet-5-5
Stale: docs/planted-results/2-commits.card.json
  - The card was measured on claude-haiku-4-5-20251001, not claude-sonnet-5-5.
```

## What's next

1. A way to report a skill that rarely fires, distinct from Inconclusive. A proposal and its effect on every recorded card are in [docs/review-queue.md](docs/review-queue.md); it isn't applied.
2. A planted skill with a moderate effect, to check the simulation's +20 point finding on real runs.
3. `mordecai measure`: run the eval with a pinned model and a cost cap, then write the card, in one step.
4. A registry template: a Git repo that's also a Claude Code plugin marketplace, with a GitHub Action that posts each skill's card on its pull request and blocks the merge on Hurts, Invalid or a stale card.

## Prior art

- [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) runs the cases, both arms and the graders. Mordecai only reads its result.
- [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) and [SkillsBench](https://arxiv.org/abs/2602.12670) measured how often skills help, with and without.
- [NVIDIA SkillEvaluator](https://developer.nvidia.com/blog/evaluating-ai-agent-skill-performance-with-nvidia-skillevaluator/) reports a with-minus-without "skill lift", and says it doesn't report confidence intervals.

## License

MIT. See [LICENSE](LICENSE).
