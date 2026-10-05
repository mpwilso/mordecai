# The planted skills check

The question: do Mordecai's verdict rules hold up on real eval runs? Each planted skill below is built so its effect is known in advance. The predictions, the pass criterion and the plan were written and committed before any of these suites ran. Results go in [planted-skills-results.md](planted-skills-results.md), including the misses.

The fixtures are written by `scripts/planted.py` into [evals/planted/](../evals/planted/). Each skill is its own plugin, because `claude plugin eval` drops the whole plugin under test from the baseline arm; one plugin holding every skill would measure them all together.

## How every suite is built

- 12 cases: 9 the skill should change, each with an outcome grader (a regex on the reply) and a "the skill fired" grader, and 3 nearby requests where the skill should stay quiet (a `tool_used` Skill grader with `min: 0`, `max: 0`, `arm: both`).
- No prompt names its skill, and `mordecai lint` reports no warnings for any suite. `tests/test_planted.py` checks both.
- Only regex and `tool_used` graders, so no judge model is called and grading is the same every time.
- Every case allows `Read`, `Glob`, `Grep` and `Skill`. Cases run 3 times per side, the default.

## The skills and the predictions

| # | Suite | Skill | Expected verdict |
|---|---|---|---|
| 1 | `1-convention` | `ferry-workflow` | Helps |
| 2 | `2-commits` | `commit-messages` | Already handled |
| 3 | `3-outdated` | `python-project-commands` | Hurts |
| 4 | `4-vague` | `notes` | Never fired |
| 5a | `5a-twin` | `ferry-workflow-twin` | Not Helps, not Hurts |
| 5b | `5b-filler` | `ferry-helper` | Not Helps, not Hurts |

**1. A convention the model can't know: Helps.** Branches are named `qrx-<ticket>--<summary>` and pull request descriptions end with the line `Ferry-Check: pending`. The prefix, the double hyphen and the footer are made up, so without the skill no run should pass, and with it most should. Miss if: the skill rarely fires, or it fires and the model ignores it.

**2. Something the model already does: Already handled.** The skill restates Conventional Commits, and the cases ask for commit messages. The rule needs the model to score at least 90% without the skill. Risk: if the model doesn't default to Conventional Commits often enough, the honest verdict is Helps or Inconclusive. That would be a wrong prediction about the model, not a wrong rule, and will be reported as a miss either way.

**3. An outdated rule that conflicts with the repo: Hurts.** Each case's workspace is a small Python project that uses uv, pytest, ruff and Python 3.12, with a README and Makefile that say so. The skill insists on `pip install -r requirements.txt`, `python setup.py test`, flake8, black and Python 3.8. Without the skill the model can read the repo and get it right. With the skill, it may follow the skill. Risk: a careful model notices the conflict and trusts the repo, which would give No effect or Already handled.

**4. Good content, a vague description: Never fired.** The skill holds a real release tag convention, but its description is "General notes." The cases ask for release tags. Risk: the model opens the skill anyway on some runs. Then the verdict depends on how often, and the prediction misses.

**5a. A twin measured against itself: neither Helps nor Hurts.** An exact copy of skill 1 under another name. The eval can't load another skill into the baseline arm, since only the plugin under test loads, so the twin is measured against its own text: every case appends skill 1's text to the system prompt in both arms. The skill can add nothing the baseline doesn't already have. The most likely verdict is **Already handled**, because both arms should score high. It may also be Never fired, if the model sees the rule in its prompt and never opens the skill.

**5b. Filler that changes nothing: neither Helps nor Hurts.** Same description and cases as skill 1, but the body is generic advice with no convention in it. Both arms should fail the convention graders, so the most likely verdict is **No effect**.

## Holdouts: written, not run

| # | Suite | Skill | Expected verdict |
|---|---|---|---|
| 6 | `holdout/6-convention` | `changelog-format` | Helps |
| 7 | `holdout/7-filler` | `changelog-helper` | Not Helps, not Hurts |

**6.** A made-up changelog format, `ZK-<ticket> | <area> | <summary>`, built like skill 1. **7.** The same description and cases as 6, with a filler body, built like 5b.

The holdouts run exactly once, after the main set has run and after any proposed rule change is written down. They are the only test of a rule change.

## Pass criterion

Decided before anything runs:

- **The check passes only if all six suites get the outcome in the table above.** Each suite is scored as a match or a miss. A miss is reported as a miss, with the card and the numbers, whatever the reason.
- **For 5a and 5b, the hard requirement is no Helps and no Hurts.** That is the false-positive test. You named No effect or Inconclusive as the acceptable verdicts. I expect 5a to come out Already handled, for the reason above. So each placebo is scored twice: on the false-positive test, and on whether it landed on No effect or Inconclusive. An Already handled or Never fired twin passes the first and misses the second, and is reported that way.
- **Every miss gets a second question:** given the card's own numbers, did the rules apply correctly? A miss where the rules read the numbers correctly but the model behaved differently than predicted is a prediction miss. A miss where the numbers support a different verdict than the rules gave is a rule miss. Only rule misses can justify a rule change.
- **Invalid counts as a miss.** If a suite is Invalid because of infrastructure, such as a rate limit or the cost cap, it may be rerun once, and both cards are reported.

## Fixed for the whole check

- **The rules are frozen** as `src/mordecai/verdict.py` and `Rules()` stand in the commit that adds this file: 5 cases minimum, a 90% interval, a 10-point minimum effect, a 90% ceiling, 2000 resamples, seed 0. If a result looks wrong, a rule change is proposed separately and tested only against the holdouts.
- **One pinned model ID** for every suite, holdouts included, set with `--model`. Every call also passes `--no-publish`, `--max-cost-usd` and `--scaffold` (suite 3 needs it to build its workspace). Raw results go to `evals/results/`, which git ignores. Each card and its cost go into planted-skills-results.md.
- **No reruns to get a better answer.** A suite runs once, except for the infrastructure case above.
