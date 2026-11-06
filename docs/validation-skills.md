# Validation skills

**These two suites were written after the first planted-skills results were known, so they are a validation set, not a blind test.** They were designed to probe the two weak spots that run exposed:

- an outdated skill that did harm but rarely fired (suite 3);
- placebos that gave the rules no noise to misread (suites 5a and 5b).

The predictions and the pass criterion below were committed before either suite ran.

The verdict rules are the 0.2.0 rules, frozen at commit 64a7701. That commit changed Already handled so it must also rule out a 10-point loss. The fixtures are written by `scripts/planted.py` into [evals/planted/validation/](../evals/planted/validation/). Each suite has 12 cases (9 compared, 3 where the skill should stay quiet). No prompt names its skill, and `mordecai lint` reports no warnings for either suite.

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

After V1 and V2, the two original holdout suites run exactly once each. Both were written and committed in bd92b23, before any result existed: `holdout/6-convention`, predicted Helps, and `holdout/7-filler`, predicted not Helps and not Hurts. Their predictions are in [planted-skills.md](planted-skills.md) and are not changed here. They run under the 0.2.0 rules. The rule change can't alter either prediction: one expects a large gain, and the other a placebo with a failing baseline.

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

## H1: a Hurts check that must fire (`h1-must-fire`, skill `branch-naming`)

Written after V1, where an outdated skill fired in 1 of 27 runs, so no harm could be measured.

**The setup.** The skill encodes a made-up branch convention the model can't know: summary first in CamelCase, then an at sign and the ticket number, as in `FixLoginTimeout@1042`, with no hyphens or slashes. Its description ("Use when naming a git branch for work tracked in this team's ticket system.") is close to suite 1's, which fired in 27 of 27 runs. The 9 compared prompts each ask for a branch name for a team ticket, worded like suite 1's.

**The graders require the opposite of the skill.** They want the ticket number followed by a lowercase, hyphenated summary, such as `fix/3301-password-reset-spam` or `3301-fix-password-reset-email`. That is the form Haiku used without any skill in suite 1: `fix/1042-login-timeout-mobile`, `6020-speed-up-nightly-report`. So the model should pass without the skill and fail whenever it follows the skill. 3 quiet cases are nearby git questions and a temperature conversion.

**Prediction: Hurts.** Without the skill, most runs should pass. With it, the skill should fire, because the model can't know a team's branch convention without opening it, and following it fails every case.

**Pass criterion.**
- **H1 must come out Hurts.** Anything else is a miss, reported with the card and a case-level diagnosis.
- **The fire rate is reported.** If the skill fires in fewer than half the runs that needed it, that is the finding: Hurts can only be detected when the skill is actually opened. One labeled second attempt is allowed, and no more.

## R1: a skill meant to fire rarely (`r1-rarely-fires`, skill `workspace-commands`)

Written on 2026-10-11, after every earlier result and after the Rarely fired rule (D21), to test that rule on runs it wasn't designed from. **Not blind:** the design uses suite 3's per-case fire counts. The prediction below is committed and pushed before the suite runs. The rules are the 0.4.0 rules, frozen at commit 4a94b17.

**The setup.** The workspace is suite 3's small uv project (pyproject.toml, a Makefile, a README, uv.lock), and the prompts are in suite 3's style: "Look at the project in the current directory and tell me ... Reply with only the answer." The 9 compared questions are suite 3's seven that the repo answers on its own (run the tests, lint, format, install, run one test file, lint and fix, the minimum Python version), plus two more it also answers: stop at the first failing test, and check the formatting without changing files. Suite 3's two dependency-adding questions are left out. The skill's description names exactly these tasks. Its body is correct: the same commands the repo uses, so following it can't lower a score, and the graders accept the repo's answer with or without the skill. 3 quiet cases ask what a pytest fixture is, what a .gitignore does, and a unit conversion.

**Why it should fire rarely, but not never.** In suite 3, Haiku answered these questions from the repo's files without opening the skill: 0 of 18 runs fired on the six questions R1 keeps from it besides "install", and 1 of 3 fired on "install". The runs where suite 3's skill fired most were the dependency-adding questions (3 of 3 and 2 of 3), which R1 drops. That predicts about 1 fire in 27.

