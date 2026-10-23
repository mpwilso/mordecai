# mordecai-skills

Mordecai reads a skill's `claude plugin eval` results and says what the skill can honestly claim: it helps, it hurts, the model already handles it, or there isn't enough to tell. Code decides the verdict, never a model. The card is tied by hash to the skill, cases and model it was measured on, so a team can see when a claim goes stale.

This page is the package's description on PyPI. The README, with an example card, the verdict rules, the skill library and the known limits, is at https://github.com/mpwilso/mordecai.

## Setup

Requires Python 3.11 or later.

```
pip install mordecai-skills
```

`identify`, `check` and `lint` use the standard library alone. The skill library and its MCP server need the extra: `pip install "mordecai-skills[library]"`.

Check your cases, run the eval with a pinned model, then read it:

```
mordecai lint path/to/plugin
claude plugin eval path/to/plugin --trust-plugin --model claude-sonnet-5-5 --json result.json --no-publish --max-cost-usd 5
mordecai identify result.json --skill path/to/plugin --card card.json --markdown card.md
mordecai check card.json --model claude-sonnet-5-5
```

**`claude plugin eval` runs the plugin's code on your machine, as you,** so pass `--trust-plugin` for a plugin you've reviewed. Mordecai never runs a plugin; it reads the result and hashes files. `--fail-on hurts,invalid` makes `identify` exit 1 for CI.

## More

- [Usage: flags, exit codes, paths and a worked `check` example](https://github.com/mpwilso/mordecai/blob/master/docs/usage.md)
- [The verdicts in detail](https://github.com/mpwilso/mordecai/blob/master/docs/verdicts.md)
- [How it was tested](https://github.com/mpwilso/mordecai/blob/master/docs/testing.md)
- [The skill library](https://github.com/mpwilso/mordecai/blob/master/docs/library.md)
- [Changelog](https://github.com/mpwilso/mordecai/blob/master/CHANGELOG.md)
- [Security policy](https://github.com/mpwilso/mordecai/blob/master/SECURITY.md)

MIT license.
