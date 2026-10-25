# Releasing to PyPI

[.github/workflows/release.yml](../.github/workflows/release.yml) publishes the package `mordecai-skills` to PyPI when a GitHub release is published. It uses PyPI's trusted publishing, so no PyPI token is stored in the repository or its secrets: PyPI trusts a short-lived token that GitHub issues to that one workflow, in that one environment.

The v0.5.0 release is its first run. The README's install lines stay a clone and `uv sync` until a version is on PyPI.

The package's description on pypi.org is [docs/pypi.md](pypi.md), set as `readme` in `pyproject.toml`, not README.md: the README's relative links and images are for GitHub and wouldn't render on PyPI, so the PyPI page is short and links to GitHub with absolute URLs.

## One-time setup

1. **On pypi.org**, signed in as the owner: Account settings, Publishing, "Add a new pending publisher", GitHub tab. A pending publisher reserves the name and creates the project on the first upload. Enter exactly:

   | Field | Value |
   |---|---|
   | PyPI Project Name | `mordecai-skills` |
   | Owner | `mpwilso` |
   | Repository name | `mordecai` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

2. **On GitHub**, in the repository's Settings, Environments: create an environment named `pypi`. Restricting it to tags (deployment branches and tags: `v*`) and adding yourself as a required reviewer are optional, and make a release wait for your approval before it uploads.

## Each release

1. Bump `version` in `pyproject.toml` and `__version__` in `src/mordecai/__init__.py`, run `uv lock`, and move the changelog's Unreleased notes under the new version, on a branch, through CI, into master.
2. Tag master `vX.Y.Z` and publish a GitHub release from that tag.
3. The workflow checks the tag is `v` plus the version in `pyproject.toml`, builds the sdist and wheel with `uv build`, and uploads them. The `build` job has a read-only token; only the `publish` job, in the `pypi` environment, can ask for the token PyPI trusts.

PyPI never lets a version be uploaded twice, so a failed upload after a partial success means bumping the version, not retrying.
