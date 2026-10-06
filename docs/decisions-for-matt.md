# Decisions for Matt

Questions from the library build that need the author's judgment. Each has a recommendation and what it would cost, and the build went ahead with the recommended default where that was reversible. The reversible choices made without asking are in [decisions.md](decisions.md).

## 1. Add Loupe's public skill as a real library entry?

- **Recommendation:** not yet. Measure it first, then add it with its card.
- **Why:** added now, it would sit in the seeded library as unmeasured, beside two planted skills with real cards. A library that gates on evidence should show a real skill earning its card, not an author's other project listed without one. It would also be a copy that has to be kept in step with Loupe's repository by hand.
- **Cost of measuring:** a planted-style suite for Loupe's skill (12 cases, 3 runs per side) and one live `claude plugin eval` run. The planted suites cost about $1.40 each on Haiku 4.5, so roughly that, and it needs your go-ahead under rule 3. Then one `release` and an `identify` to add the card.
- **Cost of adding it unmeasured now:** about ten minutes; read only Loupe's public GitHub page, copy its skill folder into `library/loupe/base/`, and release 1.0.0.

## 2. Push the library's release tags

- **Recommendation:** push them with the branch: `git push origin 'refs/tags/skill/*'`.
- **Why:** the 15 `skill/...` tags are local. Without them, a clone or a GitHub source reads every copy as untagged at the commit, and `history` shows no tags. The demo's output assumes they exist. CI passes either way (a test run on a clone with no tags passed).
- **Cost:** 15 more tags in the tag list. None matches `v*`.

## 3. The raw eval results are committed as they were

- **Recommendation:** keep them unchanged.
- **Why:** `library/ferry-workflow/variants/qrx/evidence/1.0.0/result.json` and `library/branch-naming/variants/camelcase/evidence/1.0.0/result.json` are byte for byte `evals/results/1-convention/result.json` and `evals/results/h1-must-fire/result.json`. That makes their hashes equal the recorded cards' result hashes, which ties the library cards to the recorded runs.
- **Cost:** they hold local paths (`/work/...`, and `/tmp/claude-eval-*` trace paths). The alternative is to replace the paths, as the test fixtures do; the hash tie to the recorded cards would then be lost, and the cards would need remaking with `identify`.

## 4. Version stamps are optional, not required

- **Recommendation:** keep them optional (decision D4).
- **Why:** the brief put versions and lineage in `metadata` as `mordecai-*` keys. A card hashes the skill folder's bytes, so required stamps would mean the planted variants couldn't keep their cards, and every release would change the bytes. The changelog holds versions and lineage instead, and stamps, where a copy has them, are checked against it.
- **Cost of requiring them:** re-measure the two planted variants after stamping, about $3 in live runs.

## 5. The tag names have a `skill/` prefix

- **Recommendation:** keep it (decision D3).
- **Why:** without it, a skill whose name starts with `v` would match `v*` release triggers.
- **Cost of dropping it:** rename the 15 tags, change one constant.

## 6. This repository now publishes skills at its root

- **Recommendation:** keep `skills/` and `mordecai-library.toml` (decision D8).
- **Why:** `npx skills add mpwilso/mordecai` used to fall back to a recursive search and find the planted suites. With the library, it would find several same-named copies and pick one arbitrarily. `skills/` gives it one copy per name: the org bases, and `ferry-workflow`'s measured Helps variant.
- **Cost:** someone who runs `npx skills add mpwilso/mordecai` now gets three made-up example skills. If you'd rather it found nothing, the alternative is an empty-looking repository for npx skills, which isn't possible without moving the library and the planted suites out of its reach.

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