**Prediction.**

- **Fire rate: 1 or 2 of the 27 runs that need it** (above 0%, under 10%).
- **Verdict: Rarely fired.**
- **Quiet cases:** 0 misfires in 9 runs.
- Not part of the prediction: the result section will also report what the 0.3.0 rules (commit 328bc59) say on the same result. With a baseline expected near suite 3's 93% and a skill that agrees with the repo, Already handled or Inconclusive is likely there.

**What would make it a miss.**

- **0 of 27: Never fired.** The skill wasn't opened at all, so the rule wasn't exercised. Reported as a miss of the fire-rate prediction.
- **3 or more of 27:** the verdict comes from the interval, with D21's warning if under half. The rule wasn't exercised. Reported as a miss.
- **Invalid** (a usage or rate limit, or the cost cap): no reading. Recorded, not counted either way.

**Pass criterion.**

- R1 must fire in 1 or 2 of 27 runs and read Rarely fired. Anything else is a miss, reported with the card, the per-case fire counts and a diagnosis.
- The verdict follows from the fire count by construction, so what this tests is whether a skill can be designed to land in the band on new runs, and whether a Rarely fired card says something more useful than the interval verdict it replaces. One suite can't show that the 10% threshold is right.
- R1 runs once, on `claude-haiku-4-5-20251001` with the same model as judge, 3 runs per side, with a $3 cap, the spend ceiling the owner set for it. It is not rerun to get a better answer. If a case file has a real defect, the original result is recorded, the fix goes in a separate commit, and one labeled second attempt is allowed if it fits under the same $3.
- Claude Code is now 2.1.296, against 2.1.289 when suite 3 ran. A change in how it offers skills could move the fire rate either way.

## R2: a skill meant to fire rarely, measured first (`r2-rarely-fires`, skill `project-background`)

Written on 2026-11-05, after R1 missed, to do what [open question 1](open-questions.md) says: measure a candidate skill's fire rate first, then freeze the suite and predict. **Not blind:** the design uses R1's result and its per-case fire counts. The rules are the 0.6.0 rules, unchanged since 0.5.0 (D22). Claude Code is 2.1.310.

**The candidate pool.** 15 questions about suite 3's small uv project (pyproject.toml, a Makefile, a README, uv.lock), in R1's wording: "Look at the project in the current directory and tell me ... Reply with only the answer." R1's nine questions, plus six more the repo answers on its own: the project's name, the linter's line length, the test directory, the one runtime dependency, the dev dependency group, and which tool wrote the lock file. The skill's body is R1's, correct and the same as the repo, so following it can't change a score. Its description is "Background on how the tally project in this workspace is set up.": it names the project but no task, to sit between R1's description (named every task; fired 15 of 27) and suite 4's "General notes." (fired 0 of 27). 3 quiet cases, R1's.

**The pilot.** The whole pool runs once as one plugin, `evals/pilot/r2-candidates`, with the skill arm only (`--ablation none`), 3 runs per case, on `claude-haiku-4-5-20251001`, with a $1.50 cap. It is the fire-rate measurement, nothing more: its scores are not a card.

**The selection rule, fixed before the pilot runs.**

1. Count fires per compared case, out of 3 runs.
2. Take the 9 cases with the fewest fires, ties broken by pool order (the order in `R2_POOL`).
3. If those 9 total 0 fires and some other case fired exactly once, swap that case in for the last one chosen, so the suite has 1 expected fire.
4. The frozen suite is those 9 cases plus the 3 quiet cases, under the name `validation/r2-rarely-fires`, written by `scripts/planted.py` from `R2_CHOSEN`.
5. If the 9 chosen total 0 fires with no swap possible, or 3 or more, the pool cannot land in the band. The pilot is recorded as the finding and R2 stops without a frozen run.

**Prediction, to be completed from the pilot's counts before the frozen run.** The frozen suite fires in the band 1 to 2 of 27 runs that need it, its verdict is Rarely fired, and the quiet cases fire 0 of 9. The exact expected count is the chosen cases' pilot total, and is written in below once known.

**What would make it a miss.**

- 0 of 27: Never fired, the rule not exercised.
- 3 or more of 27: the verdict comes from the interval, with D21's warning under half. The rule not exercised.
- Invalid: no reading. Recorded, not counted either way.

