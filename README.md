<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/lockup-dark.svg">
    <img src="docs/brand/lockup-light.svg" alt="Mordecai: a potion flask on a round badge, filled above a dashed line across the bulb" height="72">
  </picture>
</p>

<p align="center"><b>Reads a skill's eval results and says what the skill can honestly claim.</b></p>

<p align="center"><a href="https://github.com/mpwilso/mordecai/actions/workflows/ci.yml"><img src="https://github.com/mpwilso/mordecai/actions/workflows/ci.yml/badge.svg" alt="CI status"></a></p>

Status: A portfolio project, built to show how I design, test and judge an AI tool. Version 0.3.0. Its verdict rules have been checked on simulated skills and on 12 planted skill suites with real eval runs, almost all on one small model (Claude Haiku 4.5). Only the first set of five skills and two sealed holdouts were blind; on that first set, 3 of 5 got their predicted verdict. The later suites were designed after seeing those results. Every result is in [docs/planted-skills-results.md](docs/planted-skills-results.md), including the misses.

Mordecai is for teams that share Claude skills. Claude Code already runs a skill's test cases with and without the skill (`claude plugin eval`). Mordecai reads that result and decides what the skill can honestly claim: it helps, it hurts, the model already handles it, or there isn't enough to tell. The card it writes is tied to the exact skill, cases and model it was measured on, so a team can see when a claim has gone stale.

