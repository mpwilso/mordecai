"""The GitHub Action and the workflows: every third-party action pinned to a commit SHA, inputs
reaching shell scripts only through env, and CI running the action's identify step (#29).

Read as text, since the engine has no YAML parser."""

import re

from conftest import ROOT

ACTION = (ROOT / "action.yml").read_text(encoding="utf-8")
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def _uses(text: str) -> list[str]:
    return re.findall(r"^\s*(?:-\s+)?uses:\s*(\S+)", text, re.M)


def test_every_action_is_pinned_to_a_full_commit_sha():
    for name, text in [("action.yml", ACTION)] + [(w.name, w.read_text()) for w in WORKFLOWS]:
        for ref in _uses(text):
            if ref.startswith("./"):
                continue
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref), (name, ref)


def test_the_action_is_composite_and_passes_fail_on_through():
    assert re.search(r"^runs:\n  using: composite$", ACTION, re.M)
    assert '--fail-on "$FAIL_ON"' in ACTION
    assert '--markdown "$card"' in ACTION
    assert 'gh pr comment "$PR" --repo "$REPO" --body-file "$CARD"' in ACTION


def test_no_input_is_interpolated_into_a_script():
    """${{ }} inside a run: block would let a crafted input run as shell."""
    for name, text in [("action.yml", ACTION)] + [(w.name, w.read_text()) for w in WORKFLOWS]:
        for block in re.findall(r"run: \|\n((?:\s{8,}.*\n?)+)|run: (.+)", text):
            script = block[0] or block[1]
            assert "${{" not in script, (name, script)


def test_ci_runs_the_actions_identify_step_without_commenting():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    steps = re.findall(r"uses: \./\n {8}with:\n((?: {10}\S.*\n)+)", ci)
    assert len(steps) == 2
    for step in steps:
        assert 'comment: "false"' in step
        assert "result: tests/fixtures/suite1-result.json" in step
    assert "fail-on: helps" in steps[1]
    assert "steps.failing.outcome != 'failure'" in ci


def test_release_publishes_with_trusted_publishing_from_one_job():
    """PyPI trusted publishing (#18): only the publish job, in the pypi environment, can ask
    for an OIDC token, and nothing stores a PyPI token."""
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert re.search(r"^on:\n  release:\n    types: \[published\]$", release, re.M)
    assert re.search(r"^permissions:\n  contents: read$", release, re.M)
    assert release.count("id-token: write") == 1
    publish = release[release.index("\n  publish:\n") :]
    assert "id-token: write" in publish and "name: pypi" in publish
    assert "pypa/gh-action-pypi-publish@" in publish
    assert "password" not in release and "secrets." not in release
    assert "uv build" in release
