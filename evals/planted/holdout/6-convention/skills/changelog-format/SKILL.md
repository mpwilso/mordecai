---
name: changelog-format
description: Use when writing a changelog entry or a line for the change log of this team's services.
---

# Changelog entries

Every changelog entry is exactly one line:

    ZK-<ticket> | <area> | <summary>

- The area is one of api, web, data or ops.
- The summary is in the past tense and starts in lowercase.

For example, ticket 318, a fix for the CSV export timing out in the web app, is
`ZK-318 | web | fixed the CSV export timing out`.
