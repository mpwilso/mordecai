# Open questions

What the planted skills check ran, what it found, and the questions it leaves open. Details for every run are in [planted-skills-results.md](planted-skills-results.md). The predictions are in [planted-skills.md](planted-skills.md) for the first set and the sealed holdouts, and in [validation-skills.md](validation-skills.md) for V1 to V3 and H1.

## What was run

The check ran 12 planted suites, 15 runs in all, almost all on Claude Haiku 4.5, at a total of $20.60 at list price. Each suite compares 9 cases, with 3 runs per side. Every prediction was committed before its suite ran.

**Only some suites were blind.** The first set (suites 1 to 5b) and holdouts 6 and 7 were written before any result existed. V1, V2, V3, H1 and both Sonnet reruns were designed or predicted after seeing earlier results.

- **Rules 0.1.0** applied to the first set.
- **Rules 0.2.0**, frozen at commit 64a7701, applied to everything after it. That release changed Already handled so it must also rule out a 10-point loss.
- **No run** hit a cost cap, went partial or came out Invalid.

## Scorecard

All on Claude Haiku 4.5 unless marked.

| Suite | Blind | Rules | Predicted | Actual | | Better / same / worse | Fired |
|---|---|---|---|---|---|---|---|
| 1 Made-up convention | Yes | 0.1.0 | Helps | Helps (+100) | Match | 9 / 0 / 0 | 27 of 27 |
| 2 Conventional Commits | Yes | 0.1.0 | Already handled | Helps (+78) | Miss (wrong premise) | 9 / 0 / 0 | 27 of 27 |
| 3 Outdated rule | Yes | 0.1.0 | Hurts | Already handled (-15) | Miss | 1 / 6 / 2 | 6 of 27 |
| 4 Vague description | Yes | 0.1.0 | Never fired | Never fired | Match | 0 / 9 / 0 | 0 of 27 |
| 5a Twin placebo | Yes | 0.1.0 | Not Helps or Hurts | Already handled | Match | 0 / 9 / 0 | 15 of 27 |
| 5b Filler placebo | Yes | 0.1.0 | Not Helps or Hurts | No effect | Match | 0 / 9 / 0 | 27 of 27 |
| V1 Outdated rule meant to fire | No | 0.2.0 | Hurts | Inconclusive (-11) | Miss | 0 / 7 / 2 | 1 of 27 |
| V2 Not-inert "placebo" | No | 0.2.0 | Not Helps or Hurts | Hurts (-37) | Design defect | 0 / 3 / 6 | 27 of 27 |
| V3 Inert placebo | No | 0.2.0 | Not Helps or Hurts | Inconclusive (-11) | Match | 2 / 3 / 4 | 27 of 27 |
| Holdout 6 Changelog format | Yes | 0.2.0 | Helps | Helps (+100) | Match | 9 / 0 / 0 | 27 of 27 |
| Holdout 7 Filler placebo | Yes | 0.2.0 | Not Helps or Hurts | No effect | Match, weak evidence | 0 / 9 / 0 | 27 of 27 |
| H1 Conflicting convention | No | 0.2.0 | Hurts | Hurts (-100) | Match | 0 / 0 / 9 | 27 of 27 |
| 1 on Sonnet 5.5 | No | 0.1.0 | (no written prediction) | Helps (+100) | Unchanged | 9 / 0 / 0 | 27 of 27 |
| 2 on Sonnet 5.5 | No | 0.2.0 | Helps | Helps (+100) | Match; baseline moved the other way | 9 / 0 / 0 | 27 of 27 |

What the scorecard shows:

- **First set:** 3 of 5 skills got their predicted verdict, so the check failed on the criterion written in advance.
- **Holdout 7 is weak evidence.** Its baseline was 0%, so it could only have shown a false gain, and its text isn't inert.
- **Placebos.** No placebo was called Helps or Hurts. Only one, V3, ran on noisy runs: it fired in all 27 runs, all 3 runs agreed in only 16 of 24 case-and-side cells, and its card said Inconclusive (-11, interval -33 to +11). V2's Hurts was a real effect of an instruction in its text, not a false call.
- **Hurts.** It was detected once, in H1, which was designed so its skill would fire in every run. Harmful skills that fired in 6 of 27 runs (suite 3) or 1 of 27 (V1) were not called Hurts.
- **Haiku vs Sonnet.** Neither rerun moved a verdict. On suite 2, Sonnet used a Conventional Commits prefix unprompted in 0 of 27 runs, against Haiku's 5, so the change grew from +78 to +100.

## Open question 1: report skills that rarely fire distinctly (proposed for 0.3.0, not applied)

V1's skill fired in 1 of 27 runs, and its card said Inconclusive, the same word used for a wide interval. The practical message is different: the skill is almost never used, so its description needs fixing before anything else can be measured.

Fire rates on the 14 recorded cards: 100% on 10 cards, 56% (5a), 22% (suite 3), 4% (V1) and 0% (suite 4, already Never fired).

