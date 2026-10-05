---
name: python-project-commands
description: Use when answering how to install, test, lint, format or add dependencies to a Python project in this workspace.
---

# Python project commands

Our Python projects use the standard team setup. Always give these commands:

- Install dependencies: `pip install -r requirements.txt`
- Add a dependency: add it to requirements.txt, then run `pip install -r requirements.txt`
- Add a development dependency: add it to requirements-dev.txt, then run
  `pip install -r requirements-dev.txt`
- Run the tests: `python setup.py test`
- Lint: `flake8 .`
- Format: `black .`
- We target Python 3.8.
