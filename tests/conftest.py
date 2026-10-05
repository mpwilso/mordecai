import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from builder import make_result, same  # noqa: E402,F401
