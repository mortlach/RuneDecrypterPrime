from __future__ import annotations
import json
import pytest
from rune_decrypter_prime.core.capability_gates import (
    lane_failure_status,
    raise_for_lane_status,
    raise_if_requested_lane_blocked,
)
from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    CapabilityEffectiveState,
    FallbackPolicy,
    RankingEffect,
    CapabilityRequestState,
    RequestedLaneUnavailableError,
    ScorerCapabilityReport,
    ScoringLane,
)


def _issue() -> CapabilityIssue:
    return CapabilityIssue(
        code="backend_unavailable",
        message="test backend unavailable",
        status=CapabilityStatus.UNAVAILABLE,
        source="test",
    )


def test_report_only_failure_maps_to_report_only_and_does_not_block() -> None:
    lane = lane_failure_status(
        lane=ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY,
        issue=_issue(),
        ranking_effect=RankingEffect.REPORT_ONLY,
        fallback_policy=FallbackPolicy.REPORT_ONLY,
        report_section="word_ngram_judge",
    )
    assert lane.effective_state is CapabilityEffectiveState.REPORT_ONLY
    assert not lane.is_blocking
    raise_for_lane_status(lane)
    raise_if_requested_lane_blocked(ScorerCapabilityReport(lanes=(lane,)))
    payload = lane.to_json_dict()
    assert payload["effective_state"] == "report_only"
    assert payload["ranking_effect"] == "report_only"
    assert payload["fallback_policy"] == "report_only"
    json.dumps(payload)


def test_explicit_reported_fallback_failure_does_not_block() -> None:
    lane = lane_failure_status(
        lane=ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY,
        issue=_issue(),
        ranking_effect=RankingEffect.REPORT_ONLY,
        fallback_policy=FallbackPolicy.EXPLICIT_REPORTED_FALLBACK,
        report_section="ngram_hamming_experimental",
    )
    assert lane.effective_state is CapabilityEffectiveState.FALLBACK_REPORTED
    assert not lane.is_blocking
    raise_for_lane_status(lane)
    raise_if_requested_lane_blocked(ScorerCapabilityReport(lanes=(lane,)))


def test_block_failure_blocks_and_raises_requested_lane_error() -> None:
    lane = lane_failure_status(
        lane=ScoringLane.HAMMING,
        issue=_issue(),
        ranking_effect=RankingEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.BLOCK,
        report_section="hamming_dictionary",
    )
    assert lane.effective_state is CapabilityEffectiveState.BLOCKED
    assert lane.is_blocking
    with pytest.raises(RequestedLaneUnavailableError, match="hamming"):
        raise_for_lane_status(lane)
    with pytest.raises(RequestedLaneUnavailableError, match="hamming"):
        raise_if_requested_lane_blocked(ScorerCapabilityReport(lanes=(lane,)))


def test_disabled_not_requested_failure_is_inactive_and_non_blocking() -> None:
    lane = lane_failure_status(
        lane=ScoringLane.SPAN_HAMMING_RAW,
        issue=_issue(),
        ranking_effect=RankingEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.DISABLED,
        request_state=CapabilityRequestState.NOT_REQUESTED,
        report_section="span_hamming_raw",
    )
    assert lane.effective_state is CapabilityEffectiveState.INACTIVE
    assert not lane.is_blocking
    raise_for_lane_status(lane)
    raise_if_requested_lane_blocked(ScorerCapabilityReport(lanes=(lane,)))


def test_disabled_requested_failure_blocks_instead_of_disappearing() -> None:
    lane = lane_failure_status(
        lane=ScoringLane.SPAN_HAMMING_CALIBRATED,
        issue=_issue(),
        ranking_effect=RankingEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.DISABLED,
        request_state=CapabilityRequestState.REQUESTED,
        report_section="span_hamming_calibrated",
    )
    assert lane.effective_state is CapabilityEffectiveState.BLOCKED
    assert lane.is_blocking
    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_calibrated"):
        raise_if_requested_lane_blocked(ScorerCapabilityReport(lanes=(lane,)))
