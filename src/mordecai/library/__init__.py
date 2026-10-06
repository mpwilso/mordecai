"""The skill library: skills kept in Git as plain skill folders, each with a base and named
variants, each with its own version, changelog and optional Mordecai card. docs/library-design.md
explains the layout and the rules.

This package imports the verdict engine and is never imported by it. Its third-party
dependencies are the optional `library` extra (uv sync --extra library).
"""


class LibraryError(Exception):
    """Input the library can't read or won't use. The message says which and why."""
