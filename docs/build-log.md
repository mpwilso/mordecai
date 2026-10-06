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
| 5. README and release prep, fresh-clone check | done (a7b7552) |

## Notes

- 2026-10-06: started. Four research agents (spec and Claude Code docs, client tools, npx skills and APM, skill MCP servers and the author's public repos) read public pages only.
- Step 2: commands work end to end on a scratch library. The hook in this environment allows one git write per shell command, so commits and tags are run one at a time.
- CI now checks out the full history (`fetch-depth: 0`) so tests/test_docs_commits.py can run; it skips on a shallow clone.
- The terminal crashed while the seed-layout fixes were uncommitted (tag scoping per copy path, variant-only libraries). On restart the diff was reviewed, tests passed, and the fixes were committed.
- Step 4 seeding, all with the real `release` and `fork` commands (each a commit plus a local annotated tag, with the Co-Authored-By trailer passed through `--message`): pr-description base 1.0.0, 1.1.0, 1.2.0, 2.0.0; mobile 1.0.0, 1.0.1, 1.1.0 (based on base 1.0.0, so behind); platform 1.0.0, 1.1.0, 2.0.0 (brought up to base 2.0.0); ferry-workflow base 1.0.0 and qrx 1.0.0 (suite 1's skill, byte for byte); branch-naming base 1.0.0 and camelcase 1.0.0 (H1's skill, byte for byte); the team example's pr-description.payments 1.0.0. 15 skill/ tags in all, all local.
- The planted evidence: evals/results/1-convention/result.json and evals/results/h1-must-fire/result.json copied (their local paths were later made relative; see the hardening notes below), and cards made with `mordecai identify --skill <variant's skill folder>` from the repository root. Same verdict, numbers, rules, cases hash and result hash as docs/planted-results/; only the skill hash differs, since it covers the skill folder rather than the plugin.
- docs/library-demo.md was produced by running its commands in a fresh shell and pasting the output (temporary folder written as `$DEMO`). The whole demo runs in about a second.
- Step 5: version 0.3.0 in pyproject.toml and `__init__.py`; no v0.3.0 tag. Final check from a fresh clone in a temporary folder: without the extra, 157 passed and 7 skipped (the library's test files); with `--extra library --group spec`, 277 passed. Lint, format, `brand.py --check` and `planted.py --check` pass both ways. A clone with no tags also passes all 277. The demo was rerun after the version bump and printed the same output as docs/library-demo.md.

## Next

Nothing is half finished. The open questions are in [decisions-for-matt.md](decisions-for-matt.md). Pushing the branch and the `skill/*` tags, and tagging v0.3.0, are left to the author.

## Hardening pass before the first push

- Section 1, paths: the two library result files named absolute local folders. The repository prefix was removed from every path in them (74 each), the cards were remade with `mordecai identify`, and only the result hash changed. Original and new hashes are in each evidence folder's NOTE.md. Lockfiles now record a local source's path as the config wrote it, so the demo's lockfile shows `..` rather than a machine path. The history after fd83056 still holds the old blobs; see the end of this section.
- Section 3: .mcp.json at the root runs `uv run --extra library mordecai mcp --config mordecai-library.toml --project ${MORDECAI_MCP_PROJECT:-.mcp-demo}`. Driven over stdio exactly as written, it lists 7 tools, lists the 4 skills, returns qrx as current Helps, and refuses camelcase without writing anything. Refusals over MCP now say only a person can override them at the command line.
- Section 5, security: five problems reproduced and fixed, each with a test in tests/test_library_security.py (decisions D16, D17). pip-audit 2.10.0, run with `uvx` against `uv export` of the plain set, the library set and every group, found no known vulnerabilities in either the PyPI or the OSV database, so no pin changed. zizmor 1.30.1 (offline) flagged a missing Dependabot cooldown, now 7 days, and then reported nothing; the library CI job has the same `contents: read`, SHA-pinned actions, `persist-credentials: false` and no secrets as the first.
- Section 7, README: restructured to open with the claims and the 3 of 5 blind result, then the card, the verdicts, and the library framed as what the verdicts govern. The library detail moved, unchanged in substance, to docs/library.md (411 lines down to 265). CHANGELOG.md added for 0.1.0 to 0.3.0. A test now checks every relative link and image in the README and the docs; every external link returned 200 when checked. "The brief" is defined where docs use it.
- Section 4: a case-insensitive search of every tracked file, every commit after fd83056 (content and messages) and every tag message found no hits, and every host, email address and commit identity is public. Nothing was rewritten for it.
- Section 6: `status` failed on a tag it couldn't trust, instead of reporting it; fixed. `show` now reads a SKILL.md that isn't UTF-8, `uninstall` lost an unused `--config`, every option has help text, the exit codes are in the help and the README, and tests/test_library_demo.py replays the demo doc. Coverage with the extra went from 92% to 93%; the engine alone, without it, from 98% to 99%.
- History: the rewrite that would remove the old local paths from the commits after fd83056 was refused by this session's permission check, so it wasn't done. The tracked files are clean. [decisions-for-matt.md](decisions-for-matt.md) item 0 says what remains before a push.
