# Library demo

A walk-through of the skill library that runs in a few seconds, offline, with no tokens and no model calls. It lists the library, shows history, installs a variant into a temporary project, shows the lockfile, tries a Hurts variant and gets refused, reports a variant behind its base, and exports a Claude Code marketplace.

Every output below is what the commands printed when they were run on 2026-10-06, with the temporary folder's path written as `$DEMO`.

## Setup

```
git clone https://github.com/mpwilso/mordecai
cd mordecai
uv sync --extra library
export MORDECAI_LIBRARY_CONFIG=examples/library.toml
DEMO=$(mktemp -d)
```

[examples/library.toml](../examples/library.toml) has three sources, org, team and personal, all in this repository so the demo needs no network. The library's release tags (`skill/...`) are local Git tags. A clone that doesn't have them still works, but reads every copy at the commit as untagged.

## List

Every skill, every copy, the version install would pick, its verdict and where it came from. `ferry-workflow`'s `qrx` variant is the planted suite 1 skill with its real card (Helps), and `branch-naming`'s `camelcase` is H1's (Hurts). The personal library's `mobile` copy shadows the org's, and is behind the base. The team's `payments` variant is the default for `pr-description`, through `[variants]` in the config.

```
$ uv run mordecai library list
branch-naming
  base                   1.0.0              unmeasured                 org
  variant camelcase      1.0.0              hurts                      org  (based on 1.0.0)
ferry-workflow  (default variant: qrx)
  base                   1.0.0              unmeasured                 org
  variant qrx            1.0.0              helps                      org  (based on 1.0.0)
mordecai
  base                   1.0.0              unmeasured                 org
pr-description  (default variant: payments)
  base                   2.0.0              unmeasured                 org
  variant mobile         0.0.0 (untagged)   unmeasured                 personal  (based on 1.0.0; behind base 2.0.0; shadows org)
  variant payments       1.0.0              unmeasured                 team  (based on 2.0.0)
  variant platform       2.0.0              unmeasured                 org  (based on 2.0.0)
```

## History

The base's releases: each is a tag made by `mordecai library release`, with the changelog notes for it.

```
$ uv run mordecai library history pr-description
pr-description from org
  2.0.0  2026-10-06  skill/pr-description@2.0.0  unmeasured
    - Renamed the sections to Summary, Motivation, Verification and Risk, to match the review checklist. Descriptions written to 1.x headings no longer match.
    - Verification also says what wasn't checked.
  1.2.0  2026-10-06  skill/pr-description@1.2.0  unmeasured
    - Title rules: imperative mood, under 72 characters, no ticket number.
  1.1.0  2026-10-06  skill/pr-description@1.1.0  unmeasured
    - A Risk section: what could break, and how to roll it back.
  1.0.0  2026-10-06  skill/pr-description@1.0.0  unmeasured
    - The organization's pull request template: What, Why and Testing.
```

A variant has its own versions, and each release records the base version it is based on. `platform` was brought up to base 2.0.0 by hand and released as 2.0.0.

```
$ uv run mordecai library history pr-description --variant platform
pr-description.platform from org
  2.0.0  2026-10-06  skill/pr-description.platform@2.0.0  unmeasured  based on base 2.0.0
    - Brought up to base 2.0.0: title rules, and the renamed sections. Rollout and the paging note stay.
  1.1.0  2026-10-06  skill/pr-description.platform@1.1.0  unmeasured  based on base 1.1.0
    - Name the paged team when a change touches an alert.
  1.0.0  2026-10-06  skill/pr-description.platform@1.0.0  unmeasured  based on base 1.1.0
    - Forked from base 1.1.0 for the platform team.
    - A Rollout section: the flag or deploy step, and the dashboard to watch.
```

The org's `mobile` variant, read with the repository's own config (`mordecai-library.toml`) since the personal copy shadows it in the example config. It is still based on base 1.0.0.

```
$ uv run mordecai library history pr-description --variant mobile --config mordecai-library.toml
pr-description.mobile from mordecai
  1.1.0  2026-10-06  skill/pr-description.mobile@1.1.0  unmeasured  based on base 1.0.0
    - Testing also names the devices or simulators used.
  1.0.1  2026-10-06  skill/pr-description.mobile@1.0.1  unmeasured  based on base 1.0.0
    - Screenshots cover any change to what a user sees, not only whole screens.
  1.0.0  2026-10-06  skill/pr-description.mobile@1.0.0  unmeasured  based on base 1.0.0
    - Forked from base 1.0.0 for the mobile team.
    - Testing names the app version and platforms.
    - A Screenshots section for changes to a screen.
```

