---
name: pr-description
description: Use when writing or editing the description of a pull request in one of this organization's repositories.
metadata:
  mordecai-version: "1.0.0"
  mordecai-variant: "platform"
  mordecai-based-on: "pr-description@1.1.0"
---

# Pull request descriptions

Write the description in five short sections, in this order:

- **What**: one or two sentences on what the change does.
- **Why**: the problem it solves, with a link to the ticket.
- **Testing**: how you checked that it works.
- **Risk**: what could break, and how to roll it back.
- **Rollout**: the feature flag or deploy step that turns it on, and the dashboard to watch.

Keep the whole description under 200 words, and don't paste the diff.
