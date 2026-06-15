from __future__ import annotations

import pytest

from rune_decrypter_prime.core.capability_gates import inactive_lane, lane_failure_status, raise_for_lane_status
from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    EffectiveState,
    FallbackPolicy,
    RankEffect,
    RequestState,
    RequestedLaneUnavailableError,
    ScorerLaneName,
)


def _issue() -> CapabilityIssue:
    return CapabilityIssue(
        code="missing_asset",
        message="required test asset is missing",
        status=CapabilityStatus.ASSET_MISSING,
    )


def test_requested_lane_failure_blocks_by_default() -> None:
    lane = lane_failure_status(
        lane=ScorerLaneName.HAMMING,
        issue=_issue(),
        rank_effect=RankEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.BLOCK,
    )

    assert lane.request_state is RequestState.REQUESTED
    assert lane.effective_state is EffectiveState.BLOCKED
    with pytest.raises(RequestedLaneUnavailableError, match="hamming"):
        raise_for_lane_status(lane)


def test_report_only_failure_stays_report_only_not_blocking() -> None:
    lane = lane_failure_status(
        lane=ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY,
        issue=_issue(),
        rank_effect=RankEffect.REPORT_ONLY,
        fallback_policy=FallbackPolicy.REPORT_ONLY,
    )

    assert lane.effective_state is EffectiveState.REPORT_ONLY
    raise_for_lane_status(lane)


def test_not_requested_disabled_lane_is_inactive() -> None:
    lane = inactive_lane(
        ScorerLaneName.SPAN_HAMMING_RAW,
        rank_effect=RankEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.DISABLED,
    )

    assert lane.request_state is RequestState.NOT_REQUESTED
    assert lane.effective_state is EffectiveState.INACTIVE
    raise_for_lane_status(lane)
