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


# The inertness criterion for V3 (docs/validation-skills.md): no instruction of any kind, and
# none of these words, which name or steer what a commit message looks like.
STEERING = {
    "commit",
    "commits",
    "message",
    "messages",
    "git",
    "write",
    "writing",
    "format",
    "style",
    "tone",
    "short",
    "long",
    "length",
    "prefix",
    "type",
    "word",
    "words",
    "plain",
    "brief",
    "clear",
    "concise",
    "summary",
    "describe",
    "should",
    "must",
    "always",
    "never",
    "use",
    "keep",
    "say",
    "avoid",
    "prefer",
    "conventional",
    "feat",
    "fix",
    "chore",
    "docs",
}


def test_v3_is_inert():
    import re

    body = planted.V3_BODY.lower()
    words = set(re.findall(r"[a-z]+", body))
    assert words & STEERING == set()
    for sentence in re.split(r"(?<=\.)\s+", planted.V3_BODY.split("\n", 2)[2].strip()):
        assert sentence.split()[0] in {"The", "Its"}, sentence
