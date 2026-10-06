---
name: pr-description
description: Use when writing or editing the description of a pull request in one of this organization's repositories.
metadata:
  mordecai-version: "2.0.0"
  mordecai-variant: "platform"
  mordecai-based-on: "pr-description@2.0.0"
---

# Pull request descriptions

Write the title in the imperative mood, under 72 characters, with no ticket number.

Write the description in five short sections, in this order:

- **Summary**: one or two sentences on what the change does.
- **Motivation**: the problem it solves, with a link to the ticket.
- **Verification**: how you checked that it works, and what you didn't check.
- **Risk**: what could break, and how to roll it back.
- **Rollout**: the feature flag or deploy step that turns it on, and the dashboard to watch.

If the change adds, removes or changes an alert, name the team that is paged by it.

Keep the whole description under 200 words, and don't paste the diff.
