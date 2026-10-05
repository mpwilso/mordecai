# Validation skills

**These two suites were written after the first planted-skills results were known, so they are a validation set, not a blind test.** They were designed to probe the two weak spots that run exposed:

- an outdated skill that did harm but rarely fired (suite 3);
- placebos that gave the rules no noise to misread (suites 5a and 5b).

The predictions and the pass criterion below were committed before either suite ran.

The verdict rules are the 0.2.0 rules, frozen at commit 03d2619. That commit changed Already handled so it must also rule out a 10-point loss. The fixtures are written by `scripts/planted.py` into [evals/planted/validation/](../evals/planted/validation/). Each suite has 12 cases (9 compared, 3 where the skill should stay quiet). No prompt names its skill, and `mordecai lint` reports no warnings for either suite.

## V1: an outdated rule that fires (`v1-outdated`, skill `python-dependencies`)

**Prediction: Hurts.**

**The setup.** The workspace is the same small uv project as suite 3. The skill says dependencies are managed with pip and requirements files. Its description names every dependency task outright, and all 9 compared prompts are dependency tasks: add, add for development, remove, upgrade, install everything, add with a version floor, add another package, relock, add another dev package.

**Why Hurts.** In suite 3, the skill fired in only 6 of 27 runs. All 6 were on dependency questions, and in 5 of them the model gave the outdated pip answer. Without the skill, the model read the repo and answered with uv: 25 of 27 baseline runs passed. V1 keeps only the kind of question that made the skill fire.

**Grading.** Each grader requires the uv command and rejects any answer mentioning requirements, `pip install`, `pip uninstall` or `pip freeze`.

**What would make it a miss.**
- The skill fires rarely again, and the change is too small or too uncertain to call. Under 0.2.0 that gives Inconclusive.
- The model trusts the repo over the skill when they conflict.

## V2: a filler placebo on a noisy task (`v2-noisy-placebo`, skill `commit-helper`)

> **Relabeled after the run: a design defect.** The body below says "Say what changed in plain words", which is a behavior-changing instruction, not inert filler. Without the skill, 10 of 27 runs used a Conventional Commits prefix. With it, 0 of 27 did. That is a real effect, and the rules read it correctly as Hurts. V2 did not test whether an inert placebo stays out of Helps and Hurts on noisy runs. V3, below, is that test. The text of this section is otherwise as it was committed before the run.

**Prediction: not Helps, not Hurts.** No effect or Inconclusive are both acceptable, and so is Already handled.

**The setup.** The skill fires on commit messages, as suite 2's skill did 27 of 27 times. Its body is generic advice with nothing about format. The grader is suite 2's Conventional Commits pattern, which Haiku 4.5 met in only 5 of 27 runs without a skill, and not consistently within a case.

**The pilot.** It cost $0.25, recorded in [planted-skills-results.md](planted-skills-results.md). It ran 10 new commit-message candidates once each with no skill, to find cases whose baseline is neither always passing nor always failing. The selection rule was fixed before the pilot ran:

1. Take the 4 suite-2 cases whose 3 baseline runs disagreed: commit-2, commit-4, commit-5 and commit-6.
2. Then add candidates whose pilot run passed.
3. Then add candidates that failed, in pool order, up to 9.

All 10 candidates failed their single run, so the last 5 are the first 5 of the pool (ci-workflow, readme-link, bump-pytest, csv-tests, docstring-typo). **V2's noise comes mainly from the 4 suite-2 cases.** It will be less noisy than hoped, and its run-agreement rate is recorded with the result.

**Why not Helps or Hurts.** The body adds nothing about commit format, so any difference between the two sides is noise. This is the false-positive test that suites 5a and 5b couldn't be, because their runs never disagreed.

## Pass criterion

- **V1 must come out Hurts.** Anything else is reported as a miss, with the card, the numbers and a case-level diagnosis.
- **V2 must not be Helps or Hurts.** If it is, that's a false positive. It is recorded, and the check stops.
- Neither suite is rerun to get a better answer. If a case file has a real defect, the original result is recorded, the fix goes in a separate commit, and the suite is rerun once as a labeled second attempt.

## The sealed holdouts

After V1 and V2, the two original holdout suites run exactly once each. Both were written and committed in 6c37ff9, before any result existed: `holdout/6-convention`, predicted Helps, and `holdout/7-filler`, predicted not Helps and not Hurts. Their predictions are in [planted-skills.md](planted-skills.md) and are not changed here. They run under the 0.2.0 rules. The rule change can't alter either prediction: one expects a large gain, and the other a placebo with a failing baseline.

## V3: an inert placebo on V2's cases (`v3-inert-placebo`, skill `team-background`)

Written after V2's result, to run the test V2 was meant to be.

**The setup.** These are V2's 12 cases with the same prompts and the same outcome graders, reused without a new pilot. Only the skill differs. Its description, "Use when writing a git commit message.", is the same as V2's and suite 2's, so it should fire as theirs did, 27 of 27. Its body is three facts that have nothing to do with commits: the team formed in 2019 and has six people, it plans on Tuesdays at 10:00, and the office is on the fourth floor next to the kitchen.

**Inertness criterion**, enforced by `test_v3_is_inert` in tests/test_planted.py:
- Every sentence in the body is a statement of fact, not an instruction.
- The body uses none of these words: commit, message, git, write, format, style, tone, short, long, length, prefix, type, word, plain, brief, clear, concise, summary, describe, should, must, always, never, use, keep, say, avoid, prefer, conventional, feat, fix, chore, docs.
- The facts are unrelated to anything the graders check.

The folder-layout example was passed over because folder names such as `api/` could suggest a commit scope.

**Prediction: not Helps, not Hurts.** If the skill changes nothing, both sides should look like V2's baseline: about 10 of 27 runs with a prefix, varying within cases. That leaves the interval too wide to call, or near zero. Inconclusive and No effect are the likely verdicts. Already handled is acceptable but unlikely, given a baseline around 37%.

**Pass criterion.**
- **V3 must not be called Helps or Hurts.** If it is, that is a real false positive. It will be recorded prominently, the rules will not change, and the remaining steps will continue.
- **The fire rate is reported with the result.** If the skill fires in fewer than half the runs that needed it, the test is weak and is reported that way.
- **Merely opening a skill could shift the output.** In V2, runs with the skill took about 3 turns against 1.2 without, so firing changes the conversation even when the body says nothing. If V3 moves anyway, that effect is a finding about firing, not about the skill's text.
