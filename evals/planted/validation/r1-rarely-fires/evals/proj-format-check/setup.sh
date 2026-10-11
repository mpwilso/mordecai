#!/usr/bin/env bash
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
