"""Make ``src`` importable so tests can ``import main`` (matches ``python src/main.py``)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
