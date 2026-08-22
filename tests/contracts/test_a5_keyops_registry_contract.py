from __future__ import annotations

import itertools
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a
REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORT_MODULES = (
    "rune_decrypter_prime.keyops.registry",
    "rune_decrypter_prime.keyops.periodic_structured_matrix_ops",
    "rune_decrypter_prime.keyops.dev.matrix",
)
EXPECTED_MATRIX_FACTORY = "PeriodicStructuredMatrixKeyOps"


def _fresh(code: str) -> str:
    env = os.environ.copy()
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (src, env.get("PYTHONPATH", "")) if part
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()


def _import_order_code(order: tuple[str, ...]) -> str:
    imports = "\n".join(f"import {name}" for name in order)
    return (
        imports
        + "\nfrom rune_decrypter_prime.core.types import KeyOpsFamily\n"
        + "from rune_decrypter_prime.keyops import registry\n"
        + "factory = registry.get(KeyOpsFamily.MATRIX)\n"
        + f"assert factory.__name__ == {EXPECTED_MATRIX_FACTORY!r}, factory\n"
        + "print(factory.__name__)\n"
    )


_IMPORT_ORDERS = list(itertools.permutations(IMPORT_MODULES))
# Six additional fresh-interpreter sequences repeat the first ordinary import.
# Python import caching must remain harmless while the remaining order changes.
_IMPORT_ORDERS += [(order[0], *order) for order in _IMPORT_ORDERS]
assert len(_IMPORT_ORDERS) == 12


@pytest.mark.parametrize("order", _IMPORT_ORDERS)
def test_matrix_registry_identity_is_invariant_across_12_fresh_import_sequences(order):
    assert _fresh(_import_order_code(order)) == EXPECTED_MATRIX_FACTORY


def test_dev_matrix_import_cannot_replace_production_matrix_registry():
    code = (
        "from rune_decrypter_prime.core.types import KeyOpsFamily\n"
        "from rune_decrypter_prime.keyops import registry\n"
        "before = registry.get(KeyOpsFamily.MATRIX)\n"
        "from rune_decrypter_prime.keyops.dev import matrix as dev_matrix\n"
        "assert registry.get(KeyOpsFamily.MATRIX) is before\n"
        "print(before.__name__)\n"
    )
    assert _fresh(code) == EXPECTED_MATRIX_FACTORY


def test_duplicate_registration_is_loud_unless_replace_is_explicit():
    code = (
        "from rune_decrypter_prime.core.types import KeyOpsFamily\n"
        "from rune_decrypter_prime.keyops import registry\n"
        "class Replacement: pass\n"
        "try:\n"
        "    registry.register_keyop(KeyOpsFamily.MATRIX)(Replacement)\n"
        "except ValueError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('duplicate registration did not fail')\n"
        "registry.register_keyop(KeyOpsFamily.MATRIX, replace=True)(Replacement)\n"
        "assert registry.get(KeyOpsFamily.MATRIX) is Replacement\n"
        "print('ok')\n"
    )
    assert _fresh(code) == "ok"
