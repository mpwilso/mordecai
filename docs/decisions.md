# Decisions

Reversible decisions made during the library build, each with the options considered, the reason, and how to reverse it. The library was built from a short written specification, called the brief here; where a decision departs from it, the entry says so. Trade-offs still open are in [open-questions.md](open-questions.md).

## D1. The library's dependencies are an extra, not a dependency group

- **Decision:** the MCP SDK and PyYAML go in `[project.optional-dependencies] library`. `uv sync` installs neither; `uv sync --extra library` installs both. Someone installing the package can ask for `mordecai-skills[library]`.
- **Options:** a `[dependency-groups]` group (like `dev` and `visual`), or an extra.
- **Why:** dependency groups are for working on the repository and are never published with the package, so a user installing from an index couldn't get the MCP server at all. An extra is the published form of an optional dependency set.
- **Reverse:** move the two pins into a dependency group and change `--extra library` to `--group library` in CI and the docs.

## D2. `library` and `mcp` are dispatched before the engine's parser

- **Decision:** `mordecai.cli.main` hands `library ...` and `mcp ...` to `mordecai.library.cli` with a lazy import, before it builds its own parser. Both commands are also listed in `mordecai --help`.
- **Options:** a second entry point (`mordecai-library`), or registering every library flag in the engine's parser.
- **Why:** the brief asks for `mordecai library` and `mordecai mcp`. A lazy import keeps the engine modules (`verdict`, `card`, `result`, `provenance`, `lint`, `render`) free of any import of the library, and keeps `identify`, `check` and `lint` parsing exactly as before. The only visible change to the engine's command line is that the top-level help and the "invalid choice" message list two more commands.
- **Reverse:** remove the two `if` lines and the two help-only subparsers in `cli.py`.

## D3. Library tags are `skill/<skill>@X.Y.Z` and `skill/<skill>.<variant>@X.Y.Z`

- **Decision:** a fixed `skill/` prefix before the brief's proposed names.
- **Options:** the brief's `<skill>@X.Y.Z` with no prefix; a different separator such as `<skill>--<variant>-X.Y.Z`; a prefix.
- **Why:** the unprefixed names are valid refs and can't equal a `vX.Y.Z` tag, but a skill named `vue-components` would match a `v*` release trigger. GitHub's `*` doesn't match `/`, so a prefix keeps every library tag out of `v*` globs, and lets `refs/tags/skill/*` fetch all of them at once. The `.` and `@` separators are unambiguous because names can't contain either. Checked with `git check-ref-format`.
- **Reverse:** change `TAG_PREFIX` in `src/mordecai/library/versions.py`. Existing tags would need renaming.

## D4. The changelog is the version record; frontmatter stamps are optional

- **Decision:** a copy's version and lineage come from its `CHANGELOG.md`. `metadata.mordecai-version`, `mordecai-variant` and `mordecai-based-on` are optional; when present, `validate` checks they agree and `release` updates them.
- **Options:** required stamps (the brief); a separate manifest file per copy; the changelog.
- **Why:** a card hashes the skill folder's bytes. With required stamps, a skill measured before it joined the library (the planted suites) couldn't keep its card, and the brief requires those cards to check current. The changelog already has to exist and already holds each version, so it can hold the lineage line too, with no third file.
- **Reverse:** make `validate` report a copy without stamps as an error. The planted variants would then need re-measuring.

## D5. For the same copy in several sources, the source listed last wins

