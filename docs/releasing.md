# Releasing

[.github/workflows/release.yml](../.github/workflows/release.yml) runs when a GitHub release is published. Its one job checks that the release tag is `v` plus the version in `pyproject.toml`, builds the sdist and the wheel with `uv build`, and keeps them as the run's artifact. It has a read-only token and no secrets.

Mordecai is not on PyPI. Trusted publishing to PyPI was set up in this workflow on 2026-10-11, never used, and dropped on 2026-10-24; the setup is in git history before that date. The README installs from a clone with `uv sync`, and `git checkout vX.Y.Z` gives a release.

The package's long description, `readme` in `pyproject.toml`, is [docs/package.md](package.md), not README.md: the README's relative links and images are for GitHub, so the metadata page is short and links to GitHub with absolute URLs.

## Each release

1. Bump `version` in `pyproject.toml` and `__version__` in `src/mordecai/__init__.py`, run `uv lock`, and move the changelog's Unreleased notes under the new version, on a branch, through CI, into master.
2. Tag master `vX.Y.Z` and publish a GitHub release from that tag, with the changelog section as its notes.
3. The workflow's run on the published release is a check: its tag test and build pass, or the release was cut from the wrong commit.