## Install a variant into a project

With no `--variant`, install takes the config's default, the team's `payments` variant, at its newest release. It writes the folder into both targets and records each one in the project's lockfile.

```
$ uv run mordecai library install pr-description --project $DEMO --target agents --target claude
warning: pr-description (variant payments) 1.0.0 has no card, so nothing says whether it helps.
Installed pr-description (variant payments) 1.0.0 (unmeasured) into .agents/skills/pr-description, .claude/skills/pr-description.
Locked in $DEMO/mordecai-lock.json at commit 7b0cdbdaa1f9.
```

## The lockfile

One entry per installed folder: the source, the release tag, the commit SHA it was read at, the copy's path in the source, the folder hash, and the verdict with its evidence state. No timestamps.

```
$ cat $DEMO/mordecai-lock.json
{
  "installed": {
    ".agents/skills/pr-description": {
      "allowed": [],
      "commit": "7b0cdbdaa1f9261d64f207b7fc693f2ba6e42d72",
      "evidence": "unmeasured",
      "hash": "sha256:4da3fcae45ceea08f8e39ccba90e6cf5aeae3a0d3dc738206fd56b2a286d3fe1",
      "path": "examples/team/library/pr-description/variants/payments/pr-description",
      "skill": "pr-description",
      "source": {
        "library": "examples/team/library",
        "name": "team",
        "path": ".."
      },
      "tag": "skill/pr-description.payments@1.0.0",
      "variant": "payments",
      "verdict": "unmeasured",
      "version": "1.0.0"
    },
    ".claude/skills/pr-description": {
      "allowed": [],
      "commit": "7b0cdbdaa1f9261d64f207b7fc693f2ba6e42d72",
      "evidence": "unmeasured",
      "hash": "sha256:4da3fcae45ceea08f8e39ccba90e6cf5aeae3a0d3dc738206fd56b2a286d3fe1",
      "path": "examples/team/library/pr-description/variants/payments/pr-description",
      "skill": "pr-description",
      "source": {
        "library": "examples/team/library",
        "name": "team",
        "path": ".."
      },
      "tag": "skill/pr-description.payments@1.0.0",
      "variant": "payments",
      "verdict": "unmeasured",
      "version": "1.0.0"
    }
  },
  "lockfileVersion": 1
}
```

## The card verifies against the installed copy

`ferry-workflow` installs its `qrx` variant, which has a current Helps card.

```
$ uv run mordecai library install ferry-workflow --project $DEMO
warning: Claude Code reads skills from .claude/skills, not .agents/skills; install to the claude target too if you use it.
Installed ferry-workflow (variant qrx) 1.0.0 (helps) into .agents/skills/ferry-workflow.
Locked in $DEMO/mordecai-lock.json at commit 9fa950b9a9b0.
```

The installed folder is byte for byte the stored copy, so the engine's own `mordecai check` confirms the card against it: the card was made from the real suite 1 result, on exactly these files.

```
$ uv run mordecai check library/ferry-workflow/variants/qrx/evidence/1.0.0/card.json --skill $DEMO/.agents/skills/ferry-workflow --cases-root evals/planted/1-convention
Current: library/ferry-workflow/variants/qrx/evidence/1.0.0/card.json matches the skill and cases it was measured on.
```

## Try the Hurts variant

The `camelcase` variant's card says Hurts, so the default policy refuses it, and nothing is written. Overriding it takes `--allow hurts`, which the lockfile would record.

```
$ uv run mordecai library install branch-naming --variant camelcase --project $DEMO
Refused: branch-naming (variant camelcase) 1.0.0 is refused: its evidence says hurts. Pass --allow hurts to install it anyway.
```

It exits 1.

## A replacement shows the diff first

Installing another variant into a target that already holds one would replace it. Install prints the diff and changes nothing without `--yes`. `update` works the same way for a newer release.

