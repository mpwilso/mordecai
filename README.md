<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/lockup-dark.svg">
    <img src="docs/brand/lockup-light.svg" alt="Mordecai: a potion flask on a round badge, filled above a dashed line across the bulb" height="72">
  </picture>
</p>

<p align="center"><b>Skill catalogs count downloads. Mordecai checks whether the skill helps.</b></p>

<p align="center">v0.1: the verdict rules have not yet been checked against real eval runs.</p>

Status: A portfolio project, built to show how I design, test and judge an AI tool. Version 0.1, a first slice. It reads real eval results and writes a card. Its rules have been checked on simulated skills with a known effect, and not yet on planted skills with real runs.

Mordecai is for teams that share Claude skills. Claude Code already runs a skill's test cases with and without the skill (`claude plugin eval`). Mordecai reads that result and decides what the skill can honestly claim: it helps, it hurts, the model already handles it, or there isn't enough to tell. The card it writes is tied to the exact skill, cases and model it was measured on, so a team can see when a claim has gone stale.

It sits beside [Loupe](https://github.com/mpwilso/loupe), [Parallax](https://github.com/mpwilso/parallax), [ISR](https://github.com/mpwilso/isr) and [Polarizer](https://github.com/mpwilso/polarizer), and has no dependency on any of them.

Jump to [an example card](#what-a-card-looks-like), [the verdicts](#the-verdicts), [crawl mode](#crawl-mode), [how it was tested](#how-it-was-tested), [the limits](#known-limits) or [setup](#setup).

## Why it exists

Most shared skills don't measurably help, and nobody checks:

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

Every card also lists warnings that don't change the verdict: a model alias instead of a pinned ID, fewer than 3 runs per side, no case that checks the skill stays quiet, no case that checks it fired, and case prompts that name the skill (which tests whether the model follows an instruction, not whether it finds the skill).

## Crawl mode

`--crawl`, or `MORDECAI_MODE=crawl`, prints the same card as loot, in honor of Matt Dinniman's *Dungeon Crawler Carl*. Helps is ENCHANTED, Hurts is CURSED, Already handled is VENDOR TRASH, and Mordecai has opinions. On a terminal, the box opens first.

<p align="center"><img src="docs/brand/crawl-card.svg" alt="Crawl mode: a pixel treasure chest shakes, opens and lifts out a red potion, beside the card mordecai identify --crawl prints for a demo skill that helps" width="900"></p>

<p align="center"><sub>A demo skill with simulated results. The text is printed by the same code as the command.</sub></p>

The jokes come from fixed templates around the plain card's stat block. They can't change a number or a verdict, and a test checks that every number in crawl mode is also in plain mode.

Crawl mode is a fan nod. It isn't affiliated with or endorsed by the author or publisher, and its text is original.

## How it was tested

- **The result format** comes from a real `claude plugin eval` run (Claude Code 2.1.289, two runs per side, $0.07), not from the docs alone. Parsing ignores fields it doesn't use, as the format's docs ask.
- **Each verdict and warning** has a test on a constructed result, along with hashing, staleness and the command line. `uv run pytest` runs 37 tests.
- **The rules were run on simulated skills with a known effect**, 200 suites per row, in [docs/simulation.md](docs/simulation.md). A placebo was called Helps or Hurts in 2 to 4% of suites. A skill worth +40 points was called Helps in 94% of suites at 10 cases. A skill worth +20 points was called Helps only 52% of the time even at 15 cases; the rest were Inconclusive.

That last row is the main thing the simulation taught me. With pass or fail graders and 3 runs per side, these rules rarely claim an effect that isn't there, and often can't confirm one that is. An Inconclusive card usually means "measure more".

## Known limits

- **Not yet checked against real runs.** The next step is a set of planted skills whose effect is known in advance: one that encodes a convention the model can't know, one that restates what the model already does, one with an outdated rule that conflicts with the repo, one with a vague description, and a placebo. The simulation treats runs as independent coin flips; real cases share causes, and judges disagree with themselves.
- **The bootstrap is optimistic with few runs.** When every run in both arms agrees, the interval shrinks to a point.
- **Only one plugin per result.** Cards name the first plugin in the suite.
- **Staleness covers files, not the model.** `mordecai check` notices a changed skill or case. A new model only shows up as a different model on the next card.
- **Cost, not tokens.** The eval result reports each run's estimated cost at list price, not its tokens, so that's what the card compares.

## Setup

Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/mpwilso/mordecai
cd mordecai
uv sync
```

Run your skill's eval with a pinned model, then read it:

```
claude plugin eval path/to/plugin --model claude-sonnet-5-5 --json result.json --no-publish --max-cost-usd 5
uv run mordecai identify result.json --card card.json --markdown card.md
uv run mordecai check card.json
```

`identify` prints the card, and can write it as JSON and as Markdown for a pull request. `--fail-on hurts,invalid` makes it exit 1 on those verdicts, for CI. `check` exits 1 when the skill or its cases have changed since the card was written.

## What's next

1. `mordecai measure`: run the eval with a pinned model and a cost cap, then write the card, in one step.
2. The planted skills check, run for real, with every result published, including the misses.
3. A registry template: a Git repo that's also a Claude Code plugin marketplace, with a GitHub Action that posts each skill's card on its pull request and blocks the merge on Hurts, Invalid or a stale card.

## Prior art

- [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) runs the cases, both arms and the graders. Mordecai only reads its result.
- [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) and [SkillsBench](https://arxiv.org/abs/2602.12670) measured how often skills help, with and without.
- [NVIDIA SkillEvaluator](https://developer.nvidia.com/blog/evaluating-ai-agent-skill-performance-with-nvidia-skillevaluator/) reports a with-minus-without "skill lift", and says it doesn't report confidence intervals.

## License

MIT. See [LICENSE](LICENSE).