0.3.0 adds a [skill library](#the-skill-library): skills kept in Git, each with a base and named variants, each version with its own history and, when it has been measured, its card. Install copies a skill into the folder your AI coding tool reads and refuses a version whose card says it hurts.

It sits beside [Loupe](https://github.com/mpwilso/loupe), [Parallax](https://github.com/mpwilso/parallax), [ISR](https://github.com/mpwilso/isr) and [Polarizer](https://github.com/mpwilso/polarizer), and has no dependency on any of them.

Jump to [the skill library](#the-skill-library), [an example card](#what-a-card-looks-like), [the verdicts](#the-verdicts), [crawl mode](#crawl-mode), [how it was tested](#how-it-was-tested), [the limits](#known-limits) or [setup](#setup).

## The skill library

0.3.0 adds a way to share skills with that evidence attached. A library is a folder of skills in a Git repository. `mordecai library` installs a skill from it into the folder your AI coding tool reads, records where it came from, and refuses a version whose card says it hurts. `mordecai mcp` offers the same operations to MCP clients. It works for one person with a personal library, and for an organization with base skills and team variants. The design is in [docs/library-design.md](docs/library-design.md), the research behind it in [docs/research.md](docs/research.md), and the choices made along the way in [docs/decisions.md](docs/decisions.md).

### Base and variants

Each skill has a base and any number of named variants, and each of those copies is a plain skill folder that passes the Agent Skills spec's reference validator (`skills-ref validate`) on its own:

```
library/pr-description/base/pr-description/SKILL.md
library/pr-description/base/CHANGELOG.md
library/pr-description/variants/mobile/pr-description/SKILL.md
library/pr-description/variants/mobile/CHANGELOG.md
library/pr-description/variants/mobile/evidence/1.1.0/card.json    (when it has been measured)
```

The spec says a skill's `name` must match its folder, so every copy's folder is named after the skill, whichever variant it is. An installed skill always has that name, and a project has one variant of it at a time. Install copies the inner folder byte for byte, so the card's skill hash verifies against the installed copy with `mordecai check`.

### Versions and history

The base and each variant have their own semver version and `CHANGELOG.md`. `mordecai library release <skill> [--variant V] --bump patch|minor|major` moves the changelog's Unreleased notes under a new version, commits the copy, and creates a local annotated tag: `skill/<skill>@X.Y.Z` for a base, `skill/<skill>.<variant>@X.Y.Z` for a variant. It never pushes. The `skill/` prefix keeps these tags out of `v*` release triggers. History (`mordecai library history`) is the tags plus the changelog.

Each variant records the base version it was forked from (`mordecai library fork`) or last brought up to. `mordecai library status` reports a variant that is behind its base's newest release. It never merges: a variant is someone's deliberate change.

### Sources and precedence

A config file (`mordecai-library.toml`) lists sources, each a GitHub repository or a local folder, with an optional ref. For each copy of a skill (its base, or one named variant), the source listed last wins. List them broad to narrow, org then team then personal, and a team can add a variant of an org skill, or a person replace one, without copying the rest. Shadowed copies are reported, never installed and never merged. [examples/library.toml](examples/library.toml) shows all three. Who may change a library is decided by GitHub: repository permissions, CODEOWNERS and branch rules.

Every Git source is read at a commit, from Git's objects, never from a working tree, and every install records that commit. A private repository is read with a token from `MORDECAI_GITHUB_TOKEN` (or `GITHUB_TOKEN`), passed to Git in its environment, never read from the config, never written to the lockfile and never printed.

### Verdicts gate installs

A version can carry a card and the eval result it was made from, beside it in `evidence/<version>/`. The library never trusts the verdict written in the card: it checks that the result is the one the card was made from, reruns the verdict rules on it, and checks that the card's skill hash equals the hash of that version's files. Listing shows the verdict, or one of these: unmeasured (no card), stale (a card for other files), or broken (a card that doesn't match its result).

Install refuses Hurts, Invalid and broken by default, and warns on stale and unmeasured. `--allow hurts` overrides one refusal, at the command line only, and the lockfile records it.

In the seeded library, two variants carry real cards from the planted check. Their skill folders are byte for byte the planted skills, their result files are the recorded results with local paths made relative (each evidence folder's NOTE.md gives the original hash), and their cards were made from them with `mordecai identify`:

| Copy | Planted suite | Card | Install |
|---|---|---|---|
| `ferry-workflow` variant `qrx` | 1, a made-up convention | Helps (+100) | installs |
| `branch-naming` variant `camelcase` | H1, a convention that conflicts with the graders | Hurts (-100) | refused |

The rest of the seeded library (an org skill, `pr-description`, with a `platform` and a `mobile` variant, several releases each, `mobile` behind its base) is unmeasured, and says so.

### Install, update and the lockfile

```
uv run mordecai library install <skill> [--variant V] [--version X.Y.Z] [--target agents|claude|github|cursor|PATH]...
uv run mordecai library update [<skill>] [--yes]
uv run mordecai library uninstall <skill>
```

- `agents` (`.agents/skills/`, read by Codex, Cursor and Copilot) is the default target. Claude Code's docs list `.claude/skills/` and not `.agents/skills/`, so add `--target claude` for it. `--user` installs under your home folder instead.
- `mordecai-lock.json` in the project records each installed folder's source, ref, commit, tag, version, folder hash and verdict.
- `update` prints a diff of every change and replaces nothing without `--yes`. Installing a different variant over an installed one works the same way.
- Mordecai never replaces or removes a folder it didn't install, or one that changed since it did.
- It never runs a skill's scripts. But a skill's scripts run with your permissions when your AI tool uses them, so install says when a skill has any. Read them first.

**Why install rather than serve.** Claude Code, Codex, Cursor and Copilot all read each installed skill's name and description up front, and load the rest when the description matches the task. That is how a skill fires, and how it was measured. A skill served over MCP reaches the model only if the model first decides to call a tool. So install is the main path, and reading a skill over MCP is the fallback for clients without native skills.

### Enterprise: export a marketplace

```
uv run mordecai library export --marketplace <dir> --name <marketplace> --owner "<org>"
```

This writes the resolved library as a Claude Code plugin marketplace: one plugin per skill, holding the copy install would pick, byte for byte, with its verdict in the description. Refused copies are left out. An organization commits the folder to a repository, and its managed settings restrict users to that marketplace (`strictKnownMarketplaces`), register it (`extraKnownMarketplaces`) and install each plugin for everyone (`enabledPlugins`). [examples/managed-settings.json](examples/managed-settings.json) is an example, explained in [examples/README.md](examples/README.md).

`export --skills <dir>` writes the same copies as plain `<skill>/` folders, the layout npx skills and APM read. An export goes to tools that don't run Mordecai's gate, so it always leaves out Hurts, Invalid and broken copies, whatever the config's policy says. To publish your own library, run `uv run mordecai library export --skills skills` in it, with `[export] skills` in its `mordecai-library.toml` listing what to publish.

This repository publishes only one skill at its root, in [skills/](skills/): `mordecai`, which tells an agent how to run Mordecai. The seeded library is demo content (made-up conventions, and one deliberately harmful variant), so none of it is published. Something has to be in `skills/`, though: with nothing there, `npx skills add mpwilso/mordecai` would search the whole repository and could install any of its same-named copies.

### Library setup

```
uv sync --extra library
uv run mordecai library list
```

To install into another project, run it from there with `uv run --project /path/to/mordecai mordecai library install <skill>`, or pass `--project`.

**The MCP server.** `mordecai mcp` is a stdio server with seven tools: `list_skills`, `search_skills`, `get_skill`, `skill_history`, `check_updates`, `install_skill` and `uninstall_skill`. The last two change files: they write only inside the targets the config's `[install] targets` allows, they're marked destructive so a client can ask you first, they can't override the install policy, and replacing an installed copy takes a second call after the diff. No tool writes to GitHub. The server reads the config from the folder it is started in (the project), and installs into that project unless you pass `--project`. `get_skill` returns skill text written by someone else, and a model may treat that text as instructions; that is one reason installing goes through the gate, and reading a skill over MCP is only the fallback. Errors name no local folders.

None of these snippets has been run against its client. Each follows the client's own docs as read on 2026-10-06; the parts marked unverified weren't stated there.

Claude Code ([docs](https://code.claude.com/docs/en/mcp)) reads a project's `.mcp.json`, the file `claude mcp add --scope project` writes, and asks before it starts a server from one. This repository has one, [.mcp.json](.mcp.json): it serves this repository's library, and installs into a gitignored `.mcp-demo/` folder (or `$MORDECAI_MCP_PROJECT`), so you can try it without touching your user config. Run `uv sync --extra library`, start Claude Code in the repository, approve the `mordecai` server, and check `/mcp` shows it connected. For your own project, put this in its `.mcp.json`. Unverified: that Claude Code starts the server in the project folder.

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

### The demo

[docs/library-demo.md](docs/library-demo.md) runs in a few seconds with no tokens and no model: it lists the library, shows history, installs a variant into a temporary project, shows the lockfile, tries the Hurts variant and gets refused, reports the variant behind its base, and exports a marketplace. Every output in it is from a real run.

### How it relates to the author's other tools

Mordecai has no dependency on any of them.

- [Loupe](https://github.com/mpwilso/loupe) and [ISR](https://github.com/mpwilso/isr) are skills. A team could keep them in a Mordecai library and measure them; neither is in the seeded library.
- [Parallax](https://github.com/mpwilso/parallax) runs agents that plan, build and check work in a sandbox. It doesn't install skills, and Mordecai doesn't run agents.
- [Polarizer](https://github.com/mpwilso/polarizer) is a local MCP gateway that pins tool definitions, holds risky calls for a person and keeps a verifiable ledger. It can sit in front of `mordecai mcp`, as above.

### Limits of the library

- **The MCP server never writes to GitHub,** and nothing in Mordecai does yet. Releases are local tags, and pushing them is up to you. There is no GitHub Action yet that posts a card on a library pull request.
- **Cards are only as good as their cases.** A Helps card says the skill helped on those cases, with that model. See [the verdicts](#the-verdicts) and [known limits](#known-limits).
- **The gate trusts committed result files.** It checks that a card matches its result and its version's files, but not that the eval really ran. Someone who writes a fake result and makes a card from it passes the gate.
- **Precedence is by rule, not merge.** The last source listed wins for each copy. Two copies are never combined, and a variant behind its base is reported, not updated.
- **The client snippets are unverified** where marked, and none has been run against its client.
- **Version stamps in frontmatter are optional.** The changelog is the record of versions and lineage. A skill measured before it joined the library, like the planted suites, can't carry stamps without changing the bytes its card measured. [docs/decisions.md](docs/decisions.md) has the reasoning.
- **Mordecai isn't a general package manager.** It installs only skills, only from Mordecai library layouts, and keeps its own lockfile. It never reads or writes npx skills' or APM's lockfiles or folders, and coexists with both. If npx skills replaces a folder Mordecai installed, Mordecai reports it rather than acting on it.
- **The release tags in this repository are local** until they're pushed. A clone without them reads every copy as untagged.
- **The Hurts example is deliberately harmful.** `branch-naming`'s `camelcase` variant is planted suite H1, built so the repository's own checks fail; it is never published, and every export refuses it.
- **`npx skills add --full-depth` searches the whole repository,** including the planted suites, several of which are deliberately harmful skills. Don't use it on this repository; `skills/` is the only part meant to be installed that way.
- **Tested offline only.** Fetching from GitHub was tested against a local Git repository standing in for github.com, never against github.com itself, and the exported marketplace hasn't been tried in a managed Claude Code install.

## Why it exists

Many skills don't measurably help, and the usual tools don't flag it:

- In SWE-Skills-Bench, 39 of 49 skills gave no gain in pass rate, and 24 of them passed every task without the skill. Token use moved between -78% and +451% with the results unchanged.
- In SkillsBench, skills written by people added about 16 points on average, skills written by models about -1, and 16 of 84 tasks did worse with a skill.
- `claude plugin eval` reports the change with and without a plugin, but its docs say "the with-minus-without delta is reported but never changes the exit code" ([Run evals in CI](https://code.claude.com/docs/en/plugin-evals#run-evals-in-ci)). The exit code depends on each case's score with the plugin against `--threshold`, so a skill that passes everything with or without it passes the gate. The same docs say a run that hits a usage or rate limit "usually scores 0", and the suite "isn't marked `partial`" ([Runs fail with a usage-limit or rate-limit error partway through](https://code.claude.com/docs/en/plugin-evals#runs-fail-with-a-usage-limit-or-rate-limit-error-partway-through)).

## What a card looks like

This is suite 1 from the planted check, a made-up branch and pull request convention that Claude Haiku 4.5 can't know without the skill, printed by `mordecai identify` from its real eval result ([recorded card](docs/planted-results/1-convention.card.json)).

```
$ uv run mordecai identify tests/fixtures/suite1-result.json --skill evals/planted/1-convention
planted-convention 1.0.0: Helps
The skill raised the score: 90% interval +100 to +100 points.

  With 100% · Without 0% · Change +100 pts (90% interval +100 to +100)
  Cases 9: 9 better, 0 same, 0 worse
  Fired in 27 of 27 runs that needed it, fired in 0 of 9 runs that didn't
  Cost per run $0.019 with, $0.025 without (-23%) · Turns 3.0 with, 2.0 without
  Tested on claude-haiku-4-5-20251001 · judge claude-haiku-4-5-20251001 · Claude Code 2.1.289 · 2026-10-05
  Skill sha256:f35f631cd4d5 · Cases sha256:417d28c8319e · Result sha256:d704ea283576

Next: Keep it.
```

The fixture is the raw result with local paths replaced, so its result hash differs from the one in the recorded card (`sha256:06cf8a473864`). The verdict, the numbers and the other two hashes are the same.

The second example shows that one case is not evidence. It's a one-case eval of a tiny skill, run once while building Mordecai to capture the result format ([tests/fixtures/probe-result.json](tests/fixtures/probe-result.json), skill and case in [tests/fixtures/probe/](tests/fixtures/probe/)). The skill went from 0% to 100%, and the card still won't call it Helps. Its warnings are cut here.

```
$ uv run mordecai identify tests/fixtures/probe-result.json --skill tests/fixtures/probe
schema-probe 0.0.1: Inconclusive
Only 1 case(s) were compared; the rules need at least 5.

  With 100% · Without 0% · Change +100 pts
  Cases 1: 1 better, 0 same, 0 worse
  Fired in 2 of 2 runs that needed it
  Cost per run $0.019 with, $0.015 without (+23%) · Turns 3.0 with, 1.0 without
  Tested on haiku · judge haiku · Claude Code 2.1.289 · 2026-10-05
  Skill sha256:c9b400d7538f · Cases sha256:a5b22319b5ee · Result sha256:997d5873c70a
```

## The verdicts

Code decides, not a model. The rules run in this order, and the first one that applies wins. They're written out in [src/mordecai/verdict.py](src/mordecai/verdict.py).

| Verdict | When |
|---|---|
| Invalid | The eval stopped early, a run hit a usage or rate limit, judge graders were skipped, or nothing ran without the skill |
| Never fired | The skill didn't fire in any run where it should have |
| Inconclusive | Fewer than 5 cases were compared |
| Hurts | The whole 90% interval for the change is below zero |
| Helps | The whole interval is above zero, and the change is at least 10 points |
| Already handled | The model scores at least 90% without the skill, and the interval rules out both a 10-point gain and a 10-point loss |
| Inconclusive | The model scores at least 90% without the skill, but the interval doesn't rule out a 10-point loss |
| No effect | The interval stays inside plus or minus 10 points |
| Inconclusive | Anything else: the interval is too wide to call |

The interval is a bootstrap over cases, and over runs inside each case, with a fixed seed, so the same result always gives the same card. Cases that check the skill stays quiet are left out of the change and reported as misfires.

Every card also lists warnings that don't change the verdict: a model alias instead of a pinned ID, fewer than 3 runs per side, no case that checks the skill stays quiet, no case that checks it fired, and case prompts that name the skill (which tests whether the model follows an instruction, not whether it finds the skill). `mordecai lint` runs the same checks on case files before an eval.

**The two Already handled rows changed in 0.2.0.** Under the original rules, Already handled only checked that the interval ruled out a 10-point gain. In the planted check, that hid harm. An outdated skill (suite 3) gave the wrong answer in 5 of the 6 runs where it fired, and the card still said Already handled, with an interval of -41 to +7. The rules never flagged that skill as Hurts, and the new rules don't either, because its interval reaches +7. They now call it Inconclusive. The change was designed after seeing that result, so suite 3 can't count as evidence for it. Of the seven cards recorded before the change, it moves only suite 3.

## Crawl mode

`--crawl`, or `MORDECAI_MODE=crawl`, prints the same card as loot, in honor of Matt Dinniman's *Dungeon Crawler Carl*. Helps is ENCHANTED, Hurts is CURSED, Already handled is VENDOR TRASH, and Mordecai has opinions. On a terminal, the box opens first.

<p align="center"><img src="docs/brand/crawl-card.svg" alt="Crawl mode: a pixel treasure chest shakes, opens and lifts out a red potion, beside the card mordecai identify --crawl prints for a demo skill that helps" width="900"></p>

<p align="center"><sub>A demo skill with simulated results. The text is printed by the same code as the command.</sub></p>

The jokes come from fixed templates around the plain card's stat block. They can't change a number or a verdict, and a test checks that every number in crawl mode is also in plain mode.

Crawl mode is a fan nod. It isn't affiliated with or endorsed by the author or publisher, and its text is original.

## How it was tested

### Planted skills, run for real

Each planted skill has a known intended effect, and every prediction was committed before its suite ran. **Only some of the suites were blind.** The first set of five skills and the two sealed holdouts were written and predicted before any result existed: their predictions are in commit bd92b23 ([docs/planted-skills.md](docs/planted-skills.md)), and the first results start at commit 15da64f. Everything after that (V1, V2, V3, H1 and both Sonnet reruns) was designed or predicted after seeing earlier results. Each suite has 12 cases: 9 compared, and 3 where the skill should stay quiet. Every suite ran with 3 runs per side and regex or tool-use graders only. Details, cards and costs are in [docs/planted-skills-results.md](docs/planted-skills-results.md).

**First set, 0.1.0 rules, Claude Haiku 4.5: 3 of 5 skills got their predicted verdict.** The criterion written in advance was that every suite gets its predicted outcome, so the check as a whole failed.

| Suite | Predicted | Actual | |
|---|---|---|---|
| 1. A made-up convention | Helps | Helps (+100) | Match |
| 2. Conventional Commits | Already handled | Helps (+78) | Miss. Haiku rarely uses the format unprompted (5 of 27 runs), so the premise was wrong |
| 3. An outdated rule | Hurts | Already handled (-15) | Miss. The skill fired in 6 of 27 runs; see the verdicts section |
| 4. A vague description | Never fired | Never fired | Match |
| 5a. A twin placebo | Not Helps or Hurts | Already handled | Match. Every run agreed, so there was no noise to misread |
| 5b. A filler placebo | Not Helps or Hurts | No effect | Match. Every run agreed |

**Later suites, 0.2.0 rules, frozen at 64a7701.** V1, V2, V3 and H1 were written after the first results, so they are not blind. Holdouts 6 and 7 were written with the first set, before any result, and each ran once.

| Suite | Predicted | Actual | |
|---|---|---|---|
| V1. An outdated rule meant to fire | Hurts | Inconclusive (-11) | Miss. The skill fired in 1 of 27 runs |
| V2. Meant as a noisy placebo | Not Helps or Hurts | Hurts (-37) | Design defect. Its text ("Say what changed in plain words") changed behavior, and the rules read that real effect correctly |
| V3. An inert placebo on V2's cases | Not Helps or Hurts | Inconclusive (-11, interval -33 to +11) | Match. It fired in 27 of 27 runs, on noisy runs |
| Holdout 6. A made-up changelog format | Helps | Helps (+100) | Match |
| Holdout 7. A filler placebo | Not Helps or Hurts | No effect | Match, but weak evidence: its baseline was 0%, so it could only have shown a false gain, and its text isn't inert |
| H1. A made-up convention that conflicts with the graders | Hurts | Hurts (-100) | Match. It fired in 27 of 27 runs. Designed after seeing results, so that the skill would fire |

What these show:

- **No placebo has been called Helps or Hurts, but only one placebo ran on noisy runs.** That was V3, which was not blind. Its skill fired every time, its runs disagreed often (all 3 runs agreed in 16 of 24 case-and-side cells), and its card said Inconclusive. The other placebos (5a, 5b and holdout 7) had no noise to misread. V2's Hurts was a real effect from an instruction in its text, not a false call.
- **Hurts was detected once, and it depends on the skill being opened.** The only Hurts on a harmful skill was H1, a suite designed after seeing results so that its skill would fire in every run. When a harmful skill fired in 6 of 27 runs (suite 3, blind) or 1 of 27 (V1), the rules didn't call Hurts. Those cards said Already handled and Inconclusive. This doesn't show that Hurts detection is reliable.
- **Real runs were much less noisy than the simulation assumed.** In the first set, all 3 runs of a side agreed in 94% of case-and-side cells.

Total cost of the planted runs: $20.60 at list price, across 15 runs, one of them a $0.25 pilot.

### Model comparisons

Two suites were rerun on Claude Sonnet 5.5 (`claude-sonnet-5-5`). Neither verdict moved, so no drift was caught. The first rerun had no written prediction; the second was predicted after seeing the Haiku card. Suite 1 stayed Helps (+100 on both models). Suite 2 stayed Helps, but its baseline went down, not up: Sonnet used a Conventional Commits prefix unprompted in 0 of 27 runs, against Haiku's 5. The change grew from +78 to +100. Both cards in each pair match the same skill and case files, so only the model tells them apart. `mordecai check --model` reports that difference in the record (see [setup](#setup)). It doesn't show that a verdict changed.

### Simulation

[docs/simulation.md](docs/simulation.md) runs the rules on simulated skills with a known effect, 200 suites per row. The first simulation treated every run as an independent coin flip, which makes 3 runs agree only about a third of the time. Real runs agreed 94% of the time, so that assumption didn't match. Rerun at 94% agreement:

- **A placebo was called Helps or Hurts in 0% of suites**, against up to 4% with coin flips.
- **A skill worth +20 points was called Helps in 13%, 36% and 56% of suites at 5, 10 and 15 cases.** That's almost the same as with coin flips (14%, 35% and 52%). The remaining uncertainty is between cases, not between runs: a +20 point skill changes the outcome of only some cases. In simulation, a moderate effect needs well over 15 cases to be called reliably. **This finding hasn't been tested on real runs:** no planted skill had a moderate effect.
- **A skill worth +40 points was called Helps in 80% of suites at 10 cases and 96% at 15.**

### Unit tests

Each verdict and warning has a test on a constructed result, along with hashing, staleness, relative card paths, `lint`, `check --model` and the command line. Others feed in hostile input: malformed results and cards, paths and links that lead outside the plugin, and names carrying terminal escapes or Markdown. One test is built from the real suite 3 result, and others check that the README's example cards are what the tool prints. The library's tests cover every command, including hostile sources and targets (path traversal, links, malformed frontmatter, a name that doesn't match its folder, a card that doesn't match its version's files or its result), the byte-for-byte install, the seeded library, and the MCP server through the SDK's in-process client and over stdio. `uv run pytest` runs 157 tests without the library extra (its seven test files skip), and 277 with it (`uv sync --extra library --group spec`). None call a model or reach the network. CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the tests, lint, the format check, `scripts/brand.py --check` and `scripts/planted.py --check` on Python 3.11, 3.12 and 3.13, on every push and pull request, and runs the tests again with the library extra. Live eval runs are never part of CI: they call a model and cost money, and CI has no secrets. The result format comes from a real `claude plugin eval` run, not from the docs alone.

### What wasn't checked

- **Other models.** Everything ran on Claude Haiku 4.5, except two suites rerun on Claude Sonnet 5.5.
- **Judge-graded suites.** Every grader was a regex or a tool-use check, so judge disagreement was never in play.
- **Skills with a moderate real effect,** somewhere around +10 to +30 points. The changes measured on the planted cards were -100, -37, -15, -11, 0, +78 and +100.
- **A harmful skill that fires in some runs but not others.** The rules gave Already handled (0.1.0) or Inconclusive (0.2.0) in those cases, and there is no verdict for it.
- **Domains other than git workflow and Python project setup.**
- **Invalid and partial results from real runs.** No real run hit a cost cap or a rate limit, so those paths are tested only on constructed results.
- **Using `--fail-on` as a CI gate on a real repository.**

## Known limits

- **Hurts needs the skill to be opened.** A harmful skill that fires rarely gets Inconclusive, or Already handled under the 0.1.0 rules, not Hurts. Check the card's "Fired in" line.
- **A skill that rarely fires is reported as Inconclusive.** V1's skill fired in 1 of 27 runs, and its card says Inconclusive, the same word used for a wide interval. A fix is proposed in [docs/open-questions.md](docs/open-questions.md): a Rarely fired verdict under a 10% fire rate, and a warning under 50%. It isn't applied.
- **The bootstrap is optimistic when runs agree.** In 8 of the 13 planted cards that have an interval, it collapsed to a single point, such as +100 to +100.
- **Results come from one small model.** See [what wasn't checked](#what-wasnt-checked).
- **Only one plugin per result.** Cards name the first plugin in the suite.
- **Cost, not tokens.** The eval result reports each run's estimated cost at list price, not its tokens, so that's what the card compares.
- **Links aren't followed.** A symbolic link in a skill is hashed as the path it points to, never opened, so a card doesn't go stale when the linked file's contents change. This keeps a skill under review from making Mordecai read files outside it.

## Setup

Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/mpwilso/mordecai
cd mordecai
uv sync
```

`uv sync` is enough for `identify`, `check` and `lint`, which use only the standard library. The skill library and its MCP server need `uv sync --extra library`; see [its setup](#library-setup).

Check your cases, run your skill's eval with a pinned model, then read it:

```
uv run mordecai lint path/to/plugin
claude plugin eval path/to/plugin --trust-plugin --model claude-sonnet-5-5 --json result.json --no-publish --max-cost-usd 5
uv run mordecai identify result.json --skill path/to/plugin --card card.json --markdown card.md
uv run mordecai check card.json --model claude-sonnet-5-5
```

**`claude plugin eval` runs the plugin's code on your machine, as you.** Under `--json` it can't ask whether you trust the plugin directory, so it refuses to run unless you pass `--trust-plugin` or have already trusted the directory. Only pass it for a plugin you've reviewed and would run yourself. Mordecai itself never runs a plugin: it reads the result file and hashes the plugin's files.

- `lint` exits 1 if the case files would get any warning.
- `identify` prints the card, and can write it as JSON and as Markdown for a pull request. `--fail-on hurts,invalid` makes it exit 1 on those verdicts, for CI. `--crawl` or `MORDECAI_MODE=crawl` prints crawl mode, and `--plain` overrides the variable.
- `check` exits 1 when the skill or its cases have changed since the card was written. With `--model`, it also exits 1 when the card was measured on a different model.
- Every command exits 2 when it can't read its input or won't use it, with one line saying why.

Cards store paths relative to where the card is written, so a card still checks after the repository is cloned somewhere else. Run Mordecai from the repository root: it reads only inside the current directory and directories you pass with `--skill` or `--cases-root`, since a result or card may come from someone else.

A worked example from the planted check: suite 2's Haiku card still matches its files, but it is stale for Sonnet.

```
$ uv run mordecai check docs/planted-results/2-commits.card.json --model claude-sonnet-5-5
Stale: docs/planted-results/2-commits.card.json
  - The card was measured on claude-haiku-4-5-20251001, not claude-sonnet-5-5.
```

## What's next

1. A way to report a skill that rarely fires, distinct from Inconclusive (see [known limits](#known-limits)).
2. A planted skill with a moderate effect, to check the simulation's +20 point finding on real runs.
3. `mordecai measure`: run the eval with a pinned model and a cost cap, then write the card, in one step.

## Prior art

- [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) runs the cases, both arms and the graders. Mordecai only reads its result.
- [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) and [SkillsBench](https://arxiv.org/abs/2602.12670) measured how often skills help, with and without.
- [NVIDIA SkillEvaluator](https://developer.nvidia.com/blog/evaluating-ai-agent-skill-performance-with-nvidia-skillevaluator/) reports a with-minus-without "skill lift", and says it doesn't report confidence intervals. NVIDIA's [skills catalog](https://docs.nvidia.com/skills/evaluating-agent-skills) gates publication on a with-and-without eval, and [Tessl's registry](https://tessl.io/blog/introducing-task-evals-measure-whether-your-skills-actually-work/) shows with-and-without scores for each version.
- [npx skills](https://github.com/vercel-labs/skills) and [APM](https://github.com/microsoft/apm) install skills with lockfiles. Mordecai's library coexists with both and doesn't replace them.
- Skill MCP servers such as [agentskills-mcp](https://github.com/pinkpixel-dev/agentskills-mcp) and [tiger-skills-mcp-server](https://github.com/timescale/tiger-skills-mcp-server) list, read and install skills, and registries such as [Speakeasy's](https://www.speakeasy.com/docs/ai-control-plane/mcp-gateway/skills) track versions and drift. None of those gates an install on a measured result for that version's files. [docs/research.md](docs/research.md) has the comparison.

## License

MIT. See [LICENSE](LICENSE).
