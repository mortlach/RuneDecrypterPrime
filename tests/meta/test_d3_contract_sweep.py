from __future__ import annotations
from pathlib import Path
import pytest
pytestmark = pytest.mark.guardrails
ROOT = Path(__file__).resolve().parents[2]
D3_CONTRACT_FILES = [
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

def test_d3_contract_paths_do_not_use_config_helper_tokens() -> None:
    banned = ('_cfg_get', '_config_get', '_get_cfg', '_get_config')
    for path in D3_CONTRACT_FILES:
        text = _text(path)
        for token in banned:
            assert token not in text

def test_d3_contract_paths_do_not_score_report_only_lanes() -> None:
    banned = ('report_only_score', 'score_report_only', 'report_only_bonus')
    for path in D3_CONTRACT_FILES:
        text = _text(path)
        for token in banned:
            assert token not in text
