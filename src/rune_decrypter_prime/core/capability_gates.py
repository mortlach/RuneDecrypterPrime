from __future__ import annotations

from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    CapabilityEffectiveState,
    FallbackPolicy,
    ScoringLaneStatus,
    RankingEffect,
    CapabilityRequestState,
    RequestedLaneUnavailableError,
    ScorerCapabilityReport,
    ScoringLane,
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
    lane: ScoringLane,
    *,
    ranking_effect: RankingEffect,
    fallback_policy: FallbackPolicy = FallbackPolicy.DISABLED,
    report_section: str | None = None,
) -> ScoringLaneStatus:
    return ScoringLaneStatus(
        lane=lane,
        request_state=CapabilityRequestState.NOT_REQUESTED,
        effective_state=CapabilityEffectiveState.INACTIVE,
        ranking_effect=ranking_effect,
        fallback_policy=fallback_policy,
        issues=tuple(),
        report_section=report_section,
    )


def active_lane(
    lane: ScoringLane,
    *,
    request_state: CapabilityRequestState = CapabilityRequestState.REQUESTED,
    ranking_effect: RankingEffect,
    fallback_policy: FallbackPolicy = FallbackPolicy.BLOCK,
    report_section: str | None = None,
) -> ScoringLaneStatus:
    return ScoringLaneStatus(
        lane=lane,
        request_state=request_state,
        effective_state=CapabilityEffectiveState.ACTIVE,
        ranking_effect=ranking_effect,
        fallback_policy=fallback_policy,
        issues=tuple(),
        report_section=report_section,
    )


def _failure_effective_state(
    *,
    fallback_policy: FallbackPolicy,
    request_state: CapabilityRequestState,
) -> CapabilityEffectiveState:
    if fallback_policy is FallbackPolicy.REPORT_ONLY:
        return CapabilityEffectiveState.REPORT_ONLY
    if fallback_policy is FallbackPolicy.EXPLICIT_REPORTED_FALLBACK:
        return CapabilityEffectiveState.FALLBACK_REPORTED
    if fallback_policy is FallbackPolicy.DISABLED and request_state is CapabilityRequestState.NOT_REQUESTED:
        return CapabilityEffectiveState.INACTIVE
    return CapabilityEffectiveState.BLOCKED


def lane_failure_status(
    *,
    lane: ScoringLane,
    issue: CapabilityIssue,
    ranking_effect: RankingEffect,
    fallback_policy: FallbackPolicy,
    request_state: CapabilityRequestState = CapabilityRequestState.REQUESTED,
    report_section: str | None = None,
) -> ScoringLaneStatus:
    return ScoringLaneStatus(
        lane=lane,
        request_state=request_state,
        effective_state=_failure_effective_state(
            fallback_policy=fallback_policy,
            request_state=request_state,
        ),
        ranking_effect=ranking_effect,
        fallback_policy=fallback_policy,
        issues=(issue,),
        report_section=report_section,
    )


def raise_if_requested_lane_blocked(report: ScorerCapabilityReport) -> None:
    report.raise_if_blocked()


def raise_for_lane_status(lane_status: ScoringLaneStatus) -> None:
    if not lane_status.is_blocking:
        return
    ScorerCapabilityReport(lanes=(lane_status,)).raise_if_blocked()
