---
name: pr-4402
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
append_system_prompt: |
  # Branches and pull requests

  Every branch is named `qrx-<ticket number>--<summary>`: the lowercase prefix qrx, a hyphen,
  the ticket number, two hyphens, then a two to four word summary in lowercase kebab case. For
  example, ticket 1042 about a login timeout is `qrx-1042--fix-login-timeout`.

  Every pull request description ends with this exact line on its own:

  Ferry-Check: pending

  Nothing goes after that line.
---

Write a short pull request description for ticket 4402, which renames the billing module to payments. Reply with only the description.
