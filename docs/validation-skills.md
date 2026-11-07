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

### R2 result: the pilot fired in none of 45 runs, so no suite was frozen

The pilot ran once on 2026-11-07 (UTC), on `claude-haiku-4-5-20251001`, Claude Code 2.1.310, skill arm only, 3 runs per case, for $1.21 under its $1.50 cap. **The skill fired in 0 of the 45 runs that needed it, on every one of the 15 candidates, and in 0 of the 9 quiet runs.** The 9 cases with the fewest fires total 0 and no case fired once, so step 5 of the selection rule applies: the pool can't land in the band, and R2 stops here without a frozen run. The $3 set aside for that run was not spent.

**The description set the fire rate, not the questions.** On the same uv project and mostly the same questions, R1's description, which named every task, fired in 15 of 27 runs. This one, which names the project and no task, fired in none of 45, as suite 4's "General notes." did. Neither wording landed in the 1 to 2 of 27 that Rarely fired needs, and one pilot can't find a wording between them that does. The answers came from the repo whatever the skill did: the outcome graders passed in 42 of 45 runs, and the three misses (proj-format-check twice, which answered with the lint command, and proj-one-file once, with a bare `pytest`) never opened the skill. **Rarely fired is still untested on runs it wasn't designed from.**

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

### M1 result: No effect, a miss

M1 ran once on 2026-11-07 (UTC), on `claude-haiku-4-5-20251001` with the same model as judge, Claude Code 2.1.310, for $1.97 under its $3 cap. [Card](planted-results/m1-moderate.card.json).

| Predicted | Card | Score | Better / same / worse | With / without | Fired | Run agreement |
|---|---|---|---|---|---|---|
| +10 to +30, Helps or Inconclusive | No effect (-2, interval -9 to +0) | Miss on both | 0 / 14 / 1 | 0% / 2% | 45 of 45; 0 of 9 quiet | 29 of 30 cells |

**The change was -2, under +10, and No effect is neither predicted verdict.** With the skill, no run wrote a scope: 0 of 45. Without it, 1 of 45 did (bump-pytest run 2, `chore(deps): upgrade pytest from 7.4 to 8.2`), which is the one worse case.

**Diagnosis: a prediction miss about the model. The rules read the numbers correctly.**

- **The skill worked on what it taught.** With it, all 45 replies started with a type prefix, such as `fix: prevent crash when config file is empty` and `build: upgrade pytest dev dependency from 7.4 to 8.2`. Without it, 11 of the 44 replies that could be read did. The grader didn't score that part.
- **The model copied the template.** The body shows `<type>: <summary>`, and every reply followed it to the letter. Suite 2's body shows `<type>(<optional scope>): <summary>`, and its runs had a scope in 14 of 27. The prediction assumed a model writing in the format would add a scope on its own some of the time. Haiku 4.5 didn't: what the template leaves out, it leaves out.
- **No effect is what these numbers support.** With 15 cases, a change of -2 and an interval of -9 to +0, the interval rules out a 10-point change either way, and 15 cases is past the 10 a null needs (D22). A rule miss would need numbers that support another verdict, and these don't.
- One baseline run (commit-9 run 2) hit the 4-turn cap. It scored 0, as every run of that case did, and the card warns.

**What this leaves.** The simulation's +20 point finding is still untested on real runs: M1 was built to have a partial effect and had none on what was graded. A moderate effect is harder to plant than a large one, because Haiku followed this skill's template completely. A next try would need the partial effect to come from the model's own variation, not from a template the model follows or ignores as a whole.

## R3: a skill meant to fire rarely, measured first, with a description between R1's and R2's (`r3-rarely-fires`, skill `project-background`)

Written on 2026-11-07, after the R2 pilot, to try [open question 1](open-questions.md) again the way it says: measure a candidate skill's fire rate first, then freeze the suite and predict. **Not blind:** the design uses R1's and R2's results. The rules are the 0.6.1 rules, 0.5.0's unchanged. Claude Code is 2.1.310.

