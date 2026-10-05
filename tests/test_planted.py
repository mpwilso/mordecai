"""The planted skills check: its files are what scripts/planted.py writes, every suite has 12
cases with 3 quiet ones, and mordecai lint finds nothing to warn about."""

import importlib.util

from conftest import ROOT

from mordecai.lint import frontmatter, lint

spec = importlib.util.spec_from_file_location("planted", ROOT / "scripts" / "planted.py")
planted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planted)

SUITES = [ROOT / "evals" / "planted" / s[0] for s in planted.SUITES]


def test_files_match_the_script():
    assert planted.main(["--check"]) == 0


def test_every_suite_is_lint_clean_with_12_cases():
    assert len(SUITES) >= 8
    for suite in SUITES:
        files, warnings = lint(suite)
        assert warnings == [], suite
        assert len(files) == 12, suite
        assert sum(f.case.trigger == "should-not-fire" for f in files) == 3, suite


def test_the_twin_is_an_exact_copy_measured_against_itself():
    def body(path):
        return frontmatter(path.read_text())[1]

    one = ROOT / "evals/planted/1-convention/skills/ferry-workflow/SKILL.md"
    twin = ROOT / "evals/planted/5a-twin/skills/ferry-workflow-twin/SKILL.md"
    assert body(one) == body(twin)
    for case in (ROOT / "evals/planted/5a-twin/evals").iterdir():
        fields, _ = frontmatter((case / "prompt.md").read_text())
        assert fields["append_system_prompt"] == planted.FERRY_BODY.strip()


def test_holdouts_are_kept_apart():
    assert {s.parent.name for s in SUITES if "holdout" in str(s)} == {"holdout"}


def test_patterns_survive_yaml_single_quotes():
    """Grader patterns are written inside YAML single quotes, so none may contain one."""
    for path, text in planted.outputs().items():
        if path.name == "outcome.md":
            pattern = text.split("pattern: '", 1)[1].rsplit("'\n", 1)[0]
            assert "'" not in pattern, path
