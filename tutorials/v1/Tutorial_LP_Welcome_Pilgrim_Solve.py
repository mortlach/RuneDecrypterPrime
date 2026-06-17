from __future__ import annotations

import runpy
from pathlib import Path

"""
Tutorial wrapper for the Welcome Pilgrim solved-LP attempt.

The actual per-solve entrypoint lives at:

    solving/solved_lp/welcome_pilgrim/solve.py

This wrapper keeps the existing tutorial manifest/CI runner path while ensuring
there is one obvious solved-LP file to open and run directly.
"""

_SOLVE_SCRIPT = Path(__file__).resolve().parents[2] / "solving" / "solved_lp" / "welcome_pilgrim" / "solve.py"


if __name__ == "__main__":
    runpy.run_path(str(_SOLVE_SCRIPT), run_name="__main__")
