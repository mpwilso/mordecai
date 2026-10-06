# Examples

- [library.toml](library.toml): a config with three sources (org, team, personal) that shows which copy wins when the same skill is in more than one. All three point at this repository, so it works offline: the org is [library/](../library/), the team is [team/library/](team/library/), and the person is [personal/library/](personal/library/).
- [managed-settings.json](managed-settings.json): Claude Code managed settings for an organization that hosts the output of `mordecai library export --marketplace` as a GitHub repository.

[docs/library-demo.md](../docs/library-demo.md) runs both.

## What the three sources resolve to

| Copy | Comes from | Why |
|---|---|---|
| `pr-description` base | org | only the org has a base |
| `pr-description` variant `platform` | org | only the org has it |
| `pr-description` variant `mobile` | personal | the org and the person both have it; the person is listed last |
| `pr-description` variant `payments` | team | only the team has it, and `[variants]` makes it the default |
| `ferry-workflow` variant `qrx` | org | the default, through `[variants]`; measured Helps |
| `branch-naming` variant `camelcase` | org | measured Hurts, so install refuses it |

The team's `payments` variant is released (tag `skill/pr-description.payments@1.0.0`). The personal `mobile` copy is committed but not released, the way a personal library often is, so it installs as untagged, with a warning.

## The managed settings

The organization runs `mordecai library export --marketplace <dir> --name example-org-skills --owner "Example Org"`, commits `<dir>` to a repository (here `example-org/skills-marketplace`, a placeholder), and puts this file where Claude Code reads managed settings, for example `/etc/claude-code/managed-settings.json` on Linux.

- `strictKnownMarketplaces` lets users add only this marketplace. It registers nothing by itself.
- `extraKnownMarketplaces` registers it under the name the export used, and keeps it up to date.
- `enabledPlugins` installs each exported skill for everyone. Setting one to `false` in managed settings blocks it at every scope.

Each plugin is one skill, named after it, holding the copy the library resolved, at its newest release, byte for byte. A copy the install policy refuses is left out of the export, so a Hurts variant never reaches the marketplace. The key names and shapes are from the Claude Code [settings reference](https://code.claude.com/docs/en/settings-reference) as read on 2026-10-06; this file hasn't been tried against a managed Claude Code install.
