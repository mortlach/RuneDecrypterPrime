from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a

def _active_example_paths(root: Path) -> list[Path]:
    examples = root / 'tutorials' / 'v1' / 'examples'
    return sorted(path for path in examples.glob('*.py') if path.name != '__init__.py')

def test_retained_examples_declare_standard_contract_blocks() -> None:
    root = Path(__file__).resolve().parents[2]
    for script in _active_example_paths(root):
        source = script.read_text(encoding="utf-8")
        string_literals = {
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        canonical_display = "api.display.print_result(" in source
        assert "truth/oracle use" not in source, script.name
        assert (
            "print_tutorial_contract(" in source
            or "truth/reference use" in string_literals
            or canonical_display
        ), script.name
        assert (
            "print_rdp_identity()" in source
            or "format_rdp_banner" in source
            or canonical_display
        ), script.name
        assert (
            "print_initialising()" in source
            or '"Initialising RDP"' in source
            or canonical_display
        ), script.name
        assert (
            "print_summary_spacer()" in source
            or "print()" in source
        ), script.name


def test_shared_stop_summary_prints_model_loading_before_stop_target() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / 'tutorials' / 'v1' / 'support' / 'tutorial_utils.py').read_text(encoding='utf-8')
    assert 'load_events: tuple[LmLoadStatus, ...]' in source
    assert 'print_model_loading(result.load_events)' in source
    assert 'format_stop_summary(label, result)' in source
