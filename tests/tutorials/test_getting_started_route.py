"""Executable and import-boundary checks for the short public-API route."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a
REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE = REPO_ROOT / "tutorials" / "v1" / "getting_started"
STOPS = (
    "01_known_key.py",
    "02_first_search.py",
    "03_repeating_key_search.py",
    "04_reproducible_runs.py",
    "05_known_interruptors.py",
    "06_partial_recovery.py",
    "07_liber_primus_source.py",
)


def test_route_is_ordered_and_uses_only_the_public_package_boundary() -> None:
    assert tuple(path.name for path in sorted(ROUTE.glob("[0-9][0-9]_*.py"))) == STOPS
    for filename in STOPS:
        source = (ROUTE / filename).read_text(encoding="utf-8")
        assert "from rdp import api" in source
        assert "from rdp." not in source
        assert "import rdp." not in source
        assert "sys.path" not in source
        assert "tutorials.v1" not in source


@pytest.mark.parametrize("filename", STOPS)
def test_route_stop_runs_and_checks_its_claim(filename: str) -> None:
    script = ROUTE / filename
    launch = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r}); "
        f"runpy.run_path({str(script)!r}, run_name='__main__')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", launch],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
