---
name: python-dependencies
description: Use whenever a question is about a Python project's dependencies in this workspace: adding, removing, upgrading or installing packages, or updating the lock file.
---

# Python dependencies

Our Python projects manage dependencies with pip and requirements files. Always give these
commands:

- Add a package: add it to requirements.txt, then run `pip install -r requirements.txt`
- Add a development package: add it to requirements-dev.txt, then run
  `pip install -r requirements-dev.txt`
- Remove a package: delete its line from requirements.txt, then run
  `pip uninstall <package>`
- Upgrade a package: `pip install --upgrade <package>`, then `pip freeze > requirements.txt`
- Install everything: `pip install -r requirements.txt -r requirements-dev.txt`
- Update the pinned versions: `pip freeze > requirements.txt`
