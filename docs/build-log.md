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
| 4. Seed library and demo | done: library/, examples/, skills/, docs/library-demo.md |
| 5. README and release prep, fresh-clone check | in progress |

## Notes

- 2026-10-06: started. Four research agents (spec and Claude Code docs, client tools, npx skills and APM, skill MCP servers and the author's public repos) read public pages only.
- Step 2: commands work end to end on a scratch library. The hook in this environment allows one git write per shell command, so commits and tags are run one at a time.
- CI now checks out the full history (`fetch-depth: 0`) so tests/test_docs_commits.py can run; it skips on a shallow clone.
- The terminal crashed while the seed-layout fixes were uncommitted (tag scoping per copy path, variant-only libraries). On restart the diff was reviewed, tests passed, and the fixes were committed.
- Step 4 seeding, all with the real `release` and `fork` commands (each a commit plus a local annotated tag, with the Co-Authored-By trailer passed through `--message`): pr-description base 1.0.0, 1.1.0, 1.2.0, 2.0.0; mobile 1.0.0, 1.0.1, 1.1.0 (based on base 1.0.0, so behind); platform 1.0.0, 1.1.0, 2.0.0 (brought up to base 2.0.0); ferry-workflow base 1.0.0 and qrx 1.0.0 (suite 1's skill, byte for byte); branch-naming base 1.0.0 and camelcase 1.0.0 (H1's skill, byte for byte); the team example's pr-description.payments 1.0.0. 13 skill/ tags in all, all local.
- The planted evidence: evals/results/1-convention/result.json and evals/results/h1-must-fire/result.json copied unchanged (their hashes equal the recorded cards'), and cards made with `mordecai identify --skill <variant's skill folder>` from the repository root. Same verdict, numbers, rules, cases hash and result hash as docs/planted-results/; only the skill hash differs, since it covers the skill folder rather than the plugin.
- docs/library-demo.md was produced by running its commands in a fresh shell and pasting the output (temporary folder written as `$DEMO`). The whole demo runs in about a second.
