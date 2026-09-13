from __future__ import annotations
from pathlib import Path
import pytest
pytestmark = pytest.mark.guardrails
ROOT = Path(__file__).resolve().parents[2]
RUNTIME_BOUNDARY_FILES = [
    ROOT / "src/rdp/core/engine/builders.py",
    ROOT / "src/rdp/core/capability_gates.py",
    ROOT / "src/rdp/scoring/scorer_lane_report.py",
    ROOT / "src/rdp/core/engine/finalization.py",
    ROOT / "src/rdp/api/run.py",
]


def _text(path: Path) -> str:
    return path.read_text(encoding='utf-8')

def test_removed_core_config_shim_does_not_exist() -> None:
    assert not (ROOT / 'src/rune_decrypter_prime/core/config.py').exists()

def test_runtime_boundary_paths_do_not_use_config_helper_tokens() -> None:
    banned = ('_cfg_get', '_config_get', '_get_cfg', '_get_config')
    for path in RUNTIME_BOUNDARY_FILES:
        text = _text(path)
        for token in banned:
            assert token not in text

def test_runtime_boundary_paths_do_not_score_report_only_lanes() -> None:
    banned = ('report_only_score', 'score_report_only', 'report_only_bonus')
    for path in RUNTIME_BOUNDARY_FILES:
        text = _text(path)
        for token in banned:
            assert token not in text

def test_runtime_capability_stop_and_scheduled_input_gates_are_present() -> None:
    builders = _text(ROOT / "src/rdp/core/engine/builders.py")
    assert "_ensure_capability_report_method" in builders
    assert "raise_if_requested_lane_blocked(report)" in builders
    assert "hamming_issue=getattr" in builders
    unified = _text(ROOT / "src/rdp/scoring/unified_rune_scorer.py")
    assert "def capability_report" in unified
    assert "cfg_scorer must be ScoringConfig" in unified
    assert "hamming_issue=getattr" in unified
    stop_reason = _text(ROOT / "src/rdp/api/stop_reason_contract.py")
    assert "target_score" in stop_reason
    assert "stop_score" in stop_reason
    assert "test_key" in stop_reason
    assert "BUDGET_REASON_PREFIXES" in stop_reason
    scheduled = _text(
        ROOT / "src/rdp/ciphers/scheduled_stream_lookup_cipher.py"
    )
    assert "requires degeneracy='allow'" in scheduled
    assert 'fixed stream values must be a sequence of integer symbols, not text' in scheduled
