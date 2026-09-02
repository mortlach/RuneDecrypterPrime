from __future__ import annotations
from rdp import api
import warnings
import pytest
from rdp.core.component_contracts import (
    CapabilityEffectiveState,
    RequestedLaneUnavailableError,
    ScoringLane,
)
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer

class _FakeRuneScorer:

    def __init__(self, c_cfg: CipherConfig, s_cfg: ScoringConfig) -> None:
        self._hamming_backend = None
        self._span_hamming_backend = None
        self._span_hamming_assets = None
        self._word_ngram_judge = None

@pytest.fixture(autouse=True)
def _patch_numpy_scorer(monkeypatch: pytest.MonkeyPatch):
    import rdp.scoring.rune_scorer as rune_scorer_module
    monkeypatch.setattr(rune_scorer_module, 'RuneScorer', _FakeRuneScorer)

def _cipher_cfg() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4)

def _warning_messages(caught) -> list[str]:
    return [str(item.message).lower() for item in caught]

@pytest.mark.parametrize(('cfg', 'lane_name'), [(api.ScoringConfig(hamming_enabled=True), 'hamming'), (api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS), 'span_hamming_raw'), (api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED), 'span_hamming_calibrated')])
def test_requested_production_lanes_block_not_warn_or_disappear(cfg: ScoringConfig, lane_name: str) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with pytest.raises(RequestedLaneUnavailableError, match=lane_name):
            build_scorer(_cipher_cfg(), cfg)
    messages = _warning_messages(caught)
    assert not any(('skipping' in msg for msg in messages))
    assert not any(('fallback' in msg for msg in messages))

def test_requested_report_only_lane_reports_without_blocking(tmp_path) -> None:
    cfg = api.ScoringConfig(word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'missing_word_ngram.sqlite')
    scorer = build_scorer(_cipher_cfg(), cfg)
    lane = next(
        (
            status
            for status in scorer.capability_report().lanes
            if status.lane is ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY
        )
    )
    assert lane.effective_state is CapabilityEffectiveState.REPORT_ONLY
    assert not lane.is_blocking
