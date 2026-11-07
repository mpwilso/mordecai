# Using Mordecai

The README has setup and the three commands a visitor needs. This page has the rest: what each command exits with, how paths are read, a worked `check` example, why the README's example card differs from the recorded one, skill-creator's benchmark.json and the GitHub Action.

## Trust

**`claude plugin eval` runs the plugin's code on your machine, as you.** Under `--json` it can't ask whether you trust the plugin directory, so it refuses to run unless you pass `--trust-plugin` or have already trusted the directory. Only pass it for a plugin you've reviewed and would run yourself. `identify`, `check` and `lint` never run a plugin: they read the result file and hash the plugin's files. `measure` runs `claude plugin eval`, which runs the plugin's code as you, so it needs `--trust-plugin` from you: without it, `measure` refuses with exit 2 before the eval, even for a directory you trusted before.

## Commands and exit codes

- `lint` exits 1 if the case files would get any warning.
- `identify` prints the card, and can write it as JSON and as Markdown for a pull request. `--fail-on hurts,invalid` makes it exit 1 on those verdicts, for CI. `--crawl` or `MORDECAI_MODE=crawl` prints crawl mode, and `--plain` overrides the variable. A `--card` or `--markdown` that names the result file, or both naming one file, is refused with exit 2, so the card never replaces the result it hashes.
- `measure <plugin> --model <id> --max-cost-usd <n> --trust-plugin` runs `claude plugin eval --max-cost-usd <n> --model <id> --trust-plugin --no-publish --json <result> <plugin>`, the flags of the line the README shows, then runs `identify` on the result with the plugin as the skill. The cap and the model come before every path, so nothing a path holds can cut them off; the plugin and the result are passed as absolute paths, so a folder named like a flag stays a path, and `claude` is run by its absolute path. The model, the cap and `--trust-plugin` are required and never defaulted, since the run spends money and runs the plugin's code as you (see Trust above). `--result` names the result file (`result.json` by default, and an existing file is never overwritten), `--skill` names the skill folder when it isn't the plugin folder, and `--card`, `--markdown`, `--crawl`, `--plain` and `--fail-on` are `identify`'s.
  - Everything that can refuse does so before the eval starts, with exit 2 and one line: a missing model, cap or `--trust-plugin`, a bad `--fail-on`, a plugin or `--skill` folder that doesn't exist, a result file that already exists, a `--result`, `--card` or `--markdown` in a folder that doesn't exist, and a `--card` or `--markdown` that names the result file.
  - On Windows, when `claude` is a `.cmd` or `.bat` file (npm installs `claude.cmd`), its arguments pass through cmd.exe, which Python doesn't escape for. So `measure` also refuses, with exit 2, any argument holding `&`, `|`, `<`, `>`, `^`, `%`, `!`, `"`, `(`, `)` or a line break: cmd.exe would end the command at an `&` and expand `%NAME%`, and in 0.6.0 a `--result` under a folder named `R&D` reached claude without the cap. Use paths and a model name without them ([D25](decisions.md#d25-on-windows-measure-refuses-an-argument-cmdexe-would-rewrite)).
  - It exits 3 when the eval didn't finish: `claude` isn't on PATH, exited non-zero, wrote no result, or was stopped with Ctrl+C. The last three print one line ending "no card was written". It never retries.
- `check` exits 1 when the skill or its cases have changed since the card was written. With `--model`, it also exits 1 when the card was measured on a different model.
- Every command exits 2 when it can't read its input or won't use it, with one line saying why. `measure` is the one command that exits 3, when the eval it ran gave it nothing to read.

## Paths

Cards store paths relative to where the card is written, so a card still checks after the repository is cloned somewhere else. Run Mordecai from the repository root: it reads only inside the current directory and directories you pass with `--skill` or `--cases-root`, since a result or card may come from someone else. For the same reason a symbolic link in a skill is hashed as the path it points to, never opened, so a card doesn't go stale when the linked file's contents change, and a skill under review can't make Mordecai read files outside it.

## A worked example

From the planted check: suite 2's Haiku card still matches its files, but it is stale for Sonnet.

```
$ uv run mordecai check docs/planted-results/2-commits.card.json --model claude-sonnet-5-5
Stale: docs/planted-results/2-commits.card.json
  - The card was measured on claude-haiku-4-5-20251001, not claude-sonnet-5-5.
```

## The README example card

The README's card is printed from [tests/fixtures/suite1-result.json](../tests/fixtures/suite1-result.json), planted suite 1's raw result with local paths replaced, so its result hash differs from the recorded card's (`sha256:06cf8a473864` in [docs/planted-results/1-convention.card.json](planted-results/1-convention.card.json)) and its traces aren't beside it, hence the warning about refused tool calls. Everything else matches. tests/test_readme.py checks that the README shows exactly what the command prints.

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

## GitHub Action

[action.yml](../action.yml) at the repository root is a composite action: it runs `mordecai identify` on a result file in your workspace, writes the card as Markdown, posts it on the pull request with `gh pr comment`, and then fails the step if the verdict is in `fail-on`. Pin it to a commit SHA, as you would any action:

```yaml
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  card:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: mpwilso/mordecai@<commit SHA>
        with:
          result: evals/result.json
          skill: path/to/plugin
          fail-on: hurts,invalid
```

The result file has to be committed or made earlier in the job: the action never runs `claude plugin eval`. Its inputs and outputs, from action.yml:

| Input | Required | Default | What it is |
|---|---|---|---|
| `result` | yes | | The `claude plugin eval --json` result, or a skill-creator benchmark.json, relative to the workspace |
| `skill` | no | empty | The plugin or skill folder, if the result's path doesn't lead to it |
| `fail-on` | no | empty | Comma-separated verdicts that fail the step, such as `hurts,invalid`; passed to `--fail-on` |
| `comment` | no | `"true"` | Post the card as a pull request comment; `"false"` writes the card and posts nothing. Needs `pull-requests: write` |
| `github-token` | no | `github.token` | The token `gh` uses to comment |

| Output | What it is |
|---|---|
| `card` | The path of the card as Markdown |
| `verdict-exit-code` | `identify`'s exit code, 0 or 1 (1 when the verdict is in `fail-on`) |

**The posting step is untested.** This repository's CI runs the action on a recorded result on every push, with `comment: "false"`, and checks the card and the `fail-on` failure. It can't test posting: a push has no pull request, and a pull request from this repository doesn't run CI (only one from a fork does, with a read-only token that can't comment). A pull request from a fork gets that read-only token in your repository too, so the comment step fails there unless you set `comment: "false"`.
