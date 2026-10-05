---
name: undo-commit
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

How do I undo my last git commit but keep the changes staged? Reply with only the command.
