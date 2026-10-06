# Library design

How Mordecai keeps a shared skill library in Git, with a base and named variants for each skill, a version and history for each, and a card that says whether a version helps. Written before the library code, and updated where the code changed it. The research behind it is in [research.md](research.md). Reversible choices made during the build are in [decisions.md](decisions.md).

## What it is, in one paragraph

A library is a folder of skills in a Git repository. Each skill has a base and any number of named variants, and each of those copies is a plain, spec-valid skill folder with its own version and changelog. A release is a local annotated Git tag. A copy's version can carry a Mordecai card and the eval result behind it. `mordecai library install` copies one resolved copy, byte for byte, into the folder an AI coding tool reads, and records where it came from in a lockfile; it refuses a version whose current card says Hurts or Invalid. `mordecai mcp` serves the same operations to MCP clients. The verdict engine is unchanged: the library calls it and is never called by it.

## Layout

```
library/
  <skill>/
    base/
      <skill>/            the skill folder: SKILL.md and any other files
      CHANGELOG.md
      evidence/<X.Y.Z>/   card.json and result.json for that version (optional)
    variants/
      <variant>/
        <skill>/          the variant's skill folder
        CHANGELOG.md
        evidence/<X.Y.Z>/
```

- **Every stored copy is spec-valid.** The spec says `name` "Must match the parent directory name", and each copy's folder is named `<skill>`, whatever variant it is. So each copy validates on its own, and `skills-ref validate` passes on every one (a test runs it).
- **The skill folder is the unit.** Install copies exactly the inner `<skill>/` folder. `CHANGELOG.md` and `evidence/` sit beside it and are never installed, so library bookkeeping never changes the bytes a card measured.
- **One active variant.** An installed skill's folder name and frontmatter `name` are always `<skill>`, whichever copy is installed. A target holds at most one copy of a skill; installing another variant into the same target replaces it, through the same diff-first path as an update. The spec allows this, since each copy's name already equals its folder's name.
- **Names.** Skill and variant names follow the spec's rule: 1 to 64 characters, `a-z`, `0-9` and single hyphens, not starting or ending with a hyphen. The reference validator also accepts other lowercase Unicode letters; Mordecai doesn't, because names become folder names and tag names, and ASCII names can't hide a lookalike character. `base` is reserved and can't be a variant name.
- **Byte for byte.** An installed folder hashes the same as its stored copy, with the engine's own directory hash, so a card's skill hash verifies against the installed copy. A test installs every seeded copy and compares. Because of that, stored copies may contain only regular files and folders: a symbolic link, a submodule or any other kind of entry is refused, both by `validate` and at install.

## Versions and history

- **Semver per copy.** The base and each variant have their own `X.Y.Z` version. Pre-release and build suffixes aren't accepted, which keeps ordering and tag names simple.
- **CHANGELOG.md is the record.** Each copy has one, in a fixed form that `release` writes and `validate` checks:

  ```
  # Changelog

  ## Unreleased

  - What changed since the last release.

  ## 1.1.0 - 2026-10-06

  Based on base 1.2.0.

  - Shorter title line.
  ```

  The newest `## X.Y.Z - YYYY-MM-DD` heading is the copy's current version, and a copy with no release yet is version 0.0.0. Variants must start each release, and the Unreleased section, with `Based on base X.Y.Z.`
- **A release is an annotated local tag.** `skill/<skill>@X.Y.Z` for a base, `skill/<skill>.<variant>@X.Y.Z` for a variant. History is the tag list plus the changelog.
- **Why the `skill/` prefix.** The brief proposed `<skill>@X.Y.Z` and `<skill>.<variant>@X.Y.Z`. Both are valid refs (`git check-ref-format` accepts them), and neither can equal one of Mordecai's own `vX.Y.Z` tags, because they contain `@`. But a skill whose name starts with `v`, such as `vue-components@1.0.0`, would match a `v*` tag trigger, the common pattern for release workflows. GitHub's tag filters don't let `*` match `/`, so a fixed `skill/` prefix keeps every library tag out of `v*`, `v*.*.*` and similar globs, and makes the tags easy to list and fetch together (`refs/tags/skill/*`). The `.` between skill and variant can't be ambiguous, because neither name may contain a dot. A trigger of `*` or `**` still matches everything, and nothing can prevent that.
- **`release` never pushes.** It refuses unless everything outside the copy's own folder is committed, moves the Unreleased notes under a new heading, updates the copy's version stamps if it has them, commits the copy's folder, and creates the annotated tag on that commit. Pushing the commit and the tag is left to the author.
- **Version stamps in frontmatter are optional.** The brief put versions and lineage in `metadata` as `mordecai-version`, `mordecai-variant` and `mordecai-based-on`. The changelog is the record instead, and those three keys are an optional copy of it: if a copy has any of them, `validate` checks they agree with the changelog, and `release` updates them. The reason is evidence. A card hashes the skill folder's exact bytes, so a version written into `SKILL.md` would make every release change the bytes, and a skill measured before it joined the library, such as the planted suites, couldn't keep its card. The seeded org skill uses stamps; the planted variants can't, and don't.
- **Unreleased changes are visible.** `status` compares each copy's folder at the source's ref with its newest tag, and reports a copy whose files changed since its last release.

