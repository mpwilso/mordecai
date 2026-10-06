# The skill library

How to keep, release and install skills with Mordecai's library, in detail. The [README](../README.md#what-the-verdicts-govern-the-skill-library) has the short version, [library-design.md](library-design.md) the design and its reasons, [research.md](research.md) what other tools do, and [decisions.md](decisions.md) the choices made along the way.

A library is a folder of skills in a Git repository. `mordecai library` installs a skill from it into the folder your AI coding tool reads, records where it came from, and refuses a version whose card says it hurts. `mordecai mcp` offers the same operations to MCP clients. It works for one person with a personal library, and for an organization with base skills and team variants.

## Base and variants

Each skill has a base and any number of named variants, and each of those copies is a plain skill folder that passes the Agent Skills spec's reference validator (`skills-ref validate`) on its own:

```
library/pr-description/base/pr-description/SKILL.md
library/pr-description/base/CHANGELOG.md
library/pr-description/variants/mobile/pr-description/SKILL.md
library/pr-description/variants/mobile/CHANGELOG.md
library/pr-description/variants/mobile/evidence/1.1.0/card.json    (when it has been measured)
```

The spec says a skill's `name` must match its folder, so every copy's folder is named after the skill, whichever variant it is. An installed skill always has that name, and a project has one variant of it at a time. Install copies the inner folder byte for byte, so the card's skill hash verifies against the installed copy with `mordecai check`.

## Versions and history

The base and each variant have their own semver version and `CHANGELOG.md`. `mordecai library release <skill> [--variant V] --bump patch|minor|major` moves the changelog's Unreleased notes under a new version, commits the copy, and creates a local annotated tag: `skill/<skill>@X.Y.Z` for a base, `skill/<skill>.<variant>@X.Y.Z` for a variant. It never pushes. The `skill/` prefix keeps these tags out of `v*` release triggers. History (`mordecai library history`) is the tags plus the changelog.

Each variant records the base version it was forked from (`mordecai library fork`) or last brought up to. `mordecai library status` reports a variant that is behind its base's newest release. It never merges: a variant is someone's deliberate change.

## Sources and precedence

A config file (`mordecai-library.toml`) lists sources, each a GitHub repository or a local folder, with an optional ref. For each copy of a skill (its base, or one named variant), the source listed last wins. List them broad to narrow, org then team then personal, and a team can add a variant of an org skill, or a person replace one, without copying the rest. Shadowed copies are reported, never installed and never merged. [examples/library.toml](../examples/library.toml) shows all three. Who may change a library is decided by GitHub: repository permissions, CODEOWNERS and branch rules.

Every Git source is read at a commit, from Git's objects, never from a working tree, and every install records that commit. A private repository is read with a token from `MORDECAI_GITHUB_TOKEN` (or `GITHUB_TOKEN`), passed to Git in its environment, never read from the config, never written to the lockfile and never printed.

## Verdicts gate installs