**The description.** On the same uv project and mostly the same questions, R1's description, "Use when answering how to install, test, lint or format the Python project in this workspace, or which Python version it needs.", fired in 15 of 27 runs, and R2's, "Background on how the tally project in this workspace is set up.", fired in 0 of 45. R1's names the tasks and says when to use the skill; R2's does neither. R3's sits between them: R2's sentence with R1's four task names added, and without R1's "Use when answering how to":

> Background on how the tally project in this workspace is set up, including its install, test, lint and format commands.

**The candidate pool and the pilot.** Everything else is R2's pilot: the skill's name (`project-background`), its body (R1's, correct and the same as the repo, so firing can't change a score), the 15 candidates and the 3 quiet cases. So the pilot differs from R2's in its description and its plugin name, nothing else. 8 candidates ask for a command the description names (tests, lint, format, install, one-file, autofix, first-failure, format-check), and 7 ask about something it doesn't (python, name, line-length, test-dir, runtime-dep, dev-deps, lock-tool), so the pool has a gradient for the selection rule to pick from. The pool runs once as `evals/pilot/r3-candidates`, with the skill arm only (`--ablation none`), 3 runs per case, on `claude-haiku-4-5-20251001`, with a $1.50 cap. It is the fire-rate measurement, nothing more: its scores are not a card.

**The selection rule, fixed before the pilot runs.** R2's rule, with step 3 widened:

1. Count fires per compared case, out of 3 runs.
2. Take the 9 cases with the fewest fires, ties broken by pool order (the order in `R2_POOL`).
3. If those 9 total 0 fires and some other case fired once or twice, swap the one with the fewest fires (ties broken by pool order) in for the last one chosen, so the suite has 1 or 2 expected fires. R2's rule swapped only a case that fired once; a case that fired in 2 of 3 runs still expects about 2 fires in the frozen run, inside the band.
4. The frozen suite is those 9 cases plus the 3 quiet cases, under the name `validation/r3-rarely-fires`, written by `scripts/planted.py` from `R3_CHOSEN`.
5. If the 9 chosen total 3 or more fires, or 0 with no case to swap in, the pool cannot land in the band. The pilot is recorded as the finding and R3 stops without a frozen run.

**Prediction, to be completed from the pilot's counts before the frozen run.** The frozen suite fires in 1 or 2 of the 27 runs that need it, its verdict is Rarely fired, and the quiet cases fire 0 of 9. The exact expected count is the chosen cases' pilot total, and is written in below once known. A known risk, stated now: the rule picks the cases that fired least in the pilot, and a case picked for a low count tends to fire a little more on a second run, so a miss is likelier on the high side than the low.

**What would make it a miss.**

- 0 of 27: Never fired, the rule not exercised.
- 3 or more of 27: the verdict comes from the interval, with D21's warning under half. The rule not exercised.
- Invalid: no reading. Recorded, not counted either way.

**Pass criterion.**

- R3 must fire in 1 or 2 of 27 runs and read Rarely fired. Anything else is a miss, reported with the card, the per-case fire counts and a diagnosis.
- The frozen suite runs once, on `claude-haiku-4-5-20251001` with the same model as judge, 3 runs per side, with a $2 cap, its share of the $6 ceiling the owner set on 2026-11-07. No rerun to get a better answer. If a case file has a real defect, the original result is recorded, the fix goes in a separate commit, and one labeled second attempt is allowed only if it fits under the ceiling.
- A match shows that a fire rate measured for one skill on these questions carries over to a second run of the same skill. It does not show that the 10% threshold is right.

## M2: a moderate effect, with the scope in the template (`m2-moderate`, skill `commit-scopes`)

Written on 2026-11-07, after M1, to try [open question 2](open-questions.md) again with M1's lesson applied. **Not blind:** the design uses the commit-message results from suite 2, V2, V3 and M1. The rules are the 0.6.1 rules, 0.5.0's unchanged. Claude Code is 2.1.310.