## Lineage

- `fork <skill> --variant <name>` copies the base's newest release into `variants/<name>/` and records `Based on base X.Y.Z.` in the new copy's Unreleased section.
- Each variant release records the base version it is based on. `release --based-on X.Y.Z` changes it, after the author has brought the variant up to date by hand; the base version must be a released one.
- `status` reports a variant whose `Based on` version is older than the base's newest release, as "behind base". It never merges: a variant is someone's deliberate change, and the right merge is a judgment call.

## Sources and precedence

A config file lists the sources to read. It is TOML (read with the standard library's `tomllib`), found at `--config`, then `$MORDECAI_LIBRARY_CONFIG`, then `./mordecai-library.toml`, then `$XDG_CONFIG_HOME/mordecai/library.toml` (`~/.config/mordecai/library.toml`). With none, the only source is the current directory, so an author can work in their own library repository with no config.

```toml
[[source]]
name = "org"
github = "acme/skills"      # a GitHub repository, read with git over HTTPS
ref = "main"                # optional: a branch, tag or commit; default the default branch

[[source]]
name = "team"
github = "acme/payments-skills"

[[source]]
name = "personal"
path = "~/skills"           # a local folder, relative to this file if not absolute
library = "library"         # optional: the library folder inside the source; default "library"

[variants]
pr-description = "mobile"   # the variant install uses when --variant isn't given

[policy]
refuse = ["hurts", "invalid", "broken"]

[install]
targets = ["agents", "claude"]   # where the MCP server may install
```

- **Which copy wins.** Each copy is an entry: a skill's base, or one named variant of it. For each entry, the source listed last wins. List sources from broadest to narrowest (org, team, personal), and a narrower source overrides a broader one entry by entry: a team can add a `mobile` variant of an org skill without replacing the org's base, and a personal source can replace one variant without touching the rest. A shadowed copy is never installed, and `list --all` and `status` show it. Copies are never merged.
- **Lineage across sources.** A variant's `Based on` version is compared with the base that wins for that skill, wherever it comes from. So a team library may hold only variants of an org skill, with no `base/` of its own; `validate` notes that it can't check those variants' lineage there.
- **Two libraries in one repository** share one set of tags. A tag counts for a copy only if the copy's changelog exists at the tagged commit, so a copy added later in another library isn't mistaken for a tagged one. Two libraries in one repository still shouldn't both release a copy with the same name.
- **Access control is GitHub's.** Who can change a library is decided by repository permissions, CODEOWNERS and branch rules. Mordecai only reads sources; nothing it does writes to GitHub.
- **Commits, not working trees.** A Git source, local or on GitHub, is always read at a commit: the ref resolves to a SHA, and every file comes from that commit's objects, never from a working tree. Uncommitted edits are never installed, and every install records a SHA. A local folder that isn't a Git repository is allowed, read as it is, and recorded as unpinned, with only a content hash.
- **Private repositories.** A token comes only from the `MORDECAI_GITHUB_TOKEN` environment variable, or `GITHUB_TOKEN` if that isn't set. It is never read from the config, never written to the lockfile, and never printed or logged. It is passed to Git in its environment as an HTTP header for `github.com`, not on the command line, where other users' processes could read it.

## Evidence

- **Where.** A version's card and the result it was made from sit in `evidence/<X.Y.Z>/card.json` and `result.json`, beside the copy. They can be added after the release: evidence is read from the source's ref, and matched to a version by its files, not by where it was committed.
- **What listing shows.** For each version, the verdict, or one of these states:

  | State | Meaning | Install |
  |---|---|---|
  | current | the card's skill hash equals the hash of this version's folder, the result's hash equals the card's, the engine recomputes the same verdict from the result, and the cases match | the verdict decides |
  | current, cases changed | as above, but the eval cases changed since the card or aren't in the source | the verdict decides, with a warning |
  | stale | the card was made for other files | allowed, with a warning that names the card's verdict |
  | unmeasured | no card | allowed, with a warning |
  | broken | the card can't be read, its result is missing or has a different hash, or the result gives a different verdict | refused |

- **Code decides.** The library never trusts the verdict written in a card. It reruns the engine on the stored result, with the rules the card records, and uses that.
- **Install policy.** `refuse` lists verdicts and states install won't accept. The default is `hurts`, `invalid` and `broken`; the brief asked for Hurts and Invalid, and broken is added because a card that doesn't match its own result can't be read either way. Stale and unmeasured always get a warning. `install --allow VERDICT` overrides one refusal for one install, and the lockfile records that it was overridden.
- **The limit.** The gate trusts committed result files. Someone who writes a fake result and a card from it passes the gate. The card proves which files a result is about, not that the eval really ran.

## Delivery

**Install is the main path.**

```
mordecai library install <skill> [--variant V] [--version X.Y.Z] [--target agents|claude|github|cursor|PATH]... [--user]
```

- **Targets.** `agents` is `.agents/skills/` (read by Codex, Cursor and Copilot) and is the default. `claude` is `.claude/skills/` (Claude Code doesn't read `.agents/skills/`). `github` is `.github/skills/` (Copilot), `cursor` is `.cursor/skills/`, and a path names any folder inside the project. `--target` can be repeated. `--user` installs into the same folders under the home directory instead.
- **Version.** Without `--version`, install takes the copy's newest release tag that the source's ref contains. If the copy has no tags (a shallow clone, or tags that weren't pushed), it takes the copy at the ref, records it as untagged and says so.
- **The lockfile.** `mordecai-lock.json` at the project root, or `$XDG_STATE_HOME/mordecai/lock.json` for `--user`. One entry per installed folder, keyed by its path, recording skill, variant, version, tag, source, ref, commit SHA, the copy's path in the source, the folder hash and the verdict with its state. Like npx skills' lockfile, it has no timestamps, so it merges cleanly.
- **update** checks every locked skill (or one) against its source, prints a unified diff of each change, and replaces nothing without `--yes`. It refuses to replace a folder whose files no longer match the lockfile's hash, since that would discard someone's edits, unless `--force` is given.
- **uninstall** removes a folder only if the lockfile records it and its files still match; then it removes the lockfile entry.

**Why install beats serving.** Claude Code, Codex, Cursor and Copilot all read each installed skill's name and description up front, and load the body when the description matches the task. A skill served over MCP reaches the model only if the model first decides to call a tool, from a tool description written for the server, not for the skill. So an installed skill fires the way it was measured to fire, and a served one may not. The MCP server's `get_skill` is the fallback for a client without native skills: the model can read the text, but nothing makes it look.

## Enterprise

`mordecai library export --marketplace <dir>` writes the resolved library as a Claude Code plugin marketplace an organization can host as a repository:

```
<dir>/
  .claude-plugin/marketplace.json
  plugins/<skill>/.claude-plugin/plugin.json
  plugins/<skill>/skills/<skill>/        the resolved copy, byte for byte
  mordecai-export.json                   source, commit, version and verdict of each plugin
```

- One plugin per skill, named after the skill, holding the copy install would pick (the `[variants]` default, or the base), at its newest release. The install policy applies: a refused copy is left out and reported.
- Plugin names may not start with `claude-` or `anthropic-`, and some marketplace names are reserved; export refuses those.
- The organization commits the folder to a repository and restricts and installs it with managed settings. [examples/managed-settings.json](../examples/managed-settings.json) shows `strictKnownMarketplaces` (allow only this marketplace), `extraKnownMarketplaces` (register it, with `autoUpdate`) and `enabledPlugins` (`"<skill>@<marketplace>": true` to install, `false` to block).
- `export --skills <dir>` writes the same resolved copies as plain `<dir>/<skill>/` folders, the shape npx skills and APM read.

## Coexisting with npx skills and APM

Mordecai isn't a general package manager. It installs only skills, only from Mordecai library layouts, and works beside the tools that are.

- **Its own lockfile.** It writes `mordecai-lock.json` and never reads or writes `skills-lock.json`, `.skill-lock.json` or `apm.lock.yaml`. A compatible lockfile was considered and rejected: npx skills' `update` re-runs its own discovery against the source, which in a library repository would pick an arbitrary same-named copy and replace the one Mordecai installed.
- **It never touches another tool's folders.** Install refuses a destination that exists and isn't in Mordecai's lockfile, and refuses a destination that is a symbolic link (npx skills links agent folders to `.agents/skills/` by default). It suggests removing the folder or picking another target.
- **It notices when another tool replaced its install.** npx skills deletes whatever is at a destination before writing. If that happens, the folder no longer matches the lockfile's hash, and `status`, `update` and `uninstall` report it instead of acting on it.
- **npx skills against a library repository.** In a repository with no standard skill folder, npx skills falls back to a recursive search, and when two copies share a name the first one found wins. A library repository holds several copies of each name, so a plain `npx skills add` could pick any of them. `metadata.internal: true` isn't enough, because npx skills includes internal skills whenever one is asked for by name. So a library repository should publish what it means to be installed in a root `skills/` folder with `export --skills skills`, and `[export] skills` in its config chooses which skills. npx skills reads `skills/` first, and with something found there it doesn't search further. With `--full-depth` it searches further, and a name it has already seen in `skills/` still resolves to that copy, but other names resolve to whatever it finds first. An export always refuses Hurts, Invalid and broken copies, since the tools that read it don't run the gate. This repository publishes only its `mordecai` skill: everything else in its library is demo content. A test checks that `skills/` is what export writes, and that nothing refused is in it.
- **APM** reads a root `skills/` folder as a package of skills, so it sees the same copies.

## The MCP server

`mordecai mcp` is a stdio server on the official MCP Python SDK. It shares the library code with the command line, reads the same config, and writes the same lockfile.

| Tool | What it does | Changes files |
|---|---|---|
| `list_skills` | every skill, its copies, versions and verdicts | no |
| `search_skills` | skills whose name or description contains the query words; no model involved | no |
| `get_skill` | a copy's `SKILL.md` text, file list, version, lineage and verdict | no |
| `skill_history` | a copy's releases, notes and the verdict for each | no |
| `check_updates` | locked skills that have a newer release, with the verdict of each | no |
| `install_skill` | installs one copy into a configured target; returns the diff and writes nothing if it would replace an installed copy, unless called again with `confirm_replace` | yes |
| `uninstall_skill` | removes an installed copy recorded in the lockfile | yes |

- The two writing tools say in their descriptions that they change files in the project, and carry `destructive_hint` and `read_only_hint` annotations, so a client can ask the user first. Annotations are hints, not security; the real limit is that they write only inside the targets listed in `[install] targets`, under the project the server was started for.
- No tool writes to GitHub, and none runs a skill's scripts.
- The server writes nothing to standard output except protocol messages, and logs no token.

## Safety

Everything read from a source is untrusted: skill text, file names, changelogs, cards and results.

- **Pinned.** Every Git install records the commit SHA it came from, and the folder hash of what it wrote.
- **Diff first.** Nothing replaces an installed skill without showing the diff first: `update` needs `--yes`, and the MCP tool needs a second call.
- **Never executed.** Mordecai never runs a skill's scripts, and never runs Git hooks or filters from a source: files come from `git cat-file`, and every Git call disables `core.fsmonitor`. But a skill's scripts run with the user's own permissions whenever their AI tool uses them, so install says when a skill includes executable files or a `scripts/` folder.
- **Paths stay inside.** A file path from a source must be relative, without `..`, and without control characters. A target must be inside the project (or home, for `--user`), no folder on the way to it may be a symbolic link, and every write is checked with the engine's `within()` before it happens. Files are written to a temporary folder beside the destination and renamed into place, so a failed install leaves nothing half written.
- **Limits.** A skill folder may hold at most 1,000 files and 20 MB, and frontmatter at most 64 KB, so a hostile source can't fill a disk or exhaust memory.
- **Printed safely.** Every name, description and note is printed through the engine's `clean()`, so text from a source can't send terminal escapes.
- **The engine's protections are reused**, not copied: `within()`, the directory hash that never follows a link, and `clean()`.

## Engine boundary

- The library lives in `src/mordecai/library/`. It imports the engine; no engine module imports it. `mordecai.cli` hands `library` and `mcp` to it with a lazy import, so `identify`, `check` and `lint` never load it. A test checks both.
- The engine stays standard library only. The library's own dependencies are an optional extra, `library`: the MCP SDK, and strictyaml, the parser `skills-ref` uses, so Mordecai reads frontmatter exactly as the reference validator does. A plain `uv sync` gives a working `identify`, `check` and `lint`, and a test runs them with those packages unimportable.
