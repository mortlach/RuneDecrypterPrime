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
    'rdp.keyops',
    'rdp.keyops.periodic_structured_matrix_ops',
    'rdp.keyops.registry',
)
EXPECTED_MATRIX_FACTORY = 'PeriodicStructuredMatrixKeyOps'

def _fresh(code: str) -> str:
    env = os.environ.copy()
    src = str(REPO_ROOT / 'src')
    env['PYTHONPATH'] = os.pathsep.join((part for part in (src, env.get('PYTHONPATH', '')) if part))
    proc = subprocess.run([sys.executable, '-c', code], cwd=REPO_ROOT, env=env, text=True, encoding='utf-8', errors='replace', capture_output=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()

def _import_order_code(order: tuple[str, ...]) -> str:
    imports = '\n'.join((f'import {name}' for name in order))
    return imports + '\nfrom rdp.core.types import KeyOpsFamily\n' + 'import rdp.keyops.registry as registry\n' + 'from rdp.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps\n' + 'factory = registry.get(KeyOpsFamily.MATRIX)\n' + f'assert factory.__name__ == {EXPECTED_MATRIX_FACTORY!r}, factory\n' + 'assert factory is PeriodicStructuredMatrixKeyOps\n' + 'print(factory.__name__)\n'
_IMPORT_ORDERS = list(itertools.permutations(IMPORT_MODULES))
_IMPORT_ORDERS += [(order[0], *order) for order in _IMPORT_ORDERS]
assert len(_IMPORT_ORDERS) == 12

@pytest.mark.parametrize('order', _IMPORT_ORDERS)
def test_matrix_registry_identity_is_invariant_across_12_fresh_import_sequences(order):
    assert _fresh(_import_order_code(order)) == EXPECTED_MATRIX_FACTORY

def test_deleted_keyops_development_packages_are_not_discoverable():
    code = "import importlib.util\nfor name in ('rdp.keyops.dev', 'rune_decrypter_prime.keyops.dev'):\n    try:\n        found = importlib.util.find_spec(name)\n    except ModuleNotFoundError:\n        found = None\n    assert found is None, (name, found)\nprint('absent')\n"
    assert _fresh(code) == 'absent'

def test_duplicate_registration_is_loud_unless_replace_is_explicit():
    code = "from rdp.core.types import KeyOpsFamily\nimport rdp.keyops.registry as registry\nclass Replacement: pass\ntry:\n    registry.register_keyop(KeyOpsFamily.MATRIX)(Replacement)\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('duplicate registration did not fail')\nregistry.register_keyop(KeyOpsFamily.MATRIX, replace=True)(Replacement)\nassert registry.get(KeyOpsFamily.MATRIX) is Replacement\nprint('ok')\n"
    assert _fresh(code) == 'ok'
