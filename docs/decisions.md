# Decisions

Reversible decisions made during the library build, each with the options considered, the reason, and how to reverse it. Questions that need the author's judgment are in [decisions-for-matt.md](decisions-for-matt.md).

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
