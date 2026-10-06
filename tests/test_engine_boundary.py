"""The verdict engine stays standard library only and never imports the skill library, so a plain
`uv sync` (without the library extra) still gives a working identify, check and lint."""

import ast
import subprocess
import sys

from conftest import FIXTURES, ROOT

ENGINE = [
    "__init__",
    "__main__",
    "card",
    "cli",
    "lint",
    "provenance",
    "render",
    "result",
    "verdict",
]


def test_engine_modules_import_only_the_standard_library_and_each_other():
    allowed = set(sys.stdlib_module_names) | {"mordecai"}
    for name in ENGINE:
        tree = ast.parse((ROOT / "src/mordecai" / f"{name}.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            else:
                continue
            for mod in mods:
                assert mod.split(".")[0] in allowed, (name, mod)
                if mod.startswith("mordecai.library"):
                    # Only cli.py may reach the library, and only inside a function.
                    assert name == "cli", (name, mod)
                    assert node.col_offset > 0, "cli.py must import the library lazily"


# Runs identify, check and lint with the library's third-party packages made unimportable, and
# reports which mordecai modules got loaded.
SCRIPT = r"""
import io, sys
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("strictyaml", "mcp", "pydantic", "anyio", "skills_ref"):
            raise ImportError(f"blocked {name}", name=name)
        return None
sys.meta_path.insert(0, Block())
from mordecai.cli import main
codes = []
codes.append(main(["identify", sys.argv[1], "--skill", sys.argv[2], "--card", sys.argv[3]],
                  out=io.StringIO()))
codes.append(main(["check", sys.argv[3], "--skill", sys.argv[2]], out=io.StringIO()))
codes.append(main(["lint", sys.argv[2]], out=io.StringIO()))
loaded = sorted(m for m in sys.modules if m.startswith("mordecai"))
err = io.StringIO()
sys.stderr = err
codes.append(main(["library", "list"], out=io.StringIO()))
sys.stderr = sys.__stderr__
print(codes)
print(loaded)
print("extra" in err.getvalue())
"""


def test_identify_check_and_lint_work_without_the_library_extra(tmp_path):
    card = tmp_path / "card.json"
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            SCRIPT,
            str(FIXTURES / "probe-result.json"),
            str(FIXTURES / "probe"),
            str(card),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=True,
    )
    codes, modules, hint = done.stdout.splitlines()
    assert codes == "[0, 0, 1, 2]"  # lint warns on the one-case probe; library can't load
    assert "mordecai.library" not in modules
    assert hint == "True"
