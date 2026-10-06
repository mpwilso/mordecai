# Build log: the skill library

The library build (0.3.0) runs unattended from a written brief. This file says what is done, what is next and what is half finished, so the work can resume after a restart. Read CLAUDE.md, this file and [decisions.md](decisions.md) before doing anything else.

There is no task-list tool in this session, so the steps are tracked here instead.

## Steps

| Step | State |
|---|---|
| 0. Research: docs/research.md | done |
| 1. Design: docs/library-design.md, committed before library code | done (5093d21) |
| 2. Library commands | done (8a982fb): 258 tests with the extra |
| 3. MCP server | done (df71ad6) |
| 4. Seed library and demo | in progress |
| 5. README and release prep, fresh-clone check | not started |

## Notes

- 2026-10-06: started. Four research agents (spec and Claude Code docs, client tools, npx skills and APM, skill MCP servers and the author's public repos) read public pages only.
- Step 2: commands work end to end on a scratch library. The hook in this environment allows one git write per shell command, so commits and tags are run one at a time.
- CI now checks out the full history (`fetch-depth: 0`) so tests/test_docs_commits.py can run; it skips on a shallow clone.
- The terminal crashed while the seed-layout fixes were uncommitted (tag scoping per copy path, variant-only libraries). On restart the diff was reviewed, tests passed, and the fixes were committed.