**Pass criterion.**

- R2 must fire in 1 or 2 of 27 runs and read Rarely fired. Anything else is a miss, reported with the card, the per-case fire counts and a diagnosis.
- The frozen suite runs once, on `claude-haiku-4-5-20251001` with the same model as judge, 3 runs per side, with a $3 cap, the ceiling the owner set for it on 2026-11-05. No rerun to get a better answer.
- Since the cases were chosen on the pilot's counts, a match shows that a fire rate measured for the same skill on the same questions carries over to a second run, which R1 could not show. It does not show that the 10% threshold is right.

## M1: a moderate effect by design (`m1-moderate`, skill `commit-types`)

Written on 2026-11-05, to check [open question 2](open-questions.md): in simulation, a skill worth +20 points is called Helps in 36% of suites at 10 cases and 56% at 15, and no planted skill so far had a true effect between +10 and +30. **Not blind:** the design uses the commit-message results from suite 2, V2 and V3. The rules are the 0.6.0 rules, unchanged since 0.5.0. Claude Code is 2.1.310.

**The setup.** 15 compared cases, not 9: suite 2's nine commit-message changes and the first six of the V2 pool. The skill's description is suite 2's ("Use when writing a git commit message."), which fired 27 of 27 there. Its body teaches the Conventional Commits type prefix, `<type>: <summary>`, with the type list and the summary rules, and says nothing about a scope. **The grader requires more than the skill teaches:** a type and a scope in parentheses, `type(scope): summary`. 3 quiet cases, suite 2's.

**Why a partial effect.** Without a skill, Haiku almost never writes a scoped prefix: 0 of 27 runs in suite 2, 1 of 27 in V2 and 1 of 27 in V3. With suite 2's skill, whose body shows the scope as optional, it wrote one in 14 of 27 runs, and the count varied inside cases (0, 2, 3, 0, 1, 2, 1, 2, 3 of 3 across the nine cases). A body that leaves the scope out should produce scopes less often than that body did, so the with-skill pass rate should land between the baseline's near zero and 52%. The effect is partial because the model has to add the scope on its own once it is writing in the format, and the runs should disagree inside cases, as they did in suite 2. That is the shape the simulation modeled.

**Prediction.**

- **Change: between +10 and +30 points.** With the skill, scoped prefixes in 15% to 45% of the 45 compared runs; without it, 0 to 2 of 45.
- **Verdict: Helps or Inconclusive.** Both are what the simulation says a +20 point skill gets at 15 cases, about half each. Which one depends on whether the bootstrap interval clears zero, which 15 cases may or may not do. A miss is any other verdict.
- **Fired:** 45 of 45, since the description is suite 2's. If it fires in under half the runs, the test is weak and is reported that way.
- **Quiet cases:** 0 misfires in 9 runs.

**What would make it a miss.**

- A change under +10: the model doesn't add scopes once in the format, and the card reads No effect or Inconclusive with an interval around zero. A prediction miss about the model, not a rule miss, unless the numbers support a different verdict than the rules gave.
- A change over +30: the type prefix pulls the scope with it more often than suite 2's optional mention did. A prediction miss; the suite then measured a large effect, not a moderate one.
- Hurts, Already handled, Never fired or Rarely fired: reported with a case-level diagnosis.
- Invalid: no reading. Recorded, not counted either way.

**Pass criterion.**

- M1 passes if the change is between +10 and +30 and the verdict is Helps or Inconclusive. Each is scored on its own: a +25 change called Helps is a full match; a +25 change called Inconclusive is a full match; a +35 change called Helps is a miss on the change.
- M1 runs once, on `claude-haiku-4-5-20251001` with the same model as judge, 3 runs per side, 18 cases, with a $3 cap, the ceiling the owner set for it on 2026-11-05. No rerun to get a better answer. If a case file has a real defect, the original result is recorded, the fix goes in a separate commit, and one labeled second attempt is allowed if it fits under the same cap.
- One run cannot check the simulation's rate (Helps about half the time). What it can check is whether a real partial effect lands where the simulation puts it: inside the band, with the verdict one of the two the rate allows.
