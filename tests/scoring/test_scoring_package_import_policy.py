from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]


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


def test_scoring_package_import_is_optional_dependency_lazy() -> None:
    _run_isolated(
        """
import rdp.scoring
import sys
assert 'rdp.api' not in sys.modules
assert 'torch' not in sys.modules
assert 'cupy' not in sys.modules
assert 'rdp.scoring.language_model._fastlm' not in sys.modules
assert 'rdp.scoring.hamming._hamming' not in sys.modules
assert 'rdp.scoring.span_hamming._span_hamming_fast' not in sys.modules
assert not any(name.startswith('rdp.solvers') for name in sys.modules)
assert not any(name.startswith('rune_decrypter_prime.core.engine') for name in sys.modules)
"""
    )


def test_old_scoring_package_is_not_discoverable() -> None:
    _run_isolated(
        """
import importlib.util
assert importlib.util.find_spec('rune_decrypter_prime.scoring') is None
"""
    )
