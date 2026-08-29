from __future__ import annotations
from rdp import api
import json
import pytest
from rune_decrypter_prime.core.component_contracts import EffectiveState, RankEffect, RequestedLaneUnavailableError, ScorerLaneName
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer

def _lanes(cfg: ScoringConfig) -> tuple[ScorerLaneName, ...]:
    return tuple(cfg.requested_scorer_lanes())

def test_default_config_requests_no_optional_scorer_lanes() -> None:
    assert _lanes(api.ScoringConfig()) == tuple()

def test_hamming_enabled_requests_hamming_lane() -> None:
    assert _lanes(api.ScoringConfig(hamming_enabled=True)) == (ScorerLaneName.HAMMING,)

def test_nonzero_hamming_weight_requests_hamming_lane() -> None:
    assert _lanes(api.ScoringConfig(hamming_weight=0.01)) == (ScorerLaneName.HAMMING,)

def test_zero_hamming_weight_alone_does_not_request_hamming_lane() -> None:
    assert _lanes(api.ScoringConfig(hamming_weight=0.0)) == tuple()

def test_raw_span_mode_requests_raw_span_lane() -> None:
    assert _lanes(api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS)) == (ScorerLaneName.SPAN_HAMMING_RAW,)

def test_span_enabled_legacy_flag_requests_raw_span_lane() -> None:
    assert _lanes(api.ScoringConfig(span_hamming_enabled=True)) == (ScorerLaneName.SPAN_HAMMING_RAW,)

def test_nonzero_span_weight_requests_raw_span_lane() -> None:
    assert _lanes(api.ScoringConfig(span_hamming_weight=0.5)) == (ScorerLaneName.SPAN_HAMMING_RAW,)

def test_calibrated_span_mode_requests_calibrated_lane_only() -> None:
    assert _lanes(api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED, span_hamming_enabled=True, span_hamming_weight=0.5)) == (ScorerLaneName.SPAN_HAMMING_CALIBRATED,)

def test_word_ngram_judge_requests_report_only_lane(tmp_path) -> None:
    assert _lanes(api.ScoringConfig(word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'word_ngram.sqlite')) == (ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY,)

def test_requested_lane_order_is_stable_with_raw_span(tmp_path) -> None:
    assert _lanes(api.ScoringConfig(hamming_enabled=True, span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS, word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'word_ngram.sqlite')) == (ScorerLaneName.HAMMING, ScorerLaneName.SPAN_HAMMING_RAW, ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)

def test_requested_lane_order_is_stable_with_calibrated_span(tmp_path) -> None:
    assert _lanes(api.ScoringConfig(hamming_enabled=True, span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED, word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'word_ngram.sqlite')) == (ScorerLaneName.HAMMING, ScorerLaneName.SPAN_HAMMING_CALIBRATED, ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)

class _FakeRuneScorer:
    hamming_backend = None
    span_hamming_backend = None
    span_hamming_assets = None
    word_ngram_judge = None

    def __init__(self, c_cfg: CipherConfig, s_cfg: ScoringConfig) -> None:
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg
        self._hamming_backend = type(self).hamming_backend
        self._span_hamming_backend = type(self).span_hamming_backend
        self._span_hamming_assets = type(self).span_hamming_assets
        self._word_ngram_judge = type(self).word_ngram_judge

@pytest.fixture(autouse=True)
def _reset_fake_numpy_scorer(monkeypatch):
    import rune_decrypter_prime.scoring.rune_scorer as rune_scorer_module
    _FakeRuneScorer.hamming_backend = None
    _FakeRuneScorer.span_hamming_backend = None
    _FakeRuneScorer.span_hamming_assets = None
    _FakeRuneScorer.word_ngram_judge = None
    monkeypatch.setattr(rune_scorer_module, 'RuneScorer', _FakeRuneScorer)

def _cipher_cfg() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4)

def _lane_by_name(report, lane: ScorerLaneName):
    matches = [status for status in report.lanes if status.lane is lane]
    assert len(matches) == 1
    return matches[0]

def test_build_scorer_attaches_json_safe_capability_report() -> None:
    scorer = build_scorer(_cipher_cfg(), api.ScoringConfig())
    report = scorer.capability_report()
    assert report is scorer._capability_report
    assert tuple((status.lane for status in report.lanes)) == tuple(ScorerLaneName)
    assert _lane_by_name(report, ScorerLaneName.LM_CHAR_WLI).effective_state is EffectiveState.ACTIVE
    json.dumps(report.to_json_dict())

def test_requested_hamming_missing_backend_blocks_in_build_scorer() -> None:
    with pytest.raises(RequestedLaneUnavailableError, match='hamming'):
        build_scorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))

def test_requested_hamming_backend_is_active_in_report() -> None:
    _FakeRuneScorer.hamming_backend = object()
    scorer = build_scorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScorerLaneName.HAMMING)
    assert lane.effective_state is EffectiveState.ACTIVE
    assert lane.rank_effect is RankEffect.PRODUCTION

def test_requested_raw_span_missing_backend_blocks_in_build_scorer() -> None:
    with pytest.raises(RequestedLaneUnavailableError, match='span_hamming_raw'):
        build_scorer(_cipher_cfg(), api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS))

def test_requested_calibrated_span_missing_assets_blocks_in_build_scorer() -> None:
    with pytest.raises(RequestedLaneUnavailableError, match='span_hamming_calibrated'):
        build_scorer(_cipher_cfg(), api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED))

def test_requested_word_ngram_report_only_missing_runtime_does_not_block(tmp_path) -> None:
    scorer = build_scorer(_cipher_cfg(), api.ScoringConfig(word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'word_ngram.sqlite'))
    lane = _lane_by_name(scorer.capability_report(), ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)
    assert lane.effective_state is EffectiveState.REPORT_ONLY
    assert lane.rank_effect is RankEffect.REPORT_ONLY
    assert not lane.is_blocking
