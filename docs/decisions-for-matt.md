# Decisions for Matt

Questions from the library build that need the author's judgment. Each has a recommendation and what it would cost, and the build went ahead with the recommended default where that was reversible. The reversible choices made without asking are in [decisions.md](decisions.md).

## 0. Before pushing: the old local paths are still in unpushed history

- **Needs your decision; this blocks the push.** Every tracked file is clean (a test checks), but ten commits after fd83056, from fe4247a to 5e37b93, still hold the two result files with absolute local paths, and three of them also hold docs that quoted the path. Pushing those commits as they are would publish the paths. The hardening pass tried to rewrite those commits and the session's permission check refused it, so nothing was rewritten.
- **Recommendation:** rewrite only the commits after fd83056, so each holds the result files with the repository prefix removed, each card's result hash updated to match, and the doc quotes replaced with a placeholder; then move the 16 `skill/` tags to the rewritten commits and fix the three commit messages that call the results unchanged. The current files are the target state for every one of those blobs. fd83056 and everything before it stay as they are.
- **Cost:** every commit hash after fd83056 changes, including those cited in docs/build-log.md; they would need updating. No hash the README or the other docs cite changes, since all of those are at or before fd83056. The alternative, squashing everything after fd83056 into one commit, loses the release history the tags record.

## 1. Add Loupe's public skill as a real library entry?

- **Recommendation:** not yet. Measure it first, then add it with its card.
- **Why:** added now, it would sit in the seeded library as unmeasured, beside two planted skills with real cards. A library that gates on evidence should show a real skill earning its card, not an author's other project listed without one. It would also be a copy that has to be kept in step with Loupe's repository by hand.
- **Cost of measuring:** a planted-style suite for Loupe's skill (12 cases, 3 runs per side) and one live `claude plugin eval` run. The planted suites cost about $1.40 each on Haiku 4.5, so roughly that, and it needs your go-ahead under rule 3. Then one `release` and an `identify` to add the card.
- **Cost of adding it unmeasured now:** about ten minutes; read only Loupe's public GitHub page, copy its skill folder into `library/loupe/base/`, and release 1.0.0.

## 2. Push the library's release tags

- **Recommendation:** push them with the branch: `git push origin 'refs/tags/skill/*'`.
- **Why:** the 16 `skill/...` tags are local. Without them, a clone or a GitHub source reads every copy as untagged at the commit, and `history` shows no tags. The demo's output assumes they exist. CI passes either way (a test run on a clone with no tags passed).
- **Cost:** 16 more tags in the tag list. None matches `v*`.

## 3. The library's result files had their local paths made relative

- **Done, no decision needed.** The two committed results named absolute local folders. Their paths are now relative to the repository root, and their cards were remade with `mordecai identify`. Verdict, counts, cases hash and skill hash are unchanged; only the result hash differs. Each evidence folder's NOTE.md gives the original hash, which is the one in the recorded card under docs/planted-results/.

## 4. Version stamps are optional, not required

- **Recommendation:** keep them optional (decision D4).
- **Why:** the brief put versions and lineage in `metadata` as `mordecai-*` keys. A card hashes the skill folder's bytes, so required stamps would mean the planted variants couldn't keep their cards, and every release would change the bytes. The changelog holds versions and lineage instead, and stamps, where a copy has them, are checked against it.
- **Cost of requiring them:** re-measure the two planted variants after stamping, about $3 in live runs.

## 5. The tag names have a `skill/` prefix

- **Recommendation:** keep it (decision D3).
- **Why:** without it, a skill whose name starts with `v` would match `v*` release triggers.
- **Cost of dropping it:** rename the 16 tags, change one constant.

## 6. What this repository publishes at its root

- **Done; reverse it if you disagree.** `skills/` now holds only one skill, `mordecai`, which tells an agent how to run Mordecai's commands. The seeded library's skills are demo content and are no longer published (decision D15).
- **Why not publish nothing:** with no skill in a standard folder, `npx skills add mpwilso/mordecai` searches the whole repository. That reaches the planted suites, including deliberately harmful ones (H1, V2, the outdated-rule suites), and the library's refused variant, and with several copies of a name it installs whichever it lists first. One harmless published skill stops that search.
- **What's left:** `npx skills add --full-depth` still searches everything; the README says not to use it here. Closing that fully would mean marking the planted skills `metadata.internal`, which changes the bytes their cards measured, or moving the suites, which changes paths the docs cite.
- **Cost of publishing nothing instead:** the risk above. Cost of the current choice: one more skill to keep accurate, unmeasured.

## 7. `release` commits in the library's repository

- **Recommendation:** keep it.
- **Why:** a tag has to point at a commit that holds the updated changelog. `release` commits only the copy's folder and refuses when anything else is uncommitted, like `npm version`.
- **Cost of the alternative** (the author commits, `release` only tags): one more manual step per release, and a chance of tagging a commit whose changelog doesn't match, which install would then refuse.

## 8. A broken card refuses the install

- **Recommendation:** keep it (decision D7).
- **Why:** the brief's default was Hurts and Invalid. A card that doesn't match its own result looks like an edited card, and treating it as unmeasured would let an edited Hurts card through with a warning.

## 9. Try the client snippets

- **Recommendation:** run each README snippet once in its client before calling them verified.
- **Why:** they follow each tool's docs, but none was run. The open questions are which folder each client starts a stdio server in (the snippets pass `--project` where it matters) and whether each passes `MORDECAI_GITHUB_TOKEN` through.
- **Cost:** about ten minutes per client, and no model calls beyond the client's own.

## 10. The MCP SDK is the new 2.x line

- **Recommendation:** keep `mcp==2.3.0`.
- **Why:** it is current, and its in-process `Client` is what the tests use. 1.x is still maintained (1.30.0), with a different API (`FastMCP`).
- **Cost of 1.x:** rewrite `server.py`'s imports and the test client, about an hour.

## 11. A project's own config can loosen the install policy

- **Recommendation:** make the default refusals (Hurts, Invalid, broken) impossible to drop from any config, as exports already are, so only `--allow` at the command line overrides them.
- **Why:** `mordecai library` and the MCP server read `mordecai-library.toml` from the project they run in. A cloned project could ship one with `refuse = []`, and installs in that project would then take a Hurts copy with only the card's verdict shown.
- **Cost:** a small change in `sources.parse_config`, and `[policy] refuse` becomes add-only. Not done here because it changes documented behavior.

## 12. Fetches have a time limit but no size limit

- **Recommendation:** accept it for now, and note it as a limit.
- **Why:** each Git call stops after five minutes, and materializing a source is capped at 200 MB, but the fetch itself can download a large repository into the cache before that. Checking size first would need the GitHub API.
- **Cost of fixing:** a size check through the API before the first fetch, and a token for private repositories.

## 13. This file is addressed to you

- **Recommendation:** delete it, or move what's left into issues, once you've decided these. A public reader of the repository would find a file named for the author.