| Proposal | What it does | Cards it changes |
|---|---|---|
| A. A verdict, "Rarely fired", when the skill fires in under 10% of the runs that needed it, checked right after Never fired | Replaces the verdict | V1 only: Inconclusive becomes Rarely fired |
| B. The same verdict at under 25% | Replaces the verdict | V1, and suite 3 (Already handled under 0.1.0, Inconclusive under 0.2.0) becomes Rarely fired |
| C. A warning, not a verdict, under 50%: "Fired in only N of M runs; the change mostly reflects runs where the skill wasn't used" | Adds a warning | Suite 3 and V1 get the warning; no verdict changes. 5a (56%) does not |

**The tradeoff.** A distinct verdict under 10% says the right thing when there is almost no skill use to measure. A higher threshold (B) would hide suite 3's real harm: its skill gave the wrong answer in 5 of the 6 runs where it fired. The combination considered most useful is A and C together, plus a card line comparing runs where the skill fired with runs where it didn't. In suite 3: when it fired, 1 of 6 runs passed; when it didn't, 20 of 21. That line is diagnostic only, because a skill fires on particular cases. The proposal was designed after seeing V1, so it would need a new suite where a skill fires rarely before it could count as tested. That costs about $1.30 on Haiku.

## Open question 2: test the +20 point finding on real runs

In simulation at the observed 94% run agreement, a skill worth +20 points is called Helps in 13%, 36% and 56% of suites at 5, 10 and 15 cases ([simulation.md](simulation.md)). No planted skill had a true effect between +10 and +30. The measured changes were -100, -37, -15, -11, 0, +78 and +100. So the finding hasn't been tested on real runs.

**The tradeoff.** A planted skill with a moderate effect is harder to build than a made-up convention, because its effect has to be partial by design, such as a convention the model sometimes follows unprompted. To say anything useful, it needs about 15 cases, which costs more than the 9-case suites so far: roughly $2 per suite on Haiku.

## Open question 3: more models

Two suites were rerun on Claude Sonnet 5.5, and neither verdict moved. All other results are for Claude Haiku 4.5.

**The tradeoff.** Another model would show whether verdicts move across models, which neither rerun did. A judge-graded suite would test something the check hasn't touched at all: every grader so far was a regex or a tool-use check, so judge disagreement was never in play. Of the two, a judge-graded suite would add more new information per dollar.

## Open question 4: runs a mock aborted

`claude plugin eval` marks a run `aborted` when a [mock](https://code.claude.com/docs/en/plugin-evals)'s `expect:` or `abort_when` stops it. The run scores 0 and its `error` stays null, so Mordecai reads it as an ordinary failed run. That is the same trap as a rate limit: a run that says nothing about the skill can still move the change. No recorded result has an aborted run, since none of the planted suites uses mocks.

**The tradeoff.** Treating aborted runs like rate-limited ones, as Invalid, would be a rule change, so it isn't made here. It would only matter for suites with mocks, and it could hide a skill that makes the agent call a tool the wrong way, which is a real effect. Counting aborted runs in a warning would be a smaller first step.

## Open questions from the skill library

The library added in 0.3.0 leaves these trade-offs open. The decisions it did make are in [decisions.md](decisions.md).

### Open question 5: version stamps in frontmatter

A copy's version and lineage live in its `CHANGELOG.md`. The `mordecai-version`, `mordecai-variant` and `mordecai-based-on` metadata keys are optional, and checked against the changelog when present (decision D4).

**The tradeoff.** Required stamps would make every installed copy carry its own version. But a card hashes the skill folder's exact bytes, so a stamp written at release changes those bytes, and a skill measured before it joined the library, like the planted variants, couldn't carry stamps without losing its card. Requiring them would mean re-measuring those variants.

### Open question 6: what a library repository publishes at its root

This repository publishes one skill, `mordecai`, in `skills/` (decision D15). With no skill in a standard folder, npx skills searches the whole repository and, among same-named copies, installs whichever it lists first.

**The tradeoff.** `npx skills add --full-depth` still searches everything, including the planted suites' deliberately harmful skills. Closing that would mean marking the planted skills `metadata.internal`, which changes the bytes their cards measured, or moving the suites, which changes paths the docs cite. For now the README says not to use `--full-depth` on this repository.

### Open question 7: `release` makes a commit

A tag has to point at a commit that holds the updated changelog, so `release` commits the copy's folder and refuses when anything else is uncommitted, as `npm version` does.

**The tradeoff.** The alternative, where the author commits and `release` only tags, adds a manual step to every release and can tag a commit whose changelog doesn't match, which install would then refuse.

### Open question 8: unverified client setups

The setup snippets for VS Code with Copilot, Cursor and Codex in [library.md](library.md#setup) follow each tool's docs, but none has been run in its client. Open points are the folder each client starts a stdio server in and whether each passes `MORDECAI_GITHUB_TOKEN` through. This repository's `.mcp.json` for Claude Code can be tried without changing any user config.

### Open question 9: no size limit on fetches

Each Git call stops after five minutes, and reading a source's files is capped at 200 MB, but the fetch itself can download a large repository into the cache before that.

**The tradeoff.** A size check before the first fetch would need the GitHub API, and a token for private repositories. It is accepted as a limit for now.
