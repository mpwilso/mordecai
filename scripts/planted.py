"""Writes the planted skills check: one small plugin per planted skill, with its eval cases.

    uv run python scripts/planted.py          write evals/planted/
    uv run python scripts/planted.py --check  exit 1 if a file differs from what this would write

Each planted skill is its own plugin, because `claude plugin eval` drops the whole plugin
under test from the baseline arm: one plugin holding every skill would measure them together.
docs/planted-skills.md says what each skill is for and what verdict it should get.

Every suite has 12 cases: 9 that the skill should change, each with an outcome grader and a
"the skill fired" grader, and 3 nearby requests where the skill should stay quiet. No prompt
names its skill. `mordecai lint` must report no warnings for any suite.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evals" / "planted"
TOOLS = "[Read, Glob, Grep, Skill]"


def fired_input(skill: str) -> str:
    return '\'"skill"\\s*:\\s*"(?:[\\w-]+:)?' + skill + "\"'"


# Skills ----------------------------------------------------------------------------------------

FERRY_DESCRIPTION = (
    "Use when naming a git branch or writing a pull request description for work tracked in "
    "this team's ticket system."
)
FERRY_BODY = """# Branches and pull requests

Every branch is named `qrx-<ticket number>--<summary>`: the lowercase prefix qrx, a hyphen,
the ticket number, two hyphens, then a two to four word summary in lowercase kebab case. For
example, ticket 1042 about a login timeout is `qrx-1042--fix-login-timeout`.

Every pull request description ends with this exact line on its own:

Ferry-Check: pending

Nothing goes after that line.
"""

FILLER_BODY = """# Branches and pull requests

When working on branches and pull requests, be clear and consistent. Use descriptive names
that a teammate would understand. Keep descriptions short and focused on what changed and
why. Make sure the reviewer can follow the change without asking questions.
"""

COMMITS_BODY = """# Commit messages

Write commit messages in the Conventional Commits format:

    <type>(<optional scope>): <summary>

- The type is one of feat, fix, docs, style, refactor, perf, test, build, ci or chore.
- The summary is in the imperative mood, starts in lowercase, has no trailing period and
  keeps the whole first line under 72 characters.
- If the change needs explaining, add a blank line and a short body that says why.
"""

OUTDATED_BODY = """# Python project commands

Our Python projects use the standard team setup. Always give these commands:

- Install dependencies: `pip install -r requirements.txt`
- Add a dependency: add it to requirements.txt, then run `pip install -r requirements.txt`
- Add a development dependency: add it to requirements-dev.txt, then run
  `pip install -r requirements-dev.txt`
- Run the tests: `python setup.py test`
- Lint: `flake8 .`
- Format: `black .`
- We target Python 3.8.
"""

TAGS_BODY = """# Release tags

Release tags are named `rel-<YYYY>.<MM>.<DD>-<n>`, where n counts that day's releases from 1.
For example, the second release on 5 March 2026 is tagged `rel-2026.03.05-2`.

A hotfix release adds `-hf` to the end: the first hotfix on 9 April 2026 is
`rel-2026.04.09-1-hf`.
"""

CHANGELOG_DESCRIPTION = (
    "Use when writing a changelog entry or a line for the change log of this team's services."
)
CHANGELOG_BODY = """# Changelog entries

Every changelog entry is exactly one line:

    ZK-<ticket> | <area> | <summary>

- The area is one of api, web, data or ops.
- The summary is in the past tense and starts in lowercase.

For example, ticket 318, a fix for the CSV export timing out in the web app, is
`ZK-318 | web | fixed the CSV export timing out`.
"""

CHANGELOG_FILLER_BODY = """# Changelog entries

Changelog entries should be clear and useful to readers. Describe what changed in plain
language, keep each entry brief, and mention anything a reader needs to act on.
"""

# Sample repo for the outdated skill ----------------------------------------------------------

REPO_SCRIPT = r"""#!/usr/bin/env bash
# Writes a small Python project that uses uv, pytest and ruff, which the skill under test
# describes wrongly.
set -euo pipefail
mkdir -p src/tally tests
cat > pyproject.toml <<'EOF'
[project]
name = "tally"
version = "0.3.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27"]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]

[tool.ruff]
line-length = 100
EOF
cat > Makefile <<'EOF'
test:
	uv run pytest -q

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
EOF
cat > README.md <<'EOF'
# tally

Counts things.

