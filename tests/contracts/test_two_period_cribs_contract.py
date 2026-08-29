from __future__ import annotations
from rdp import api
import rdp.api.two_period_cribs
import ast
from pathlib import Path

def test_production_solver_has_no_campaign_dependency():
    root = Path(__file__).resolve().parents[2]
    source = root / 'src/rune_decrypter_prime/solvers/two_period_cribs.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name for alias in node.names))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert not any((name == 'cipher_development' or name.startswith('cipher_development.') for name in imports))

def test_solver_modules_are_in_package_source():
    from rune_decrypter_prime.solvers.two_period_cribs import CribConstraintSpace
    assert rdp.api.two_period_cribs.TWO_PERIOD_CRIBS_CONTRACT == 'two_period_cribs.v1'
    assert CribConstraintSpace.__module__.startswith('rune_decrypter_prime.')