```
$ uv run mordecai library install pr-description --variant platform --project $DEMO
warning: pr-description (variant platform) 2.0.0 has no card, so nothing says whether it helps.
warning: Claude Code reads skills from .claude/skills, not .agents/skills; install to the claude target too if you use it.
.agents/skills/pr-description would change:
  --- a/.agents/skills/pr-description/SKILL.md
  +++ b/.agents/skills/pr-description/SKILL.md
  @@ -2,8 +2,8 @@
   name: pr-description
   description: Use when writing or editing the description of a pull request in one of this organization's repositories.
   metadata:
  -  mordecai-version: "1.0.0"
  -  mordecai-variant: "payments"
  +  mordecai-version: "2.0.0"
  +  mordecai-variant: "platform"
     mordecai-based-on: "pr-description@2.0.0"
   ---
   
  @@ -17,7 +17,8 @@
   - **Motivation**: the problem it solves, with a link to the ticket.
   - **Verification**: how you checked that it works, and what you didn't check.
   - **Risk**: what could break, and how to roll it back.
  -- **Money**: any change to how amounts are calculated, rounded, stored or shown, with an
  -  example amount before and after.
  +- **Rollout**: the feature flag or deploy step that turns it on, and the dashboard to watch.
  +
  +If the change adds, removes or changes an alert, name the team that is paged by it.
   
   Keep the whole description under 200 words, and don't paste the diff.
That would replace an installed copy. Run again with --yes to apply.
```

It exits 1.

## The behind-base report

`status` lists everything worth acting on: copies with no card, a refused copy, a shadowed copy, and the `mobile` variant that is based on base 1.0.0 while the base is at 2.0.0. It never merges anything. It exits 1 when it reports something, so it can run in CI.

```
$ uv run mordecai library status --project $DEMO
unmeasured       branch-naming (base) 1.0.0 has no card
blocked          branch-naming (variant camelcase) 1.0.0 can't be installed: hurts
unmeasured       ferry-workflow (base) 1.0.0 has no card
unmeasured       mordecai (base) 1.0.0 has no card
unmeasured       pr-description (base) 2.0.0 has no card
shadowed         pr-description (variant mobile) from 'personal' shadows the copy in 'org'
behind-base      pr-description (variant mobile) is based on base 1.0.0; the base is at 2.0.0
unmeasured       pr-description (variant mobile) 0.0.0 has no card
unmeasured       pr-description (variant payments) 1.0.0 has no card
unmeasured       pr-description (variant platform) 2.0.0 has no card
```

It exits 1.

## The marketplace export

The resolved copies, one plugin per skill, as a Claude Code plugin marketplace. The refused `camelcase` variant isn't among them: export applies the same policy as install.

```
$ uv run mordecai library export --marketplace $DEMO/marketplace --name example-org-skills --owner "Example Org"
  branch-naming        base         1.0.0    unmeasured
  ferry-workflow       qrx          1.0.0    helps
  mordecai             base         1.0.0    unmeasured
  pr-description       payments     1.0.0    unmeasured
Wrote 4 skill(s) to $DEMO/marketplace.
```

[examples/managed-settings.json](../examples/managed-settings.json) restricts Claude Code to this marketplace and installs each plugin, once the folder is committed to a repository. The install policy, the precedence rule and the lineage report all ran on the user's machine, from Git, with no model and no network.

```
$ cat $DEMO/marketplace/.claude-plugin/marketplace.json
{
  "name": "example-org-skills",
  "owner": {
    "name": "Example Org"
  },
  "description": "Skills exported from a Mordecai library, with each version's verdict.",
  "plugins": [
    {
      "name": "branch-naming",
      "source": "./plugins/branch-naming",
      "description": "Use when naming a git branch for work tracked in this team's ticket system. (Mordecai: unmeasured, branch-naming 1.0.0)",
      "version": "1.0.0"
    },
    {
      "name": "ferry-workflow",
      "source": "./plugins/ferry-workflow",
      "description": "Use when naming a git branch or writing a pull request description for work tracked in this team's ticket system. (Mordecai: helps, ferry-workflow.qrx 1.0.0)",
      "version": "1.0.0"
    },
    {
      "name": "mordecai",
      "source": "./plugins/mordecai",
      "description": "Use when the user asks whether a skill measurably helps, wants a Mordecai card read or checked, or wants to list or install skills from a Mordecai skill library. (Mordecai: unmeasured, mordecai 1.0.0)",
      "version": "1.0.0"
    },
    {
      "name": "pr-description",
      "source": "./plugins/pr-description",
      "description": "Use when writing or editing the description of a pull request in one of this organization's repositories. (Mordecai: unmeasured, pr-description.payments 1.0.0)",
      "version": "1.0.0"
    }
  ]
}
```

## What wasn't shown

- **The MCP server.** `mordecai mcp` serves the same list, search, read, history, update check, install and uninstall operations over stdio; see the README for each tool's setup. Its tests drive it with the SDK's in-process client.
- **GitHub sources.** A source can be `github = "owner/repo"`, fetched with Git over HTTPS into a cache. The tests use a local stand-in, so nothing here reached the network.
- **A real managed Claude Code install** of the exported marketplace. The settings keys are from the Claude Code docs; the file hasn't been tried against a managed install.
