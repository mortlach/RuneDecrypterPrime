from __future__ import annotations
import pytest
from rune_decrypter_prime.core.capability_gates import lane_failure_status, raise_for_lane_status
from rune_decrypter_prime.core.component_contracts import CapabilityIssue, CapabilityStatus, EffectiveState, FallbackPolicy, RankEffect, RequestState, RequestedLaneUnavailableError, ScorerLaneName

def _missing_backend_issue() -> CapabilityIssue:
    return CapabilityIssue(code='backend_unavailable', message='requested backend is unavailable', status=CapabilityStatus.UNAVAILABLE, source='test')

def test_requested_production_lane_missing_backend_blocks_not_silent_fallback() -> None:
    lane = lane_failure_status(lane=ScorerLaneName.HAMMING, issue=_missing_backend_issue(), rank_effect=RankEffect.PRODUCTION, fallback_policy=FallbackPolicy.BLOCK, request_state=RequestState.REQUESTED)
    assert lane.effective_state is EffectiveState.BLOCKED
    assert lane.fallback_policy is FallbackPolicy.BLOCK
    with pytest.raises(RequestedLaneUnavailableError, match='hamming:backend_unavailable'):
        raise_for_lane_status(lane)

def test_explicit_reported_fallback_is_visible_not_silent() -> None:
    lane = lane_failure_status(lane=ScorerLaneName.SPAN_HAMMING_CALIBRATED, issue=_missing_backend_issue(), rank_effect=RankEffect.PRODUCTION, fallback_policy=FallbackPolicy.EXPLICIT_REPORTED_FALLBACK, request_state=RequestState.REQUESTED)
    assert lane.effective_state is EffectiveState.FALLBACK_REPORTED
    assert lane.fallback_policy is FallbackPolicy.EXPLICIT_REPORTED_FALLBACK
    assert lane.issues
    raise_for_lane_status(lane)

def test_report_only_lane_failure_is_report_only_not_rank_fallback() -> None:
    lane = lane_failure_status(lane=ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY, issue=_missing_backend_issue(), rank_effect=RankEffect.REPORT_ONLY, fallback_policy=FallbackPolicy.REPORT_ONLY, request_state=RequestState.REQUESTED)
    assert lane.effective_state is EffectiveState.REPORT_ONLY
    assert lane.rank_effect is RankEffect.REPORT_ONLY
    raise_for_lane_status(lane)
