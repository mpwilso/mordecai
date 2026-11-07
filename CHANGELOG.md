# Changelog

## Unreleased

- Two more planted runs on Claude Haiku 4.5, each with its prediction committed before it ran, for $3.04 of the $6 the owner approved. **R3**, the third test of Rarely fired, measured its fire rate first with R2's skill and questions and a description that adds four task names: the skill fired in 21 of 24 pilot runs on the named tasks and 0 of 21 on the rest, so the selection rule stopped it before a frozen run. **M2**, a moderate effect planted with the scope slot in the template and two scopes named, read Helps, +62 points (interval +44 to +80): the verdict matched its prediction and the change missed its +15 to +40 band, because the scope spread to changes the skill said to leave unscoped. Neither is a rule miss, so Rarely fired and the simulation's +20 point finding are still untested on real runs. No verdict rule changed. The M2 card is in docs/planted-results; the planted test allows M2's 18 cases.

## 0.6.1 (2026-11-06)

The verdict rules are unchanged. `measure` now needs `--trust-plugin`, so a 0.6.0 `measure` command without it exits 2.

- **Behavior change: `measure` needs `--trust-plugin` (D24, the owner's decision).** It runs `claude plugin eval`, which runs the plugin's code as you, so it now refuses with exit 2, before the eval, unless you pass `--trust-plugin`: the rule `claude plugin eval` itself applies under `--json`. 0.6.0 passed the flag for you. The README and docs/usage.md no longer say Mordecai never runs a plugin in the paragraph that introduces `measure`; they say `measure` does, through `claude plugin eval`, and so needs `--trust-plugin` from you.
- **Fix: on Windows, an `&` in an argument could drop the cost cap (D25).** When `claude` is a `.cmd` or `.bat` file, as npm installs it, its arguments pass through cmd.exe unescaped: `--result C:\x\R&D\result.json` ended the command at the `&`, and claude ran with no `--max-cost-usd`, and `%NAME%` expanded. `measure` now refuses, with exit 2 before the eval, any argument holding a character cmd.exe acts on (`& | < > ^ % ! " ( )` or a line break) when `claude` is such a file. It runs `claude` by its absolute path and puts `--max-cost-usd` and `--model` before every path, so a cut can't drop them.
- Fix: the plugin and the result are passed to `claude plugin eval` as absolute paths. `str(Path("./--x"))` is `--x`, so a plugin folder named like a flag reached claude as a flag.
- Fix: `measure` refused some bad input only after the eval had spent money. A `--card`, `--markdown` or `--result` in a folder that doesn't exist failed after the eval; a mistyped `--skill` ran and wrote a card with no skill hash; and a `--card` or `--markdown` naming the result file overwrote the result the card hashes, which D23 forbids. Each is now refused before the eval, with exit 2 and one line. `identify` also refuses a `--card` or `--markdown` that names its result, or both naming one file.
- Fix: Ctrl+C during `measure`'s eval printed a Python traceback. It now prints "claude plugin eval was interrupted; no card was written." and exits 3.
- The README was rewritten for a reader who doesn't build tools: who it's for and what a Claude skill is, up top; the simulation's plain finding (with 10 cases, a real +20 point gain is called Helps about one time in three) near the top; a plain status line; a gloss under the example card's 90% bound; test skills described instead of named by suite IDs; and two findings that were in the docs alone: Haiku copies a skill's template word for word (M1), and a description's wording alone moved the fire rate from 15 of 27 (R1) to 0 of 45 (R2's pilot). It no longer says both sealed holdouts got their predicted verdict: holdout 6, the informative one, matched, and holdout 7, a placebo on a task no run could pass, couldn't have failed. docs/testing.md and docs/planted-skills-results.md say the same.
- The planted spend table's running totals are now summed from the unrounded costs, as a line under it says, so the total is $25.28, not $25.29; several rows had been a cent off. No recorded cost changed. Run dates in the run records are UTC, from each result's `startedAt`, as docs/planted-skills-results.md now says once; the R2 pilot and M1 dates are marked UTC. D23's status says it was adopted in 0.6.0.
- Two more planted runs on Claude Haiku 4.5, each with its prediction committed before it ran, for $3.18 of the $8 the owner approved. **R2**, the second test of Rarely fired, measured its fire rate first: a correct skill whose description names the project and no task fired in 0 of 45 pilot runs over 15 candidate questions, so the selection rule stopped it before a frozen run. **M1**, a planted moderate effect (the type prefix taught, a scope graded, 15 cases), read No effect, -2 points: the skill fired in 45 of 45 runs and every reply copied its template, which has no scope. Both are misses of their predictions, and neither is a rule miss, so Rarely fired and the simulation's +20 point finding are still untested on real runs. No verdict rule changed. The M1 card is in docs/planted-results; the planted test allows M1's 18 cases.

## 0.6.0 (2026-11-05)

The verdict rules are unchanged; the version is for the new command.

- `mordecai measure <plugin> --model <id> --max-cost-usd <n>`: the eval and the card in one step. It runs the `claude plugin eval` line the README shows (`--trust-plugin`, `--json`, `--no-publish`, the model and the cap), then `identify` on the result with the plugin as the skill, taking `identify`'s `--card`, `--markdown`, `--crawl`, `--plain` and `--fail-on`. The model and the cap are required and never defaulted, since the run spends money; a bad `--fail-on`, a missing plugin folder or an existing result file refuses before the eval starts, with exit 2; an eval that didn't finish (no `claude` on PATH, a non-zero exit, no result written) exits 3, a new code, with no card and no retry. Tests run a fake `claude` on PATH and check the exact arguments; none calls a model. The third item of [docs/open-questions.md](docs/open-questions.md)'s What's next, and [D23](docs/decisions.md).

## 0.5.0 (2026-10-24)

The verdict rules changed, so this is 0.5.0.

- The README was restructured to the same order as the author's other tools and cut to about half its length. The verdict table moved to docs/verdicts.md, the full list of limits to docs/testing.md, the fixture note under the example card to docs/usage.md, and the GitHub Action's inputs and outputs are a table there. tests/test_readme_rules.py holds the README to under 155 shown lines, no dashes, links that resolve, no bare placeholders and no "only", "first" or "best" in prose.
- The package's long description (`readme` in pyproject.toml) is [docs/package.md](docs/package.md), a short page that links to GitHub with absolute URLs, since README.md's relative links and images are for GitHub.
- CI's library job runs the suite once, on Python 3.11, under `coverage`, with the report in the job summary, and is the one job with the full history; the checks job's matrix still covers 3.11, 3.12 and 3.13 for the engine.
- Fixes in the library's Git reader: a source file over the 200 MB budget is refused from its size in `git cat-file`'s header, before its content is read (it was read in full, then refused), and the repository and path checks have the same five-minute limit as every other git call (they had none).
- **Rules change: when every compared case has the same change and every run agrees, the card counts cases (D22).** The bootstrap could only return one number there, so cards showed a "90% interval" such as +100 to +100. Now the card says "9 of 9 cases" with an exact one-sided Clopper-Pearson bound, at the rules' confidence, on the share of cases like these that could differ (23% for 9 cases at 90%), and its JSON has `numbers.agreement` with `interval` null. Verdicts are decided as before. Chosen by the owner after seeing the collapsed cards, so those cards aren't evidence for it.
- **Rules change: No effect and Already handled need at least 10 compared cases (D22).** With fewer, the card is Inconclusive and says why. Helps and Hurts keep the minimum of 5. The threshold is a constant, not a `Rules` field, so existing library cards still pass D20's equal-rules check. Of the recorded cards, 5a-twin (Already handled), 5b-filler and holdout 7 (No effect) move to Inconclusive; no Helps or Hurts card moves. All 15 recorded cards and the library's two were rebuilt; docs/planted-skills-results.md lists every card that moved. In scripts/simulate.py only the 5-case null calls moved, and its non-monotonic placebo row (59%, 27%, 64% under 0.4.0) turned out real, not a bug.
- `identify` also reads skill-creator's `benchmark.json`, told apart by its shape. What it doesn't record (whether the skill fired, quiet cases, cost, turns, refused calls, early stops and limits) shows as not measured on the card. See [docs/usage.md](docs/usage.md#skill-creators-benchmarkjson).
- A composite GitHub Action, [action.yml](action.yml), runs `identify` on a result and posts the card on the pull request, with `fail-on` passed through. CI runs its identify step on every push; posting is untested until it's used on a real pull request.
- A release workflow checks that a published release's tag names the version in pyproject.toml and builds the wheel and sdist ([docs/releasing.md](docs/releasing.md)). Publishing to PyPI was set up in it, never used, and dropped; the package is not on PyPI.
- The README was cut to about a quarter of its old length. How it was tested, the verdict details, command details and prior art moved to docs/testing.md, docs/verdicts.md, docs/usage.md and docs/research.md.
- Removed the brand tooling nothing used: `scripts/frames.py`, the social preview PNG (never uploaded), `brand.py --png` and the `visual` (playwright) dependency group.

## 0.4.0 (2026-10-11)

The verdict rules changed, so this is 0.4.0. Cards built by 0.3.0 keep their verdicts except V1's (see below).

- **Rules change: Rarely fired (D21).** A skill that fired in under 10% of the runs that needed it is Rarely fired, checked right after Never fired, with no interval. Between 10% and 50%, the verdict is decided as before and the card warns that the change mostly reflects runs where the skill wasn't used. Of the recorded cards, only V1 (1 of 27) moves: Inconclusive becomes Rarely fired. The rule was designed after seeing V1. `--fail-on` accepts `rarely-fired`, and the library treats it like Never fired: not refused unless a config adds it.
- R1, the test of Rarely fired, ran once ($1.51) and missed: its skill fired in 15 of 27 runs, not the predicted 1 or 2, so the rule wasn't exercised. The result and card are in docs/planted-skills-results.md.
- **Rules change: a blocked run makes the card Invalid (D19).** This shipped on master after the v0.3.0 tag without a version bump, so the released 0.3.0 doesn't have it, while the cards in docs/planted-results rebuilt on 2026-10-06 say `"mordecai": "0.3.0"` and were made with it. It moved no recorded verdict. The bullet below describes it.
- A card warns when runs had a tool call refused by permissions, with how many on each side. The result JSON has no field for a refusal, so Mordecai reads it from each run's trace (`permission_denials`), when the trace is inside the current directory or `--skill`. When the run had the tool and the refused call aimed inside its own folder or the skill's, the setup decided the run and the card is Invalid (D19); anywhere else it stays a warning. A card says when refusals weren't checked because no trace could be read. See [open question 4](docs/open-questions.md#open-question-4-runs-that-say-nothing-about-the-skill).
- The library accepts only cards whose rules are the engine's own, and an error while rechecking a card makes it broken instead of stopping the command (D20). Before, a card with `resamples` 0 crashed `install`, a huge one hung it, and looser rules could earn an easier verdict.
- Fixes: a result with a grader name that isn't a string, or a number too big for a float, is refused with exit code 2 instead of a traceback. A case prompt names the skill only when it holds the name as a whole word, so a skill called `commit` no longer gets the warning (or a failing `lint`) from a prompt saying "uncommitted". A Skill grader counts as "it must fire" only when its `min` (1 by default) is a whole number of at least 1, and as "it must stay quiet" only when its `max` is the whole number 0: `min: 0` with no max always passes and no longer hides Never fired, and `max: false` or `0.0` no longer reads as 0.
- CI runs on every push, and on a pull request only when it comes from a fork, since a same-repo pull request already has its push run. A newer push cancels an older run on any branch but master. Both jobs use `actions/checkout` 7.0.1.

## 0.3.0 (2026-10-06)

The skill library: skills kept in Git, each with a base and named variants, each version with its own history and, when it has been measured, its card. The verdict engine is unchanged; the library uses it. See [docs/library-design.md](docs/library-design.md).

- `mordecai library`: `validate`, `list`, `show`, `history`, `release`, `fork`, `status`, `install`, `update`, `uninstall` and `export`.
- Versions are semver per base and per variant, with a `CHANGELOG.md` beside each and a local annotated tag per release (`skill/<skill>@X.Y.Z`, `skill/<skill>.<variant>@X.Y.Z`). `release` never pushes.
- Each variant records the base version it is based on, and `status` reports a variant behind its base. Nothing is merged.
- Sources (GitHub repositories or local folders, with an optional ref) are listed in `mordecai-library.toml`; for each copy, the source listed last wins.
- `install` copies a resolved skill folder byte for byte into `.agents/skills`, `.claude/skills`, `.github/skills`, `.cursor/skills` or a folder in the project, and records its source, commit, version, hash and verdict in `mordecai-lock.json`. It refuses a version whose card, rechecked against its result and that version's files, says Hurts or Invalid, or whose card doesn't match its result. No config can drop those refusals; only `--allow` at the command line overrides one. `update` shows a diff and changes nothing without `--yes`.
- `export --marketplace` writes a Claude Code plugin marketplace for managed settings, and `export --skills` writes plain skill folders. Exports always leave out Hurts, Invalid and broken copies.
- `mordecai mcp`: a stdio MCP server with `list_skills`, `search_skills`, `get_skill`, `skill_history`, `check_updates`, `install_skill` and `uninstall_skill`. It can't override the install policy, and writes only inside configured targets.
- A seeded library, examples of a three-source config and managed settings, and [docs/library-demo.md](docs/library-demo.md), a walk-through with no model calls.
- The library and its MCP server need the optional extra: `uv sync --extra library`. `identify`, `check` and `lint` still need only the standard library.

## 0.2.0 (2026-10-06)

- **Rules change:** Already handled must also rule out a 10-point loss. Under 0.1.0, an outdated skill that gave wrong answers whenever it fired (planted suite 3) was called Already handled; it is now Inconclusive. Of the seven cards recorded before the change, only suite 3's moves.
- `mordecai lint` runs the case-quality warnings on a plugin's cases before an eval.
- `mordecai check --model` reports a card measured on another model as stale.
- Cards store paths relative to where they are written, so they still check after a clone.
- Results, cards and paths from someone else are checked before use: malformed results are refused, paths stay inside the expected root, links aren't followed, and text from a result is escaped for terminals and Markdown.
- `--plain` overrides `MORDECAI_MODE=crawl`, and every command documents its exit codes.
- The planted skills check: 12 suites with predictions committed before they ran, and real eval runs on Claude Haiku 4.5 and Claude Sonnet 5.5. Results are in [docs/planted-skills-results.md](docs/planted-skills-results.md).
- CI on Python 3.11 to 3.13, with actions pinned to commit SHAs.

## 0.1.0 (2026-10-05)

- `mordecai identify` reads a `claude plugin eval` result and writes a card: a verdict (Helps, Hurts, Already handled, No effect, Inconclusive, Never fired or Invalid), decided by fixed rules in code, with the numbers behind it and hashes of the skill, cases and result it was measured on.
- `mordecai check` reports a card whose skill or cases changed since it was written.
- `--card` and `--markdown` write the card as JSON and Markdown, and `--fail-on` sets the exit code for CI.
- Crawl mode, an optional rendering of the same card as loot.
