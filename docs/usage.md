# Using Mordecai

The README has setup and the four commands. This page has the rest: what each command exits with, how paths are read, and a worked `check` example.

## Trust

**`claude plugin eval` runs the plugin's code on your machine, as you.** Under `--json` it can't ask whether you trust the plugin directory, so it refuses to run unless you pass `--trust-plugin` or have already trusted the directory. Only pass it for a plugin you've reviewed and would run yourself. Mordecai itself never runs a plugin: it reads the result file and hashes the plugin's files.

## Commands and exit codes

- `lint` exits 1 if the case files would get any warning.
- `identify` prints the card, and can write it as JSON and as Markdown for a pull request. `--fail-on hurts,invalid` makes it exit 1 on those verdicts, for CI. `--crawl` or `MORDECAI_MODE=crawl` prints crawl mode, and `--plain` overrides the variable.
- `check` exits 1 when the skill or its cases have changed since the card was written. With `--model`, it also exits 1 when the card was measured on a different model.
- Every command exits 2 when it can't read its input or won't use it, with one line saying why.

## Paths

Cards store paths relative to where the card is written, so a card still checks after the repository is cloned somewhere else. Run Mordecai from the repository root: it reads only inside the current directory and directories you pass with `--skill` or `--cases-root`, since a result or card may come from someone else. For the same reason a symbolic link in a skill is hashed as the path it points to, never opened, so a card doesn't go stale when the linked file's contents change, and a skill under review can't make Mordecai read files outside it.

## A worked example

From the planted check: suite 2's Haiku card still matches its files, but it is stale for Sonnet.

```
$ uv run mordecai check docs/planted-results/2-commits.card.json --model claude-sonnet-5-5
Stale: docs/planted-results/2-commits.card.json
  - The card was measured on claude-haiku-4-5-20251001, not claude-sonnet-5-5.
```

## skill-creator's benchmark.json

`mordecai identify benchmark.json` reads the file that the benchmark mode of Anthropic's [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) skill writes, as its `references/schemas.md` describes it. Mordecai tells it from a `claude plugin eval` result by its shape (a `metadata` object and a `runs` list, no `schemaVersion`), so there is no flag. The mapping:

| benchmark.json | Card |
|---|---|
| `runs[].eval_id`, `eval_name` | One case per eval, named by `eval_name`, or `eval N` when it's missing |
| `runs[].configuration` `with_skill` / `without_skill` | The two arms. Any other configuration, such as `old_skill` and `new_skill`, is refused: that isn't a comparison with and without the skill |
| `runs[].result.pass_rate` | The run's score, 0 to 1 |
| `metadata.skill_name`, `skill_path` | The subject, and the folder hashed for the skill hash (or pass `--skill`) |
| `metadata.executor_model`, `timestamp` | Tested on, and the date |
| `run_summary`, `notes`, `expectations`, `time_seconds`, `tokens`, `tool_calls` | Not read. The card recomputes everything from the runs |
| `result.errors` | Not read: it counts errors a run worked through, not a run that failed |

What it doesn't record, the card shows as not measured, never guessed: whether the skill fired (so Never fired and Rarely fired can't be called), cases where the skill should stay quiet, cost and turns, refused tool calls, the judge model, Claude Code's version, and whether a run stopped early or hit a rate limit (so a limited run can't make the card Invalid). It names no case files, so the card has no cases hash and `mordecai check` reports it can't check the cases. The same verdict rules apply.

The test fixture, [tests/fixtures/benchmark/](../tests/fixtures/benchmark/), was written by hand from the documented schema, not taken from a real run.