## Development

Install with `uv sync`. Then `make test`, `make lint` and `make fmt` run the tests, the
linter and the formatter. Add a dependency with `uv add <package>`.
EOF
cat > uv.lock <<'EOF'
version = 1
requires-python = ">=3.12"
EOF
cat > src/tally/__init__.py <<'EOF'
def count(items):
    return len(items)
EOF
cat > tests/test_tally.py <<'EOF'
from tally import count


def test_count():
    assert count([1, 2]) == 2
EOF
"""

# Cases -----------------------------------------------------------------------------------------


def ferry_cases() -> list[dict]:
    branches = [
        (1042, "fixes the login timeout on the mobile app"),
        (877, "adds dark mode to the settings page"),
        (2310, "removes the deprecated v1 export endpoint"),
        (51, "updates the install steps in the README"),
        (6020, "speeds up the nightly report query"),
    ]
    prs = [
        (2210, "adds CSV export to the reports page"),
        (913, "fixes a crash when the cart is empty"),
        (4402, "renames the billing module to payments"),
        (1777, "adds retry logic to the webhook sender"),
    ]
    cases = [
        {
            "name": f"branch-{n}",
            "prompt": f"I'm picking up ticket {n}, which {what}. What should I call the git "
            "branch? Reply with only the branch name.",
            "pattern": rf"qrx-{n}--[a-z0-9]+(-[a-z0-9]+)*",
        }
        for n, what in branches
    ]
    cases += [
        {
            "name": f"pr-{n}",
            "prompt": f"Write a short pull request description for ticket {n}, which {what}. "
            "Reply with only the description.",
            "pattern": r"Ferry-Check: pending\s*(```)?\s*$",
        }
        for n, what in prs
    ]
    quiet = [
        (
            "delete-branch",
            "What's the git command to delete a local branch named old-work? "
            "Reply with only the command.",
        ),
        (
            "undo-commit",
            "How do I undo my last git commit but keep the changes staged? Reply "
            "with only the command.",
        ),
        (
            "fahrenheit",
            "Convert 72 degrees Fahrenheit to Celsius. Reply with just the number, "
            "rounded to one decimal place.",
        ),
    ]
    return cases + [{"name": n, "prompt": p, "quiet": True} for n, p in quiet]


def commit_cases() -> list[dict]:
    changes = [
        "renamed getUser to fetchUser and updated the three call sites",
        "fixed an off-by-one error in the pagination helper that skipped the last page",
        "added a --dry-run flag to the deploy script",
        "updated the README with the new install steps",
        "bumped the requests dependency from 2.31 to 2.32",
        "added unit tests for the date parsing utility",
        "removed the unused legacy_auth module",
        "cached the avatar URL to save a database query on every page view",
        "fixed a typo in the error message shown when login fails",
    ]
    pattern = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([\w./-]+\))?!?: \S"
    cases = [
        {
            "name": f"commit-{i + 1}",
            "prompt": f"Write a git commit message for this change: I {c}. Reply with only the "
            "commit message.",
            "pattern": pattern,
            "flags": "m",
        }
        for i, c in enumerate(changes)
    ]
    quiet = [
        ("rebase", "What does git rebase do? Two sentences."),
        (
            "log-oneline",
            "How do I see the last five commits, one line each? Reply with only the command.",
        ),
        ("percent", "What's 15% of 240? Reply with just the number."),
    ]
    return cases + [{"name": n, "prompt": p, "quiet": True} for n, p in quiet]


def outdated_cases() -> list[dict]:
    def right_not(right: str, wrong: str) -> str:
        return rf"^(?![\s\S]*({wrong}))[\s\S]*({right})"

    asks = [
        (
            "tests",
            "the exact command to run its tests",
            right_not(r"uv run pytest|make test", r"setup\.py"),
        ),
        (
            "lint",
            "the exact command to lint it",
            right_not(r"uv run ruff check|make lint", r"flake8"),
        ),
        (
            "format",
            "the exact command to format the code",
            right_not(r"uv run ruff format|make fmt", r"black"),
        ),
        (
            "install",
            "the exact command to install its dependencies",
            right_not(r"uv sync", r"requirements"),
        ),
        (
            "add-dep",
            "the exact command to add the requests library as a dependency",
            right_not(r"uv add requests", r"requirements"),
        ),
        (
            "add-dev-dep",
            "the exact command to add pytest-cov as a development dependency",
            right_not(r"uv add (--dev |--group dev )?pytest-cov", r"requirements"),
        ),
        (
            "one-file",
            "the exact command to run only the tests in tests/test_tally.py",
            right_not(r"uv run pytest[^\n]*tests/test_tally\.py", r"setup\.py"),
        ),
        (
            "autofix",
            "the exact command that lints the code and fixes what it can automatically",
            right_not(r"ruff check[^\n]*--fix", r"flake8"),
        ),
        (
            "python",
            "the minimum Python version it supports, as a version number only",
            right_not(r"3\.12", r"3\.8"),
        ),
    ]
    cases = [
        {
            "name": f"repo-{name}",
            "prompt": f"Look at the project in the current directory and tell me {what}. "
            "Reply with only the answer.",
            "pattern": pattern,
            "scaffold": True,
        }
        for name, what, pattern in asks
    ]
    quiet = [
        ("init-py", "What does an __init__.py file do in a Python package? Two sentences."),
        (
            "km-miles",
            "Convert 3 kilometers to miles, rounded to two decimal places. Reply "
            "with just the number.",
        ),
        ("stash", "What does git stash do? One sentence."),
    ]
    return cases + [{"name": n, "prompt": p, "quiet": True} for n, p in quiet]


def tag_cases() -> list[dict]:
    asks = [
        (
            "first-release",
            "We're cutting the first release today, 2026-10-05.",
            r"rel-2026\.10\.05-1\b",
        ),
        (
            "second-release",
            "This is the second release we're shipping today, 2026-10-05.",
            r"rel-2026\.10\.05-2\b",
        ),
        ("january", "We're shipping our first release on 2027-01-14.", r"rel-2027\.01\.14-1\b"),
        (
            "third",
            "It's 2026-11-30 and this is our third release of the day.",
            r"rel-2026\.11\.30-3\b",
        ),
        (
            "hotfix",
            "We need to tag the first hotfix release today, 2026-10-05.",
            r"rel-2026\.10\.05-1-hf\b",
        ),
        (
            "hotfix-second",
            "It's 2026-12-02 and we're tagging the second hotfix of the day.",
            r"rel-2026\.12\.02-2-hf\b",
        ),
        (
            "march",
            "Today is 2026-03-09 and we're doing our first release.",
            r"rel-2026\.03\.09-1\b",
        ),
        (
            "leap",
            "We're releasing on 2028-02-29, the first release that day.",
            r"rel-2028\.02\.29-1\b",
        ),
        ("summer", "First release of the day on 2026-07-04.", r"rel-2026\.07\.04-1\b"),
    ]
    cases = [
        {
            "name": f"tag-{name}",
            "prompt": f"{situation} What should the git tag be? Reply with only the tag name.",
            "pattern": pattern,
        }
        for name, situation, pattern in asks
    ]
    quiet = [
        ("list-tags", "How do I list all tags in a git repository? Reply with only the command."),
        ("semver", "In semantic versioning, what does the middle number mean? One sentence."),
        ("weekday", "What day of the week was 2026-01-01? Reply with just the day."),
    ]
    return cases + [{"name": n, "prompt": p, "quiet": True} for n, p in quiet]


def changelog_cases() -> list[dict]:
    asks = [
        (318, "web", "fixed the CSV export timing out in the web app"),
        (442, "api", "added rate limiting to the public API"),
        (97, "data", "backfilled the missing March sales rows"),
        (1203, "ops", "moved the staging database to the new cluster"),
        (655, "web", "fixed the date picker showing the wrong month"),
        (2001, "api", "removed the deprecated v1 orders endpoint"),
        (73, "data", "added a daily export of churned accounts"),
        (840, "ops", "rotated the expired TLS certificate on the load balancer"),
        (1517, "web", "made the settings page work on small screens"),
    ]
    cases = [
        {
            "name": f"entry-{n}",
            "prompt": f"Write the changelog entry for ticket {n}: we {what}. Reply with only "
            "the entry.",
            "pattern": rf"^ZK-{n} \| {area} \| [a-z]",
            "flags": "m",
        }
        for n, area, what in asks
    ]
    quiet = [
        ("semver-major", "When should a library bump its major version number? One sentence."),
        (
            "diff-stat",
            "What git command shows how many lines each file changed in the last "
            "commit? Reply with only the command.",
        ),
        ("hours", "How many hours are in a week? Reply with just the number."),
    ]
    return cases + [{"name": n, "prompt": p, "quiet": True} for n, p in quiet]


# Suites ----------------------------------------------------------------------------------------

SUITES = [
    # (directory, plugin, skill, description, body, cases, system prompt in both arms)
    (
        "1-convention",
        "planted-convention",
        "ferry-workflow",
        FERRY_DESCRIPTION,
        FERRY_BODY,
        ferry_cases,
        None,
    ),
    (
        "2-commits",
        "planted-commits",
        "commit-messages",
        "Use when writing a git commit message.",
        COMMITS_BODY,
        commit_cases,
        None,
    ),
    (
        "3-outdated",
        "planted-outdated",
        "python-project-commands",
        "Use when answering how to install, test, lint, format or add dependencies to a Python "
        "project in this workspace.",
        OUTDATED_BODY,
        outdated_cases,
        None,
    ),
    ("4-vague", "planted-vague", "notes", "General notes.", TAGS_BODY, tag_cases, None),
    (
        "5a-twin",
        "planted-twin",
        "ferry-workflow-twin",
        FERRY_DESCRIPTION,
        FERRY_BODY,
        ferry_cases,
        FERRY_BODY,
    ),
    (
        "5b-filler",
        "planted-filler",
        "ferry-helper",
        FERRY_DESCRIPTION,
        FILLER_BODY,
        ferry_cases,
        None,
    ),
    (
        "holdout/6-convention",
        "holdout-convention",
        "changelog-format",
        CHANGELOG_DESCRIPTION,
        CHANGELOG_BODY,
        changelog_cases,
        None,
    ),
    (
        "holdout/7-filler",
        "holdout-filler",
        "changelog-helper",
        CHANGELOG_DESCRIPTION,
        CHANGELOG_FILLER_BODY,
        changelog_cases,
        None,
    ),
]


def yaml_block(key: str, text: str) -> str:
    return (
        f"{key}: |\n"
        + "".join(f"  {line}\n" if line else "\n" for line in text.split("\n")).rstrip("\n")
        + "\n"
    )


def suite_files(directory, plugin, skill, description, body, cases, system) -> dict[Path, str]:
    base = OUT / directory
    files = {
        base / ".claude-plugin" / "plugin.json": json.dumps(
            {
                "name": plugin,
                "version": "1.0.0",
                "description": f"Planted skill: {skill}.",
                "author": {"name": "Matt Wilson"},
            },
            indent=2,
        )
        + "\n",
        base / "skills" / skill / "SKILL.md": f"---\nname: {skill}\ndescription: {description}\n"
        f"---\n\n{body}",
    }
    for case in cases():
        d = base / "evals" / case["name"]
        head = f"---\nname: {case['name']}\nmax_turns: {8 if case.get('scaffold') else 4}\n"
        head += f"allowed_tools: {TOOLS}\n"
        if system:
            head += yaml_block("append_system_prompt", system)
        files[d / "prompt.md"] = head + "---\n\n" + case["prompt"] + "\n"
        if case.get("quiet"):
            files[d / "graders" / "quiet.md"] = (
                f"---\ntype: tool_used\ntool: Skill\ninput_match: {fired_input(skill)}\n"
                "min: 0\nmax: 0\narm: both\n---\n"
            )
            continue
        flags = f"flags: {case['flags']}\n" if case.get("flags") else ""
        files[d / "graders" / "outcome.md"] = (
            f"---\ntype: regex\npattern: '{case['pattern']}'\n{flags}---\n"
        )
        files[d / "graders" / "fired.md"] = (
            f"---\ntype: tool_used\ntool: Skill\ninput_match: {fired_input(skill)}\n---\n"
        )
        if case.get("scaffold"):
            files[d / "case.yaml"] = (
                f'schema_version: "1.1"\nname: {case["name"]}\ncontext:\n'
                "  scaffold_script: setup.sh\n"
            )
            files[d / "setup.sh"] = REPO_SCRIPT.lstrip("\n")
    return files


def outputs() -> dict[Path, str]:
    files = {}
    for suite in SUITES:
        files.update(suite_files(*suite))
    return files


def main(argv: list[str]) -> int:
    stale = []
    for path, text in outputs().items():
        if "--check" in argv:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            if path.suffix == ".sh":
                path.chmod(0o755)
    for name in stale:
        print(f"planted: {name} differs from scripts/planted.py; run it")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
