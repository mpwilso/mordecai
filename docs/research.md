# Research for the skill library

What the specification, the AI coding tools and the existing skill installers and servers do, as read on 2026-10-06, and what Mordecai's library adds. Every claim links to the page it came from. Where a page couldn't be read or a claim couldn't be confirmed, it says so. No code was copied from any of these projects.

## Corrections to the brief

The brief listed what was already known. Most of it holds. These parts were wrong, incomplete or out of date:

1. **Skill names.** The spec allows only `a-z`, `0-9` and hyphens, but the reference validator also accepts any lowercase Unicode letter (it checks `isalnum()` after NFKC normalization). Mordecai uses the spec's ASCII rule, since names also become folder names and Git tag names, and ASCII-only names can't hide a lookalike character.
2. **Unique metadata keys.** The spec has no uniqueness rule. It says only "We recommend making your key names reasonably unique to avoid accidental conflicts." Duplicate keys fail in `skills-ref` because its YAML parser, strictyaml, refuses them.
3. **The reference validator is stricter than Claude Code.** `skills-ref validate` rejects any top-level field outside `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`, and rejects YAML flow style (`[a, b]`, `{a: b}`), anchors and tags. Claude Code accepts many more fields, such as `when_to_use` and `disable-model-invocation`. The project also says `skills-ref` "is intended for demonstration purposes only. It is not meant to be used in production."
4. **`.agents/skills/` and Claude Code.** Codex, Cursor and Copilot in VS Code all read `.agents/skills/`. The Claude Code skills page lists only `.claude/skills/` locations and doesn't mention `.agents/`. A skill installed only into `.agents/skills/` doesn't reach Claude Code.
5. **Lockfiles.** npx skills keeps two: `skills-lock.json` in the project and `~/.agents/.skill-lock.json` (or `$XDG_STATE_HOME/skills/.skill-lock.json`) for global installs. APM keeps `apm.lock.yaml` beside `apm.yml`.
6. **npx skills discovery.** Marking a skill `metadata.internal: true` hides it from a bulk install, but an install that names the skill (`--skill name` or `owner/repo@name`) includes internal skills. When two copies share a name, the first one found wins, with no warning. So hiding copies isn't enough to stop a confusing pick; see [npx skills](#npx-skills).
7. **"None of them gate on evidence"** is accurate for the four MCP servers and the two commercial registries named in the brief. It isn't true of every catalog: NVIDIA's skills catalog gates publication on an eval run with and without the skill, and Tessl's registry shows with-and-without scores for each version. See [what Mordecai adds](#what-mordecais-library-adds).
8. **The MCP Python SDK changed in 2.0.** `FastMCP` is now `MCPServer`, and the in-process test helper `create_connected_server_and_client_session` was replaced by `mcp.Client`.
9. **`extraKnownMarketplaces` is a map, not a list.** `strictKnownMarketplaces` is a list of source objects and can only be set in managed settings.

## The Agent Skills specification

