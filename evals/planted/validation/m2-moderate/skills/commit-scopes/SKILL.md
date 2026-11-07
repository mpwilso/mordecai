---
name: commit-scopes
description: Use when writing a git commit message.
---

# Commit messages

Write every commit message as:

    <type>(<scope>): <summary>

- The type is one of feat, fix, docs, style, refactor, perf, test, build, ci or chore.
- The scope names the area that changed. Use `deps` for a change to the dependencies and
  `tests` for a change to the tests. For any other change, leave out the scope and its
  parentheses.
- The summary is in the imperative mood, starts in lowercase, has no trailing period and
  keeps the whole first line under 72 characters.
- If the change needs explaining, add a blank line and a short body that says why.
