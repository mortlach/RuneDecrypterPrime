from __future__ import annotations
from rdp import api
import json
import pytest
from rdp.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    CapabilityEffectiveState,
    FallbackPolicy,
    RankingEffect,
    CapabilityRequestState,
    RequestedLaneUnavailableError,
    ScoringLane,
)
from rune_decrypter_prime.scoring.scorer_lane_report import build_scorer_lane_report

def _issue(code: str='backend_unavailable') -> CapabilityIssue:
    return CapabilityIssue(code=code, message='test lane unavailable', status=CapabilityStatus.UNAVAILABLE, source='test')

def _lane_by_name(report, lane: ScoringLane):
    matches = [status for status in report.lanes if status.lane is lane]
    assert len(matches) == 1
    return matches[0]

def test_default_report_has_stable_lane_order_and_inactive_optional_lanes() -> None:
    report = build_scorer_lane_report(api.ScoringConfig())
    assert tuple((status.lane for status in report.lanes)) == tuple(ScoringLane)
    lm = _lane_by_name(report, ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH)
    assert lm.request_state is CapabilityRequestState.REQUIRED
    assert lm.effective_state is CapabilityEffectiveState.ACTIVE
    assert lm.ranking_effect is RankingEffect.PRODUCTION
    assert lm.fallback_policy is FallbackPolicy.BLOCK
    for status in report.lanes[1:]:
        assert status.request_state is CapabilityRequestState.NOT_REQUESTED
        assert status.effective_state is CapabilityEffectiveState.INACTIVE
        assert not status.is_blocking
    payload = report.to_json_dict()
    assert [lane["lane"] for lane in payload["lanes"]] == [
        lane.value for lane in ScoringLane
    ]
    json.dumps(payload)

def test_requested_hamming_backend_is_active_production() -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(hamming_enabled=True), hamming_backend=object()
    )
    lane = _lane_by_name(report, ScoringLane.HAMMING)
    assert lane.request_state is CapabilityRequestState.REQUESTED
    assert lane.effective_state is CapabilityEffectiveState.ACTIVE
    assert lane.ranking_effect is RankingEffect.PRODUCTION
    assert lane.fallback_policy is FallbackPolicy.BLOCK
    report.raise_if_blocked()

def test_requested_hamming_failure_blocks() -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(hamming_enabled=True), hamming_issue=_issue()
    )
    lane = _lane_by_name(report, ScoringLane.HAMMING)
    assert lane.request_state is CapabilityRequestState.REQUESTED
    assert lane.effective_state is CapabilityEffectiveState.BLOCKED
    assert lane.ranking_effect is RankingEffect.PRODUCTION
    assert lane.fallback_policy is FallbackPolicy.BLOCK
    assert lane.is_blocking
    with pytest.raises(RequestedLaneUnavailableError, match='hamming'):
        report.raise_if_blocked()

def test_requested_raw_span_failure_blocks() -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS),
        span_hamming_issue=_issue(),
    )
    lane = _lane_by_name(report, ScoringLane.SPAN_HAMMING_RAW)
    assert lane.effective_state is CapabilityEffectiveState.BLOCKED
    assert lane.ranking_effect is RankingEffect.PRODUCTION
    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_raw"):
        report.raise_if_blocked()

def test_requested_calibrated_span_failure_blocks() -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED),
        calibrated_issue=_issue("calibrated_assets_missing"),
    )
    lane = _lane_by_name(report, ScoringLane.SPAN_HAMMING_CALIBRATED)
    assert lane.effective_state is CapabilityEffectiveState.BLOCKED
    assert lane.ranking_effect is RankingEffect.PRODUCTION
    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_calibrated"):
        report.raise_if_blocked()

def test_requested_word_ngram_failure_is_report_only_and_non_blocking(tmp_path) -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        ),
        word_ngram_issue=_issue("word_ngram_unavailable"),
    )
    lane = _lane_by_name(report, ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY)
    assert lane.request_state is CapabilityRequestState.REQUESTED
    assert lane.effective_state is CapabilityEffectiveState.REPORT_ONLY
    assert lane.ranking_effect is RankingEffect.REPORT_ONLY
    assert lane.fallback_policy is FallbackPolicy.REPORT_ONLY
    assert not lane.is_blocking
    report.raise_if_blocked()


def test_requested_word_ngram_runtime_is_report_only_even_when_available(
    tmp_path,
) -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        ),
        word_ngram_judge=object(),
    )
    lane = _lane_by_name(report, ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY)
    assert lane.effective_state is CapabilityEffectiveState.REPORT_ONLY
    assert lane.ranking_effect is RankingEffect.REPORT_ONLY
    assert lane.fallback_policy is FallbackPolicy.REPORT_ONLY
    report.raise_if_blocked()

def test_report_builder_rejects_non_canonical_config() -> None:
    with pytest.raises(TypeError, match='ScoringConfig'):
        build_scorer_lane_report({})
