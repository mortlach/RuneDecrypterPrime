from __future__ import annotations

import json

import pytest

from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    ComponentContract,
    ComponentKind,
    EffectiveState,
    FallbackPolicy,
    LaneStatus,
    RankEffect,
    RequestState,
    RequestedLaneUnavailableError,
    ScorerCapabilityReport,
    ScorerLaneName,
    V1Status,
)


def test_lane_status_is_json_safe() -> None:
    issue = CapabilityIssue(
        code="asset_missing",
        message="missing test asset",
        status=CapabilityStatus.ASSET_MISSING,
        source="test/asset",
        exception_type="FileNotFoundError",
    )
    lane = LaneStatus(
        lane=ScorerLaneName.HAMMING,
        request_state=RequestState.REQUESTED,
        effective_state=EffectiveState.BLOCKED,
        rank_effect=RankEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.BLOCK,
        issues=(issue,),
        report_section="hamming_dictionary",
    )

    payload = lane.to_json_dict()
    assert payload["lane"] == "hamming"
    assert payload["effective_state"] == "blocked"
    json.dumps(payload)


def test_raw_string_enum_values_are_rejected() -> None:
    with pytest.raises(TypeError):
        LaneStatus(  # type: ignore[arg-type]
            lane="hamming",
            request_state=RequestState.REQUESTED,
            effective_state=EffectiveState.ACTIVE,
            rank_effect=RankEffect.PRODUCTION,
            fallback_policy=FallbackPolicy.BLOCK,
        )


def test_blocked_report_raises_requested_lane_error() -> None:
    lane = LaneStatus(
        lane=ScorerLaneName.SPAN_HAMMING_RAW,
        request_state=RequestState.REQUESTED,
        effective_state=EffectiveState.BLOCKED,
        rank_effect=RankEffect.PRODUCTION,
        fallback_policy=FallbackPolicy.BLOCK,
        issues=(CapabilityIssue("backend_failed", "backend failed", CapabilityStatus.UNAVAILABLE),),
    )
    report = ScorerCapabilityReport(lanes=(lane,))

    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_raw"):
        report.raise_if_blocked()


def test_component_contract_json_is_stable() -> None:
    contract = ComponentContract(
        component_id="span_hamming_raw",
        kind=ComponentKind.SCORER_LANE,
        v1_status=V1Status.V1_OPTIONAL,
        rank_effect=RankEffect.PRODUCTION,
        required_if_requested=True,
        default_fallback_policy=FallbackPolicy.BLOCK,
        owner_module="rune_decrypter_prime.scoring.span_hamming",
    )

    payload = contract.to_json_dict()
    assert payload["component_id"] == "span_hamming_raw"
    assert payload["v1_status"] == "v1_optional"
    json.dumps(payload)
