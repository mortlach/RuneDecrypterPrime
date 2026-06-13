from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.tier_a


ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = ROOT / "tests"

# These imports make pytest collection fail on clean minimal installs where Torch
# is intentionally not installed. Torch-only tests must use pytest.importorskip()
# before importing Torch-backed modules.
BANNED_TOP_LEVEL_IMPORTS = {
    "torch",
    "rune_decrypter_prime.scoring.torch_rune_scorer",
}


def _module_name_from_import(node: ast.Import | ast.ImportFrom) -> str | None:
    if isinstance(node, ast.Import):
        if not node.names:
            return None
        return node.names[0].name

    return node.module


def _is_banned_import(module_name: str | None) -> bool:
    if module_name is None:
        return False

    return any(
        module_name == banned or module_name.startswith(f"{banned}.")
        for banned in BANNED_TOP_LEVEL_IMPORTS
    )


def _top_level_import_issues(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    issues: list[str] = []

    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        module_name = _module_name_from_import(node)
        if _is_banned_import(module_name):
            rel = path.relative_to(ROOT).as_posix()
            issues.append(f"{rel}:{node.lineno}: top-level import of {module_name!r}")

    return issues


def test_tests_do_not_import_torch_backend_at_collection_time() -> None:
    issues: list[str] = []

    # Scan helper modules as well as test modules: a helper imported by a test can
    # still break pytest collection on a clean minimal install.
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        issues.extend(_top_level_import_issues(path))

    assert not issues, (
        "Torch-backed test code must not be imported at pytest collection time. "
        "Use pytest.importorskip(...) before importing Torch or Torch-backed RDP "
        "modules. Offenders:\n"
        + "\n".join(f"- {issue}" for issue in issues)
    )
