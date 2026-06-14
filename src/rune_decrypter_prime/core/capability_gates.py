from __future__ import annotations

from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    EffectiveState,
    FallbackPolicy,
    LaneStatus,
    RankEffect,
    RequestState,
    RequestedLaneUnavailableError,
    ScorerCapabilityReport,
    ScorerLaneName,
)


def issue_from_exception(
    *,
    code: str,
    status: CapabilityStatus,
    exc: BaseException,
    source: str | None = None,
    message: str | None = None,
) -> CapabilityIssue:
    return CapabilityIssue(
        code=code,
        message=message or str(exc) or exc.__class__.__name__,
        status=status,
        source=source,
        exception_type=exc.__class__.__name__,
    )


def inactive_lane(
    lane: ScorerLaneName,
    *,
    rank_effect: RankEffect,
    fallback_policy: FallbackPolicy = FallbackPolicy.DISABLED,
    report_section: str | None = None,
) -> LaneStatus:
    return LaneStatus(
        lane=lane,
        request_state=RequestState.NOT_REQUESTED,
        effective_state=EffectiveState.INACTIVE,
        rank_effect=rank_effect,
        fallback_policy=fallback_policy,
        issues=tuple(),
        report_section=report_section,
    )


def active_lane(
    lane: ScorerLaneName,
    *,
    request_state: RequestState = RequestState.REQUESTED,
    rank_effect: RankEffect,
    fallback_policy: FallbackPolicy = FallbackPolicy.BLOCK,
    report_section: str | None = None,
) -> LaneStatus:
    return LaneStatus(
        lane=lane,
        request_state=request_state,
        effective_state=EffectiveState.ACTIVE,
        rank_effect=rank_effect,
        fallback_policy=fallback_policy,
        issues=tuple(),
        report_section=report_section,
    )


def _failure_effective_state(
    *,
    fallback_policy: FallbackPolicy,
    request_state: RequestState,
) -> EffectiveState:
    if fallback_policy is FallbackPolicy.REPORT_ONLY:
        return EffectiveState.REPORT_ONLY
    if fallback_policy is FallbackPolicy.EXPLICIT_REPORTED_FALLBACK:
        return EffectiveState.FALLBACK_REPORTED
    if fallback_policy is FallbackPolicy.DISABLED and request_state is RequestState.NOT_REQUESTED:
        return EffectiveState.INACTIVE
    return EffectiveState.BLOCKED


def lane_failure_status(
    *,
    lane: ScorerLaneName,
    issue: CapabilityIssue,
    rank_effect: RankEffect,
    fallback_policy: FallbackPolicy,
    request_state: RequestState = RequestState.REQUESTED,
    report_section: str | None = None,
) -> LaneStatus:
    return LaneStatus(
        lane=lane,
        request_state=request_state,
        effective_state=_failure_effective_state(
            fallback_policy=fallback_policy,
            request_state=request_state,
        ),
        rank_effect=rank_effect,
        fallback_policy=fallback_policy,
        issues=(issue,),
        report_section=report_section,
    )


def raise_if_requested_lane_blocked(report: ScorerCapabilityReport) -> None:
    report.raise_if_blocked()


def raise_for_lane_status(lane_status: LaneStatus) -> None:
    if not lane_status.is_blocking:
        return
    ScorerCapabilityReport(lanes=(lane_status,)).raise_if_blocked()