- **Decision:** precedence is per entry (a skill's base, or one variant), and the last listed source wins. Shadowed copies are reported, never installed, never merged.
- **Options:** first listed wins (like `PATH`); a numeric priority per source; refusing duplicates.
- **Why:** configs are naturally written broad to narrow (org, team, personal), and narrower should override, as in layered settings. Per entry, so a team variant doesn't hide the org's base.
- **Reverse:** reverse the loop in `sources.resolve()`.

## D6. Git sources are read at a commit, never from a working tree

- **Decision:** every Git source, local or on GitHub, resolves its ref to a SHA and reads files from Git objects. A local folder that isn't a Git repository is read as is and recorded as unpinned.
- **Options:** read a local repository's working tree.
- **Why:** the brief asks to pin installs to a commit SHA. Reading the working tree would install uncommitted edits with a SHA that doesn't describe them. Reading objects also means no checkout, so no Git filters, hooks or `core.fsmonitor` commands from a hostile repository run.
- **Reverse:** a `working_tree = true` source option.

## D7. A broken card refuses the install by default

- **Decision:** the default `refuse` list is `hurts`, `invalid`, `broken`.
- **Options:** the brief's `hurts`, `invalid`, treating broken as unmeasured.
- **Why:** a card whose result is missing, has another hash, or gives another verdict when the engine reruns it is evidence that someone edited the card. Treating it as unmeasured would let an edited Hurts card through with only a warning.
- **Reverse:** remove `broken` from `DEFAULT_REFUSE` in `src/mordecai/library/evidence.py`, or from `[policy] refuse` in a config.

## D8. A root `skills/` folder publishes one resolved copy per name (replaced by D15)

- **Decision:** `export --skills <dir>` writes the resolved copies as plain folders, and this repository keeps the output in `skills/`, checked by a test.
- **Options:** mark library copies `metadata.internal: true`; document the problem only; tell users to use `/tree/<ref>/<path>` URLs.
- **Why:** npx skills includes internal skills whenever one is named (`--skill name`), and picks the first same-named copy it finds. A non-empty `skills/` stops its recursive search, and seeds its seen-names set when `--full-depth` forces the search anyway, so every name resolves to the published copy.
- **Reverse:** delete `skills/` and its test.

## D9. Frontmatter is read with strictyaml

- **Decision:** the library parses frontmatter with strictyaml 1.7.3, the parser `skills-ref` uses, pinned in the `library` extra.
- **Options:** PyYAML; a small parser in the standard library, like the one `lint` uses for case files.
- **Why:** "spec-valid" in practice means "what the reference validator accepts". strictyaml refuses flow style, anchors, tags and duplicate keys exactly as `skills-ref` does, and PyYAML or a hand-written parser would disagree with it at the edges. `lint` keeps its own reader, since the engine stays standard library only.
- **Reverse:** swap `_load_yaml` in `src/mordecai/library/skillmd.py`.

## D10. A `fork` command creates variants

- **Decision:** `mordecai library fork <skill> --variant <name>` copies the base's newest release and records its version as the lineage.
- **Options:** create variant folders by hand.
- **Why:** the brief requires each variant to record the base version it came from. A command gets that right every time; by hand it's easy to fork from an unreleased working copy.
- **Reverse:** remove the subcommand; `validate` still checks hand-made variants.

## D11. The MCP server can't override the install policy

- **Decision:** `install_skill` has no `allow` argument. Installing a refused version takes `mordecai library install --allow` at the command line.
- **Options:** expose `allow` like the command line does.
- **Why:** a model calling the tool could pass `allow` itself, and the user would see only a request to install. An override should be something a person types.
- **Reverse:** add an `allow: list[str]` argument to `install_skill` and pass it to `plan()`.

## D12. Replacing an installed copy over MCP takes two calls

- **Decision:** when `install_skill` would replace an installed copy (an update, or another variant), it writes nothing and returns the diff with `needsConfirmation`. The client calls again with `confirm_replace: true`.
- **Options:** a separate `update_skill` tool; replace without asking.
- **Why:** the brief asks for the diff before an update replaces an installed skill. Two calls put the diff in front of the client before anything changes, and keep the tool list to the seven the brief names.
- **Reverse:** drop the `needsConfirmation` branch in `server.py`.

## D13. Library result files use paths relative to the repository

- **Decision:** absolute local paths in a committed result are made relative to the repository root, by removing the leading folder, and the card is remade with `mordecai identify` from the edited file. The evidence folder's NOTE.md records the original hash.
- **Options:** keep the raw bytes, so the result hash equals the recorded card's; replace paths with `/work/...` as the test fixtures do.
- **Why:** no committed file may name a local home folder. Relative paths, unlike `/work/...`, still lead `identify` to the cases on disk, so the remade card keeps its cases hash and checks current. Only the result hash changes, and the note ties it back to the recorded one.
- **Reverse:** not without putting local paths back.

## D14. A lockfile records a local source's path as the config wrote it

- **Decision:** `source.path` in `mordecai-lock.json` and in an export's manifest is the path text from the config (or relative to the project, if the source is inside it), not the resolved absolute folder.
- **Options:** the resolved absolute path.
- **Why:** lockfiles are committed with projects, and an absolute path names one machine's folders. The commit SHA already pins what was installed.
- **Reverse:** `SourceSpec.describe()` in `sources.py`.

## D15. The root publishes only the mordecai skill, and exports always refuse the defaults

- **Decision:** `skills/` holds only `mordecai`, a short skill on running Mordecai, chosen by `[export] skills` in `mordecai-library.toml`. Every export, `--skills` or `--marketplace`, refuses Hurts, Invalid and broken copies whatever the config's policy says. This replaces D8's "one resolved copy per name".
- **Options:** keep publishing the seeded skills (D8); publish nothing at the root.
- **Why:** the seeded skills are demo content, made-up conventions that would do harm in a real project, and one is deliberately harmful. Publishing nothing makes npx skills search the whole repository, which reaches the planted suites' deliberately harmful skills. One harmless real skill stops that search. Exports reach tools that don't run the gate, so their refusals can't be loosened.
- **Reverse:** remove `[export]` from `mordecai-library.toml` and rerun the export; the default refusals are `DEFAULT_REFUSE` in `export.py`.

## D16. Lockfile entries are checked before update or uninstall acts on them

- **Decision:** an entry must be `<target>/<skill>` inside the project, reached without links, and, if the folder exists, hold a SKILL.md naming that skill. Otherwise update and uninstall refuse it, even with `--force`.
- **Options:** trust the lockfile, as before, and check only the folder's hash.
- **Why:** a lockfile is committed with a project and may come from someone else. A crafted entry naming `src` as an install of a skill called `src`, with `src/`'s hash, made `uninstall` delete it. The hash check alone can't stop that, since anyone can compute the hash.
- **Reverse:** `check_installed()` in `install.py`.

## D17. Paths from sources and inputs pass shared checks in `paths.py`

- **Decision:** targets refuse backslashes, drives and control characters; materializing a source never writes through a link and never replaces a file; evidence reached through a link is broken and never read; a skill folder can't hold two names that differ only by case or Unicode form; fetches allow only HTTPS, no submodules and no hooks.
- **Why:** each was reproduced first (tests/test_library_security.py says which). They matter most on macOS and Windows, where a case-insensitive or backslash-separated file system turns a harmless Linux name into an escape.
- **Reverse:** per check, in `paths.py`, `gitio.py`, `evidence.py` and `skillmd.py`.