**M1's lesson.** Haiku copied M1's `<type>: <summary>` template word for word, so no reply added the scope the grader needed, and the effect was zero. M2's template has the scope slot, `<type>(<scope>): <summary>`, and its body gives the convention only partly: it names a scope for two areas, `deps` for a change to the dependencies and `tests` for a change to the tests, and says to leave the scope and its parentheses out for any other change. The grader still wants a scope on every message. Everything else is M1's: the description ("Use when writing a git commit message."), the 15 compared cases, the grader (any `type(scope): summary` line) and the 3 quiet cases, so the two suites' case files are the same and only the skill differs.

**Why a partial effect, near +27 points.** Without a skill, Haiku almost never writes a scoped prefix: 0 of 27 runs in suite 2, 1 of 27 in V2 and in V3, and 1 of 45 in M1. With suite 2's skill, whose template shows `(<optional scope>)`, it wrote one in 14 of 27 runs; with M1's, which has no slot, in 0 of 45. Of M2's 15 changes, four are to dependencies or tests: commit-5 (bumped requests), commit-6 (added unit tests), bump-pytest and csv-tests. A fifth, ci-workflow (a workflow that runs the tests), is borderline. If Haiku follows the body as written, those four pass and the other 11 fail: 12 of 45 with-skill runs, +27 points against a baseline near zero. That is a skill that changes the outcome of some cases and not others, which is what the simulation's +20 and +40 point rows model. The spread can come from the borderline case, from a scope written where the body says to leave it out (copying the template's slot, as M1's runs copied theirs), or from one left out where the body asks for it.

**Prediction.**

- **Change: between +15 and +40 points,** most likely near +27, with the scoped runs mostly on the four dependency and test cases.
- **Verdict: Helps, the likelier reading, or Inconclusive.** In [simulation.md](simulation.md) at 94% run agreement and 15 cases, a +20 point skill is called Helps in 56% of suites and a +40 point one in 96%. Under the current rules, Helps needs the 90% interval above zero and a change of at least 10 points. Worked on constructed cases with the rules' own bootstrap: four cases at +100 and eleven at 0 give +27, interval +7 to +47, Helps; three give +20, interval +7 to +40, Helps; two full cases and two at one run in three give +18, interval +2 to +33, Helps; two cases alone give +13, interval +0 to +27, Inconclusive. So Helps is the point prediction, and Inconclusive is the other verdict the simulation allows: each is a match on the verdict, and whether the point prediction held is reported on its own line.
- **Fired:** 45 of 45, since the description is M1's, which fired in 45 of 45.
- **Quiet cases:** 0 misfires in 9 runs.

**What would make it a miss.**

- **A change under +15:** Haiku left the scope out even on dependency and test changes, or the baseline rose. A prediction miss about the model, not a rule miss, unless the numbers support a different verdict than the rules gave.
- **A change over +40:** the template's scope slot spread to changes the body says to leave unscoped. A prediction miss; the suite then measured a large effect, not a moderate one.
- **No effect, Hurts, Already handled, Never fired or Rarely fired:** reported with a case-level diagnosis.
- **Invalid:** no reading. Recorded, not counted either way.

**Pass criterion.**

- M2 passes if the change is between +15 and +40 and the verdict is Helps or Inconclusive. Each is scored on its own, as in M1.
- M2 runs once, on `claude-haiku-4-5-20251001` with the same model as judge, 3 runs per side, 18 cases, with a $2.50 cap, its share of the $6 ceiling the owner set on 2026-11-07. No rerun to get a better answer. If a case file has a real defect, the original result is recorded, the fix goes in a separate commit, and one labeled second attempt is allowed only if it fits under the ceiling.
- One run can't check the simulation's rate. What it can check is whether a real partial effect lands where the simulation puts it: inside the band, with one of the two verdicts the rate allows.