A version can carry a card and the eval result it was made from, beside it in `evidence/<version>/`. The library never trusts the verdict written in the card: it checks that the result is the one the card was made from, reruns the verdict rules on it, and checks that the card's skill hash equals the hash of that version's files. Listing shows the verdict, or one of these: unmeasured (no card), stale (a card for other files), or broken (a card that doesn't match its result).

Install always refuses Hurts, Invalid and broken, and warns on stale and unmeasured. A config's `[policy] refuse` can add to those, never drop them, so a project's own `mordecai-library.toml` can't switch the gate off. `--allow hurts`, typed at the command line, overrides one refusal for one install or update; the lockfile records it, but a later update never reuses it.

In the seeded library, two variants carry real cards from the planted check. Their skill folders are byte for byte the planted skills, their result files are the recorded results with local paths made relative (each evidence folder's NOTE.md gives the original hash), and their cards were made from them with `mordecai identify`:

| Copy | Planted suite | Card | Install |
|---|---|---|---|
| `ferry-workflow` variant `qrx` | 1, a made-up convention | Helps (+100) | installs |
| `branch-naming` variant `camelcase` | H1, a convention that conflicts with the graders | Hurts (-100) | refused |

The rest of the seeded library (an org skill, `pr-description`, with a `platform` and a `mobile` variant, several releases each, `mobile` behind its base) is unmeasured, and says so.

## Install, update and the lockfile

```
uv run mordecai library install <skill> [--variant V] [--version X.Y.Z] [--target agents|claude|github|cursor|PATH]...
uv run mordecai library update [<skill>] [--yes]
uv run mordecai library uninstall <skill>
```

- `agents` (`.agents/skills/`, read by Codex, Cursor and Copilot) is the default target. Claude Code's docs list `.claude/skills/` and not `.agents/skills/`, so add `--target claude` for it. `--user` installs under your home folder instead.
- `mordecai-lock.json` in the project records each installed folder's source, ref, commit, tag, version, folder hash and verdict.
- `update` prints a diff of every change and replaces nothing without `--yes`. Installing a different variant over an installed one works the same way.
- Mordecai never replaces or removes a folder it didn't install, or one that changed since it did.
- Every `mordecai library` command exits 0 when it's done or has nothing to report, 1 for what it checks for (validate errors, status findings, a refused install, or an update or replacement waiting for `--yes`), and 2 for input it can't read or won't use, including a folder it won't touch.
- It never runs a skill's scripts. But a skill's scripts run with your permissions when your AI tool uses them, so install says when a skill has any. Read them first.

**Why install rather than serve.** Claude Code, Codex, Cursor and Copilot all read each installed skill's name and description up front, and load the rest when the description matches the task. That is how a skill fires, and how it was measured. A skill served over MCP reaches the model only if the model first decides to call a tool. So install is the main path, and reading a skill over MCP is the fallback for clients without native skills.

## Enterprise: export a marketplace

```
uv run mordecai library export --marketplace <dir> --name <marketplace> --owner "<org>"
```

This writes the resolved library as a Claude Code plugin marketplace: one plugin per skill, holding the copy install would pick, byte for byte, with its verdict in the description. Refused copies are left out. An organization commits the folder to a repository, and its managed settings restrict users to that marketplace (`strictKnownMarketplaces`), register it (`extraKnownMarketplaces`) and install each plugin for everyone (`enabledPlugins`). [examples/managed-settings.json](../examples/managed-settings.json) is an example, explained in [examples/README.md](../examples/README.md).

`export --skills <dir>` writes the same copies as plain `<skill>/` folders, the layout npx skills and APM read. An export goes to tools that don't run Mordecai's gate, so it always leaves out Hurts, Invalid and broken copies, whatever the config's policy says. To publish your own library, run `uv run mordecai library export --skills skills` in it, with `[export] skills` in its `mordecai-library.toml` listing what to publish.

This repository publishes only one skill at its root, in [skills/](../skills/): `mordecai`, which tells an agent how to run Mordecai. The seeded library is demo content (made-up conventions, and one deliberately harmful variant), so none of it is published. Something has to be in `skills/`, though: with nothing there, `npx skills add mpwilso/mordecai` would search the whole repository and could install any of its same-named copies.

## Setup

```
uv sync --extra library
uv run mordecai library list
```

With no config, the only source is the current folder. To install into another project, give it a config that lists your library, with `--config` or in `~/.config/mordecai/library.toml`, and run it from that project: `uv run --project /path/to/mordecai --extra library mordecai library install <skill> --config /path/to/mordecai-library.toml`.

**The MCP server.** `mordecai mcp` is a stdio server with seven tools: `list_skills`, `search_skills`, `get_skill`, `skill_history`, `check_updates`, `install_skill` and `uninstall_skill`. The last two change files: they write only inside the targets the config's `[install] targets` allows, they're marked destructive so a client can ask you first, they can't override the install policy, and replacing an installed copy takes a second call after the diff. No tool writes to GitHub. The server reads the config from the folder it is started in (the project), and installs into that project unless you pass `--project`. `get_skill` returns skill text written by someone else, and a model may treat that text as instructions; that is one reason installing goes through the gate, and reading a skill over MCP is only the fallback. Errors name no local folders.

None of these snippets has been run against its client. Each follows the client's own docs as read on 2026-10-06; the parts marked unverified weren't stated there.

Claude Code ([docs](https://code.claude.com/docs/en/mcp)) reads a project's `.mcp.json`, the file `claude mcp add --scope project` writes, and asks before it starts a server from one. This repository has one, [.mcp.json](../.mcp.json): it serves this repository's library, and installs into a gitignored `.mcp-demo/` folder (or `$MORDECAI_MCP_PROJECT`), so you can try it without touching your user config. Run `uv sync --extra library`, start Claude Code in the repository, approve the `mordecai` server, and check `/mcp` shows it connected. For your own project, put this in its `.mcp.json`. Unverified: that Claude Code starts the server in the project folder.

```json
{
  "mcpServers": {
    "mordecai": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/path/to/mordecai", "--extra", "library", "mordecai", "mcp"]
    }
  }
}
```

GitHub Copilot in VS Code, `.vscode/mcp.json` ([docs](https://code.visualstudio.com/docs/copilot/reference/mcp-configuration)). The server starts in the workspace folder. Unverified: where `${env:...}` reads its value from.

```json
{
  "servers": {
    "mordecai": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/path/to/mordecai", "--extra", "library", "mordecai", "mcp"],
      "env": { "MORDECAI_GITHUB_TOKEN": "${env:MORDECAI_GITHUB_TOKEN}" }
    }
  }
}
```

Cursor, `.cursor/mcp.json` ([docs](https://cursor.com/docs/context/mcp)). Unverified: the folder Cursor starts the server in, so the project is passed explicitly.

```json
{
  "mcpServers": {
    "mordecai": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/path/to/mordecai", "--extra", "library", "mordecai", "mcp", "--project", "${workspaceFolder}"],
      "env": { "MORDECAI_GITHUB_TOKEN": "${env:MORDECAI_GITHUB_TOKEN}" }
    }
  }
}
```

Codex, `~/.codex/config.toml` ([docs](https://developers.openai.com/codex/mcp)). Unverified: the folder Codex starts the server in.

```toml
[mcp_servers.mordecai]
command = "uv"
args = ["run", "--project", "/path/to/mordecai", "--extra", "library", "mordecai", "mcp", "--project", "/path/to/your/project"]
env_vars = ["MORDECAI_GITHUB_TOKEN"]
```

**Behind Polarizer.** Unverified, and written only from [Polarizer's README](https://github.com/mpwilso/polarizer): Polarizer can sit in front of `mordecai mcp` as an upstream server, so a person approves the tool definitions and each install or uninstall before it runs. In `polarizer.toml`:

```toml
[upstream.mordecai]
command = "uv"
args = ["run", "--project", "/path/to/mordecai", "--extra", "library", "mordecai", "mcp", "--project", "/path/to/your/project"]

[upstream.mordecai.tools]
list_skills = { class = "open-world" }
search_skills = { class = "open-world" }
get_skill = { class = "open-world" }
skill_history = { class = "open-world" }
check_updates = { class = "open-world" }
install_skill = { class = "destructive" }
uninstall_skill = { class = "destructive" }
```

The reading tools are `open-world` because a GitHub source is fetched over the network. Polarizer holds a `destructive` tool on every call, so each install and uninstall waits for you.

## The demo

[library-demo.md](library-demo.md) runs in a few seconds with no tokens and no model: it lists the library, shows history, installs a variant into a temporary project, shows the lockfile, tries the Hurts variant and gets refused, reports the variant behind its base, and exports a marketplace. Every output in it is from a real run.

## Limits

The README's [limits of the library](../README.md#limits-of-the-library) apply. One more detail:

- **Version stamps in frontmatter are optional.** The changelog is the record of versions and lineage. A skill measured before it joined the library, like the planted suites, can't carry stamps without changing the bytes its card measured. [decisions.md](decisions.md) has the reasoning (D4).
