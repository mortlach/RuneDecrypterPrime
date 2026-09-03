from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import pytest


pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[3]


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


def test_engine_package_resolves_to_current_checkout_and_is_lazy() -> None:
    _run_isolated(
        """
from pathlib import Path
import rdp.core.engine
import sys

expected = Path('src/rdp/core/engine').resolve()
assert Path(rdp.core.engine.__file__).resolve().parent == expected
for name in (
    'rdp.api.run',
    'rdp.scoring.rune_scorer',
    'rdp.scoring.torch_rune_scorer',
    'torch',
    'cupy',
    'rdp.scoring.language_model._fastlm',
    'rdp.scoring.hamming._hamming',
    'rdp.scoring.span_hamming._span_hamming_fast',
):
    assert name not in sys.modules, name
"""
    )


def test_removed_engine_owners_are_not_discoverable() -> None:
    _run_isolated(
        """
import importlib.util

for name in (
    'rune_decrypter_prime.core.engine',
    'rune_decrypter_prime.core.engine.builders',
    'rune_decrypter_prime.core.solver_engine',
):
    try:
        found = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        found = None
    assert found is None, (name, found)
"""
    )


def test_engine_api_and_solver_import_orders_are_cycle_free() -> None:
    for script in (
        "from rdp.core.engine import EngineConfig, solve\nfrom rdp import api",
        "from rdp import api\nfrom rdp.core.engine import EngineConfig, solve",
        "import rdp.solvers.two_period_cribs\nimport rdp.core.engine",
        "import rdp.core.engine\nimport rdp.solvers.two_period_cribs",
    ):
        _run_isolated(script)


def test_runtime_has_no_temporary_finalizer_or_api_orchestration_dependency() -> None:
    runtime_roots = (ROOT / "src/rdp/core/engine", ROOT / "src/rdp/solvers")
    for runtime_root in runtime_roots:
        for path in runtime_root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "solution_finalizer" not in text, path
            tree = ast.parse(text, filename=str(path))
            imported = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            imported.update(
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            )
            assert "rdp.api.pipeline_helpers" not in imported, path
            assert "rdp.api.run" not in imported, path
