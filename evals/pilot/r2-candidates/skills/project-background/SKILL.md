---
name: project-background
description: Background on how the tally project in this workspace is set up.
---

# Project commands

The Python project in this workspace uses uv, pytest and ruff:

- Install the dependencies: `uv sync`
- Run the tests: `uv run pytest`, or `make test`
- Run one test file: `uv run pytest <path>`
- Stop at the first failing test: `uv run pytest -x`
- Lint: `uv run ruff check .`, or `make lint`
- Lint and fix what can be fixed: `uv run ruff check --fix .`
- Format: `uv run ruff format .`, or `make fmt`
- Check the formatting without changing files: `uv run ruff format --check .`
- Python: 3.12 or newer, as `requires-python` in pyproject.toml says.
