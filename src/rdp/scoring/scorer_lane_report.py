from __future__ import annotations

from typing import Any

from rdp.core.capability_gates import (
    active_lane,
    inactive_lane,
    lane_failure_status,
)
from rdp.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    CapabilityEffectiveState,
    FallbackPolicy,
    ScoringLaneStatus,
    RankingEffect,
    CapabilityRequestState,
    ScorerCapabilityReport,
    ScoringLane,
)
from rdp.core.config.scoring import ScoringConfig


_LANE_ORDER: tuple[ScoringLane, ...] = (
    ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH,
    ScoringLane.HAMMING,
    ScoringLane.SPAN_HAMMING_RAW,
    ScoringLane.SPAN_HAMMING_CALIBRATED,
    ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY,
    ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY,
)

_REPORT_SECTIONS: dict[ScoringLane, str] = {
    ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH: "language_model_character_and_word_length",
    ScoringLane.HAMMING: "hamming_dictionary",
    ScoringLane.SPAN_HAMMING_RAW: "span_hamming_raw",
    ScoringLane.SPAN_HAMMING_CALIBRATED: "span_hamming_calibrated",
    ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY: "word_ngram_judge",
    ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: "ngram_hamming_experimental",
}

_RANK_EFFECT: dict[ScoringLane, RankingEffect] = {
    ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH: RankingEffect.PRODUCTION,
    ScoringLane.HAMMING: RankingEffect.PRODUCTION,
    ScoringLane.SPAN_HAMMING_RAW: RankingEffect.PRODUCTION,
    ScoringLane.SPAN_HAMMING_CALIBRATED: RankingEffect.PRODUCTION,
    ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY: RankingEffect.REPORT_ONLY,
    ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: RankingEffect.REPORT_ONLY,
}

_FALLBACK_POLICY: dict[ScoringLane, FallbackPolicy] = {
    ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH: FallbackPolicy.BLOCK,
    ScoringLane.HAMMING: FallbackPolicy.BLOCK,
    ScoringLane.SPAN_HAMMING_RAW: FallbackPolicy.BLOCK,
    ScoringLane.SPAN_HAMMING_CALIBRATED: FallbackPolicy.BLOCK,
    ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY: FallbackPolicy.REPORT_ONLY,
    ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: FallbackPolicy.REPORT_ONLY,
}


def _present(value: object | None) -> bool:
    return value is not None


def _report_only_lane(
    *,
    lane: ScoringLane,
    issue: CapabilityIssue | None,
    report_section: str,
) -> ScoringLaneStatus:
    return ScoringLaneStatus(
        lane=lane,
        request_state=CapabilityRequestState.REQUESTED,
        effective_state=CapabilityEffectiveState.REPORT_ONLY,
        ranking_effect=RankingEffect.REPORT_ONLY,
        fallback_policy=FallbackPolicy.REPORT_ONLY,
        issues=tuple() if issue is None else (issue,),
        report_section=report_section,
    )


def _status_for_observed_lane(
    *,
    lane: ScoringLane,
    requested: bool,
    observed: object | None,
    issue: CapabilityIssue | None,
) -> ScoringLaneStatus:
    rank_effect = _RANK_EFFECT[lane]
    fallback_policy = _FALLBACK_POLICY[lane]
    report_section = _REPORT_SECTIONS[lane]

    if not requested:
        return inactive_lane(
            lane,
            ranking_effect=rank_effect,
            fallback_policy=FallbackPolicy.DISABLED,
            report_section=report_section,
        )

    if rank_effect is RankingEffect.REPORT_ONLY:
        return _report_only_lane(
            lane=lane,
            issue=issue,
            report_section=report_section,
        )

    if _present(observed) and issue is None:
        return active_lane(
            lane,
            ranking_effect=rank_effect,
            fallback_policy=fallback_policy,
            report_section=report_section,
        )

    if issue is None:
        issue = CapabilityIssue(
            code="requested_lane_unavailable",
            message=f"requested scorer lane {lane.value} is unavailable",
            status=CapabilityStatus.UNAVAILABLE,
            source=None,
        )

    return lane_failure_status(
        lane=lane,
        issue=issue,
        ranking_effect=rank_effect,
        fallback_policy=fallback_policy,
        request_state=CapabilityRequestState.REQUESTED,
        report_section=report_section,
    )


def build_scorer_lane_report(
    cfg: ScoringConfig,
    *,
    hamming_backend: object | None = None,
    hamming_issue: CapabilityIssue | None = None,
    span_hamming_backend: object | None = None,
    span_hamming_issue: CapabilityIssue | None = None,
    calibrated_assets: object | None = None,
    calibrated_issue: CapabilityIssue | None = None,
    word_ngram_judge: object | None = None,
    word_ngram_issue: CapabilityIssue | None = None,
    extra_report_only_lanes: dict[ScoringLane, tuple[object | None, CapabilityIssue | None]] | None = None,
) -> ScorerCapabilityReport:
    """Build the V1 scorer-lane capability report from typed config and observations.

    Public/API compatibility belongs outside this function. The input config must
    already be canonical, and the observed lane values must come from the scorer
    runtime or focused tests.
    """
    if not isinstance(cfg, ScoringConfig):
        raise TypeError(f"cfg must be ScoringConfig, got {type(cfg).__name__}")

    requested = set(cfg.requested_scorer_lanes())
    extra_report_only_lanes = dict(extra_report_only_lanes or {})

    lanes = [
        active_lane(
            ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH,
            request_state=CapabilityRequestState.REQUIRED,
            ranking_effect=RankingEffect.PRODUCTION,
            fallback_policy=FallbackPolicy.BLOCK,
            report_section=_REPORT_SECTIONS[ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH],
        )
    ]

    observed_by_lane: dict[ScoringLane, tuple[Any | None, CapabilityIssue | None]] = {
        ScoringLane.HAMMING: (hamming_backend, hamming_issue),
        ScoringLane.SPAN_HAMMING_RAW: (span_hamming_backend, span_hamming_issue),
        ScoringLane.SPAN_HAMMING_CALIBRATED: (calibrated_assets, calibrated_issue),
        ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY: (word_ngram_judge, word_ngram_issue),
        ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: extra_report_only_lanes.get(
            ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY,
            (None, None),
        ),
    }

    for lane in _LANE_ORDER[1:]:
        observed, issue = observed_by_lane[lane]
        lanes.append(
            _status_for_observed_lane(
                lane=lane,
                requested=lane in requested,
                observed=observed,
                issue=issue,
            )
        )

    return ScorerCapabilityReport(lanes=tuple(lanes), components=tuple())
