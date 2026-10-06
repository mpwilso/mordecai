---
name: mordecai
description: Use when the user asks whether a skill measurably helps, wants a Mordecai card read or checked, or wants to list or install skills from a Mordecai skill library.
---

# Mordecai

Mordecai is a command-line tool from https://github.com/mpwilso/mordecai. It runs from a clone of
that repository with uv: `uv run --project <clone> mordecai ...`. If you don't know where the
clone is, ask the user.

- Read an eval result: `mordecai identify result.json --skill <plugin folder>`. Give the user the
  verdict line and the Next line as printed. Don't restate the numbers in your own words.
- Check a card: `mordecai check card.json`. Stale means the skill or its cases changed since it
  was measured.
- Check eval cases before a run: `mordecai lint <plugin folder>`.
- See a library: `mordecai library list`, or `mordecai library show <skill> --variant <name>`.
- Install a skill: `mordecai library install <skill> --target claude`. If it prints Refused, tell
  the user why and stop. Pass `--allow` only if the user asks for it by name.

Never run `claude plugin eval` unless the user asks: it calls a model and costs money.
