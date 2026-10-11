# Changelog

## Unreleased

The verdict rules changed, so the version is 0.5.0. Not yet tagged or released.

- **Rules change: when every compared case has the same change and every run agrees, the card counts cases (D22).** The bootstrap could only return one number there, so cards showed a "90% interval" such as +100 to +100. Now the card says "9 of 9 cases" with an exact one-sided Clopper-Pearson bound, at the rules' confidence, on the share of cases like these that could differ (23% for 9 cases at 90%), and its JSON has `numbers.agreement` with `interval` null. Verdicts are decided as before. Chosen by the owner after seeing the collapsed cards, so those cards aren't evidence for it.
- **Rules change: No effect and Already handled need at least 10 compared cases (D22).** With fewer, the card is Inconclusive and says why. Helps and Hurts keep the minimum of 5. The threshold is a constant, not a `Rules` field, so existing library cards still pass D20's equal-rules check. Of the recorded cards, 5a-twin (Already handled), 5b-filler and holdout 7 (No effect) move to Inconclusive; no Helps or Hurts card moves. All 15 recorded cards and the library's two were rebuilt; docs/planted-skills-results.md lists every card that moved. In scripts/simulate.py only the 5-case null calls moved, and its non-monotonic placebo row (59%, 27%, 64% under 0.4.0) turned out real, not a bug.
- `identify` also reads skill-creator's `benchmark.json`, told apart by its shape. What it doesn't record (whether the skill fired, quiet cases, cost, turns, refused calls, early stops and limits) shows as not measured on the card. See [docs/usage.md](docs/usage.md#skill-creators-benchmarkjson).
- A composite GitHub Action, [action.yml](action.yml), runs `identify` on a result and posts the card on the pull request, with `fail-on` passed through. CI runs its identify step on every push; posting is untested until it's used on a real pull request.
- A release workflow publishes `mordecai-skills` to PyPI with trusted publishing when a GitHub release is published. It hasn't run; [docs/releasing.md](docs/releasing.md) has the one-time setup.
- The README is about a quarter of its old length. How it was tested, the verdict details, command details and prior art moved to docs/testing.md, docs/verdicts.md, docs/usage.md and docs/research.md.
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