Source: [agentskills.io/specification](https://agentskills.io/specification).

- **`name`**: "Must be 1-64 characters", "May only contain unicode lowercase alphanumeric characters (`a-z`, `0-9`) and hyphens (`-`)", "Must not start or end with a hyphen", "Must not contain consecutive hyphens (`--`)", and "Must match the parent directory name".
- **`description`**: "Must be 1-1024 characters". It "Describes what the skill does and when to use it."
- **Optional fields**: `license`; `compatibility`, "1-500 characters if provided"; `metadata`, "a map from string keys to string values"; `allowed-tools`, a space-separated string, marked experimental. There are no other fields.
- **Length**: "Keep your main `SKILL.md` under 500 lines." Metadata is about 100 tokens, and instructions under 5000 tokens are recommended.
- **Layout**: optional `scripts/`, `references/` and `assets/`; any other files are allowed.
- **Where clients look**: the spec "does not mandate where skill directories live". The [client guide](https://agentskills.io/client-implementation/adding-skills-support.md) recommends `<project>/.agents/skills/` and `~/.agents/skills/` as "a widely-adopted convention for cross-client skill sharing", says project skills override user skills, and suggests clients warn and load anyway when the name doesn't match the folder.

**The reference validator.** [`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref) is also on PyPI as `skills-ref` 0.1.1. Its parser splits the file on `---`, loads the frontmatter with `strictyaml.load`, and turns every metadata value into a string. Its validator allows exactly the six spec fields and reports "Directory name '...' must match skill name '...'" on a mismatch. Mordecai runs it in a test over every stored copy in `library/` and every exported copy, as a cross-check on its own validator; it isn't a runtime dependency.

## Claude Code

**Skills** ([code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)). Claude Code "follow[s] the Agent Skills open standard". It reads skills from the managed settings directory, `~/.claude/skills/<name>/SKILL.md`, the project's `.claude/skills/<name>/SKILL.md`, nested `.claude/skills/` folders, `--add-dir`, and plugins (`<plugin>/skills/<name>/SKILL.md`, invoked as `/plugin-name:skill-name`). Precedence is "Enterprise over personal, and personal over project." "Claude uses [the description] to decide when to apply the skill." The listing of descriptions gets 1% of the context window by default, and each description plus `when_to_use` is cut at 1,536 characters.

**Plugin marketplaces** ([plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference), [manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference)).

- `.claude-plugin/marketplace.json`: "`name`, `owner`, and `plugins` are required"; `owner.name` is required. A marketplace name uses letters, digits, `.`, `_` and `-`. Some names are reserved, including `claude-plugins-official`, `agent-skills` and anything starting `claudeai-`.
- A plugin entry needs `name` and `source`. A relative source "Must start with `./`" and may not contain `..`. Other sources are `github` (`repo`, `ref`, `sha`), a git `url`, `git-subdir`, `npm` and others. "When `plugin.json` also sets `version`, `plugin.json` takes precedence."
- `plugin.json` is optional and "`name` is the only required key". A plugin can hold only skills, as `skills/<name>/SKILL.md`. Plugin names are kebab-case and may not start with `claude-` or `anthropic-`.

**Managed settings** ([settings reference](https://code.claude.com/docs/en/settings-reference), [plugins for organizations](https://code.claude.com/docs/en/plugins/org), [managed settings](https://code.claude.com/docs/en/managed-settings)).

- `strictKnownMarketplaces`: managed settings only; an "array of marketplace source objects". Unset, users can add any marketplace; "An empty array is a complete lockdown". It "controls what users may add but registers nothing."
- `extraKnownMarketplaces`: an "object mapping a marketplace name to an object with a `source` object and an optional `autoUpdate` Boolean".
- `enabledPlugins`: an "object mapping `plugin-name@marketplace-name` to a Boolean". Set to `false` in managed settings, a plugin "is blocked from installation at every scope and hidden from the marketplace".
- Related keys: `blockedMarketplaces`, `disableSideloadFlags`, `strictPluginOnlyCustomization`.
- File locations: `/Library/Application Support/ClaudeCode/managed-settings.json` on macOS, `/etc/claude-code/managed-settings.json` on Linux and WSL, `C:\Program Files\ClaudeCode\managed-settings.json` on Windows, plus `managed-settings.d/*.json` drop-ins.
- A catch: once any allowlist is set, a plugin kept under `.claude/skills/` with its own `.claude-plugin/plugin.json` stops loading unless `{ "source": "skills-dir" }` is allowed. Plain skills keep loading.

**MCP** ([code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp)): `claude mcp add [options] <name> -- <command> [args...]`, with `--scope local|project|user`; project scope writes `.mcp.json`, which expands `${VAR}`. Project servers ask for approval in interactive sessions.

## Other AI coding tools

All three read `.agents/skills/` in the project and `~/.agents/skills/` for the user.

| Tool | Project skill folders | User skill folders | MCP config |
|---|---|---|---|
| GitHub Copilot in VS Code ([skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills), [MCP](https://code.visualstudio.com/docs/copilot/reference/mcp-configuration)) | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | `.vscode/mcp.json`, key `servers`, `"type": "stdio"` |
| Cursor ([skills](https://cursor.com/docs/context/skills), [MCP](https://cursor.com/docs/context/mcp)) | `.agents/skills/`, `.cursor/skills/`, and for compatibility `.claude/skills/`, `.codex/skills/` | `~/.agents/skills/`, `~/.cursor/skills/`, `~/.claude/skills/`, `~/.codex/skills/` | `.cursor/mcp.json` or `~/.cursor/mcp.json`, key `mcpServers`, `"type": "stdio"` |
| Codex ([skills](https://developers.openai.com/codex/skills), [MCP](https://developers.openai.com/codex/mcp); both now redirect to learn.chatgpt.com) | `.agents/skills/` in the working directory, its parent and the repo root | `~/.agents/skills/`, and `/etc/codex/skills` for admins | `~/.codex/config.toml`, or `.codex/config.toml` in trusted projects, as `[mcp_servers.<name>]` |

- Each tool loads a skill's name and description first and reads the body when it decides the skill applies. Codex: "start with each skill's name and description, then load the full `SKILL.md` instructions when they decide to use that skill."
- Codex shows two skills with the same name side by side rather than merging them.
- GitHub's own Copilot page lists fewer user folders (`~/.copilot/skills` and `~/.agents/skills`) than the VS Code page.
- Unconfirmed: whether VS Code fills `${env:VAR}` from the shell VS Code started in; whether Cursor accepts a `cwd` field; Codex's older `~/.codex/skills` location, which only third-party pages mention.

## npx skills

Source: [vercel-labs/skills](https://github.com/vercel-labs/skills), README and source as of their commit `14cf84aa922c` (2026-10-05).

- **Discovery.** It looks in the repo root (if it holds `SKILL.md`), `skills/` and its `.curated`, `.experimental` and `.system` folders, and about 55 agent folders such as `.agents/skills/` and `.claude/skills/`, walking each up to three levels deep. It also reads skills declared in a root `.claude-plugin/marketplace.json` or `plugin.json`. "If no skills are found in standard locations, a recursive search is performed", up to five folders deep; `--full-depth` forces that search.
- **Same names.** The first copy found wins, with no warning.
- **Hidden skills.** `metadata.internal: true` hides a skill unless `INSTALL_INTERNAL_SKILLS=1` is set. The code includes internal skills whenever one is requested by name ("Include internal skills when a specific skill is explicitly requested"), and compares with the YAML Boolean `true`.
- **Installs.** The main copy goes to `.agents/skills/<name>` (or `~/.agents/skills/<name>`), and each agent's folder gets a symbolic link to it unless `--copy` is passed. Before writing, it deletes whatever is at the destination.
- **Lockfiles.** `skills-lock.json` in the project (version 1: `source`, `sourceType`, `ref`, `skillPath`, `computedHash`, a SHA-256 over sorted paths and bytes, "Intentionally minimal and timestamp-free"). Global installs use `.skill-lock.json` (version 3, with a GitHub tree SHA). Neither records a resolved commit; `ref` is what the user typed.

**What that means for this repository.** Before 0.3.0 this repo had no standard skill folder, so `npx skills add mpwilso/mordecai` fell back to the recursive search and found the planted skills in `evals/planted/` and the probe in `tests/fixtures/`. The library adds more copies of the same names (a base, variants, and planted variants). With a recursive search, the copy installed for a name would depend on the order the disk lists folders. The design answers this by publishing one resolved copy per name in a root `skills/` folder, which stops the recursive fallback; see [library-design.md](library-design.md#coexisting-with-npx-skills-and-apm).

## APM

Source: [microsoft/apm](https://github.com/microsoft/apm) and its [docs](https://microsoft.github.io/apm/).

- Installs skills, prompts, instructions, agents, hooks, plugins, MCP servers and LSP servers, declared in `apm.yml` as `owner/repo`, `owner/repo#ref` or `owner/repo/sub/path#ref`.
- Detects a package from `apm.yml`, a root `SKILL.md`, `plugin.json`, `.claude-plugin/` or `skills/`. "The directory name is the skill's identity." Maintainers say they "will keep excluding ambiguous skill names".
- Puts skills in `.claude/skills/` for Claude and in `.agents/skills/` for Copilot, Cursor, Codex and others.
- [`apm.lock.yaml`](https://microsoft.github.io/apm/reference/lockfile-spec/) records `resolved_commit` (a full SHA), `resolved_ref`, `version`, `deployed_files` and a `content_hash` ("`sha256:<hex>` digest of the materialized package tree, computed from sorted relative paths and raw file bytes"). A hash mismatch aborts the install.
- For a local file it doesn't track, it reports a conflict: "Use `--force` to overwrite, or rename the local file."

## Skill MCP servers and registries

| Project | What it does | Versions, drift, lineage | Gates on measured effect |
|---|---|---|---|
| [pinkpixel-dev/agentskills-mcp](https://github.com/pinkpixel-dev/agentskills-mcp) | stdio server: list, search, get and install skills from curated GitHub collections | none documented | no |
| skillkit-mcp (mk0e) | listed on third-party sites; its GitHub repo returned 404, so its README couldn't be read | unknown | unknown |
| [skillkit-cli](https://pypi.org/project/skillkit-cli) | scaffold, lint, pack and install; MCP tools `list_skills`, `read_skill`, `lint_skill`; a static 0 to 100 lint score | none documented | no (static lint only) |
| [timescale/tiger-skills-mcp-server](https://github.com/timescale/tiger-skills-mcp-server) | serves skills from local or GitHub sources to any MCP client | no pinning shown | no |
| [mcp-agentskills](https://github.com/zouyingcao/agentskills-mcp) | loads skills from a local folder; can run shell commands | none | no |
| [Speakeasy MCP gateway skills](https://www.speakeasy.com/docs/ai-control-plane/mcp-gateway/skills) | records, versions and distributes skills; content-addressed versions, rollback, drift tracking, a "Derived" badge | yes | no gate found. Efficacy is scored by "an automated judge" reading session transcripts, with no without-skill baseline described |
| [systemprompt.io](https://systemprompt.io/features/skill-marketplace) | self-hosted skill governance; version hash per edit; forks keep a parent pointer | yes | admin approval only |

Two catalogs do measure with and without a skill:

- [NVIDIA's skills catalog](https://docs.nvidia.com/skills/evaluating-agent-skills) gates publication on it: "PASS requires every configured dimension to pass for at least one supported agent". It is a catalog review process, not a server you install from.
- [Tessl's registry](https://tessl.io/blog/introducing-task-evals-measure-whether-your-skills-actually-work/) shows with-and-without scores for each version. No gate on install was found.

## The MCP Python SDK

[modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk), PyPI `mcp` 2.3.0 (2026-10-02), Python 3.10 or later. In 2.0, `FastMCP` became `MCPServer` (`from mcp.server.mcpserver import MCPServer`), model fields became snake_case, and tool annotations are `ToolAnnotations(read_only_hint=..., destructive_hint=..., idempotent_hint=..., open_world_hint=...)`; the docs warn "They are hints, not security." `run()` with no argument serves stdio. Tests use `async with Client(server) as client:` in-process: "No subprocess. No port. Nothing on a wire." ([migration](https://py.sdk.modelcontextprotocol.io/migration/), [tools](https://py.sdk.modelcontextprotocol.io/servers/tools/), [testing](https://py.sdk.modelcontextprotocol.io/get-started/testing/)).

## The author's other tools

From their public GitHub pages only.

- [Loupe](https://github.com/mpwilso/loupe): a Claude skill for product managers that "turns meeting notes, tickets and emails into stories a developer can build without a second meeting".
- [Parallax](https://github.com/mpwilso/parallax): a local tool where agents plan, build and check work in a sandbox, and the person makes the calls.
- [ISR](https://github.com/mpwilso/isr): a Claude Code skill that "Writes the acceptance script for an AI-built change: what the build proved, what a person still has to check, and what the business has to decide."
- [Polarizer](https://github.com/mpwilso/polarizer): "A local MCP gateway: it sits between an AI agent and the MCP servers it uses". It pins the tool definitions you approved, holds risky calls for a person, and keeps a hash-chained ledger. Upstream servers are declared in `polarizer.toml` as `[upstream.<name>]` with `command` and `args`, and each tool gets a class such as `local-read`, `local-write` or `destructive`; a tool with no class is held on every call.

## What Mordecai's library adds

Plainly, and only against what was read above:

- **An install gate on measured evidence, checked against the bytes being installed.** The servers and registries above list, read, version or install skills. Speakeasy scores efficacy with a model judge. Tessl displays with-and-without scores. NVIDIA gates publication to its own catalog. None of them refuses an install because a card for that exact version, recomputed from its result by fixed rules in code, says the skill hurts. Mordecai's gate runs on the user's machine, and the user can recheck the card's hashes against the installed folder.
- **Variants with lineage.** A base skill and named variants, each with its own version and changelog, and each variant recording the base version it came from, so a variant that falls behind its base is reported. Speakeasy and systemprompt.io track derivation; the open-source servers don't.
- **A library in plain Git.** Every stored copy is a spec-valid skill folder, and releases are Git tags. The access control is GitHub's.

What it doesn't add: it isn't a general package manager. It installs only skills, only from Mordecai library layouts, and keeps its own lockfile beside npx skills' and APM's.
