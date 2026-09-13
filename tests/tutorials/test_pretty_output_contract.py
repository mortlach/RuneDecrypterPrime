from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a


def test_shared_stop_summary_prints_model_loading_before_stop_target() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / 'tutorials' / 'v1' / 'support' / 'tutorial_utils.py').read_text(encoding='utf-8')
    assert 'load_events: tuple[LmLoadStatus, ...]' in source
    assert 'print_model_loading(result.load_events)' in source
    assert 'format_stop_summary(label, result)' in source
