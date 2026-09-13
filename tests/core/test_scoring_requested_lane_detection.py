from __future__ import annotations
from rdp import api
import json
import pytest
from rdp.core.component_contracts import (
    CapabilityEffectiveState,
    RankingEffect,
    RequestedLaneUnavailableError,
    ScoringLane,
)
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.scoring import ScoringConfig
from rdp.core.engine.builders import build_scorer


def _lanes(cfg: ScoringConfig) -> tuple[ScoringLane, ...]:
    return tuple(cfg.requested_scorer_lanes())

def test_default_config_requests_no_optional_scorer_lanes() -> None:
    assert _lanes(api.ScoringConfig()) == tuple()

def test_hamming_enabled_requests_hamming_lane() -> None:
    assert _lanes(api.ScoringConfig(hamming_enabled=True)) == (ScoringLane.HAMMING,)

def test_nonzero_hamming_weight_requests_hamming_lane() -> None:
    assert _lanes(api.ScoringConfig(hamming_weight=0.01)) == (ScoringLane.HAMMING,)

def test_zero_hamming_weight_alone_does_not_request_hamming_lane() -> None:
    assert _lanes(api.ScoringConfig(hamming_weight=0.0)) == tuple()

def test_raw_span_mode_requests_raw_span_lane() -> None:
    assert _lanes(
        api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS)
    ) == (ScoringLane.SPAN_HAMMING_RAW,)


def test_span_enabled_legacy_flag_requests_raw_span_lane() -> None:
    assert _lanes(api.ScoringConfig(span_hamming_enabled=True)) == (
        ScoringLane.SPAN_HAMMING_RAW,
    )


def test_nonzero_span_weight_requests_raw_span_lane() -> None:
    assert _lanes(api.ScoringConfig(span_hamming_weight=0.5)) == (
        ScoringLane.SPAN_HAMMING_RAW,
    )


def test_calibrated_span_mode_requests_calibrated_lane_only() -> None:
    assert _lanes(
        api.ScoringConfig(
            span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED,
            span_hamming_enabled=True,
            span_hamming_weight=0.5,
        )
    ) == (ScoringLane.SPAN_HAMMING_CALIBRATED,)


def test_word_ngram_judge_requests_report_only_lane(tmp_path) -> None:
    assert _lanes(
        api.ScoringConfig(
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        )
    ) == (ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY,)


def test_requested_lane_order_is_stable_with_raw_span(tmp_path) -> None:
    assert _lanes(
        api.ScoringConfig(
            hamming_enabled=True,
            span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS,
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        )
    ) == (
        ScoringLane.HAMMING,
        ScoringLane.SPAN_HAMMING_RAW,
        ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY,
    )


def test_requested_lane_order_is_stable_with_calibrated_span(tmp_path) -> None:
    assert _lanes(
        api.ScoringConfig(
            hamming_enabled=True,
            span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED,
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        )
    ) == (
        ScoringLane.HAMMING,
        ScoringLane.SPAN_HAMMING_CALIBRATED,
        ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY,
    )


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
    import rdp.scoring.rune_scorer as rune_scorer_module
    _FakeRuneScorer.hamming_backend = None
    _FakeRuneScorer.span_hamming_backend = None
    _FakeRuneScorer.span_hamming_assets = None
    _FakeRuneScorer.word_ngram_judge = None
    monkeypatch.setattr(rune_scorer_module, 'RuneScorer', _FakeRuneScorer)

def _cipher_cfg() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4)


def _lane_by_name(report, lane: ScoringLane):
    matches = [status for status in report.lanes if status.lane is lane]
    assert len(matches) == 1
    return matches[0]

def test_build_scorer_attaches_json_safe_capability_report() -> None:
    scorer = build_scorer(_cipher_cfg(), api.ScoringConfig())
    report = scorer.capability_report()
    assert report is scorer._capability_report
    assert tuple((status.lane for status in report.lanes)) == tuple(ScoringLane)
    assert (
        _lane_by_name(
            report, ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH
        ).effective_state
        is CapabilityEffectiveState.ACTIVE
    )
    json.dumps(report.to_json_dict())

def test_requested_hamming_missing_backend_blocks_in_build_scorer() -> None:
    with pytest.raises(RequestedLaneUnavailableError, match='hamming'):
        build_scorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))

def test_requested_hamming_backend_is_active_in_report() -> None:
    _FakeRuneScorer.hamming_backend = object()
    scorer = build_scorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScoringLane.HAMMING)
    assert lane.effective_state is CapabilityEffectiveState.ACTIVE
    assert lane.ranking_effect is RankingEffect.PRODUCTION

def test_requested_raw_span_missing_backend_blocks_in_build_scorer() -> None:
    with pytest.raises(RequestedLaneUnavailableError, match='span_hamming_raw'):
        build_scorer(_cipher_cfg(), api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS))

def test_requested_calibrated_span_missing_assets_blocks_in_build_scorer() -> None:
    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_calibrated"):
        build_scorer(
            _cipher_cfg(),
            api.ScoringConfig(
                span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED
            ),
        )


def test_requested_word_ngram_report_only_missing_runtime_does_not_block(
    tmp_path,
) -> None:
    scorer = build_scorer(
        _cipher_cfg(),
        api.ScoringConfig(
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        ),
    )
    lane = _lane_by_name(
        scorer.capability_report(), ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY
    )
    assert lane.effective_state is CapabilityEffectiveState.REPORT_ONLY
    assert lane.ranking_effect is RankingEffect.REPORT_ONLY
    assert not lane.is_blocking
