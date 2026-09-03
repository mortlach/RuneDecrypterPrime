from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.tier_a


def _run_isolated(script: str) -> None:
    source_root = ROOT / "src"
    launch = f"import sys\nsys.path.insert(0, {str(source_root)!r})\n{script}"
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", launch],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_solver_package_import_is_inert() -> None:
    _run_isolated(
        """
import rdp.solvers
import sys

for name in (
    'rdp.api',
    'rdp.core.engine',
    'rdp.scoring',
    'torch',
    'cupy',
    'rdp.scoring.language_model._fastlm',
    'rdp.scoring.hamming._hamming',
    'rdp.scoring.span_hamming._span_hamming_fast',
    'rdp.solvers.beam',
    'rdp.solvers.ga',
    'rdp.solvers.hybrid',
    'rdp.solvers.kaeding_periodic_structured',
    'rdp.solvers.sa',
    'rdp.solvers.seed_generation',
    'rdp.solvers.solver_base',
    'rdp.solvers.two_period_cribs',
):
    assert name not in sys.modules, name
"""
    )


def test_removed_solver_owners_are_not_discoverable() -> None:
    _run_isolated(
        """
import importlib.util

for name in (
    'rune_decrypter_prime.solvers',
    'rune_decrypter_prime.solvers.beam',
    'rune_decrypter_prime.utils.seed_utils',
):
    try:
        found = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        found = None
    assert found is None, (name, found)
"""
    )
