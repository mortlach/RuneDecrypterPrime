from __future__ import annotations

from typing import Any

from rune_decrypter_prime.core.capability_gates import (
    active_lane,
    inactive_lane,
    lane_failure_status,
)
from rune_decrypter_prime.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    EffectiveState,
    FallbackPolicy,
    LaneStatus,
    RankEffect,
    RequestState,
    ScorerCapabilityReport,
    ScorerLaneName,
)
from rune_decrypter_prime.core.config.scoring import ScoringConfig


_LANE_ORDER: tuple[ScorerLaneName, ...] = (
    ScorerLaneName.LM_CHAR_WLI,
    ScorerLaneName.HAMMING,
    ScorerLaneName.SPAN_HAMMING_RAW,
    ScorerLaneName.SPAN_HAMMING_CALIBRATED,
    ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY,
    ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY,
)

_REPORT_SECTIONS: dict[ScorerLaneName, str] = {
    ScorerLaneName.LM_CHAR_WLI: "lm_char_wli",
    ScorerLaneName.HAMMING: "hamming_dictionary",
    ScorerLaneName.SPAN_HAMMING_RAW: "span_hamming_raw",
    ScorerLaneName.SPAN_HAMMING_CALIBRATED: "span_hamming_calibrated",
    ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY: "word_ngram_judge",
    ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: "ngram_hamming_experimental",
}

_RANK_EFFECT: dict[ScorerLaneName, RankEffect] = {
    ScorerLaneName.LM_CHAR_WLI: RankEffect.PRODUCTION,
    ScorerLaneName.HAMMING: RankEffect.PRODUCTION,
    ScorerLaneName.SPAN_HAMMING_RAW: RankEffect.PRODUCTION,
    ScorerLaneName.SPAN_HAMMING_CALIBRATED: RankEffect.PRODUCTION,
    ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY: RankEffect.REPORT_ONLY,
    ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: RankEffect.REPORT_ONLY,
}

_FALLBACK_POLICY: dict[ScorerLaneName, FallbackPolicy] = {
    ScorerLaneName.LM_CHAR_WLI: FallbackPolicy.BLOCK,
    ScorerLaneName.HAMMING: FallbackPolicy.BLOCK,
    ScorerLaneName.SPAN_HAMMING_RAW: FallbackPolicy.BLOCK,
    ScorerLaneName.SPAN_HAMMING_CALIBRATED: FallbackPolicy.BLOCK,
    ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY: FallbackPolicy.REPORT_ONLY,
    ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: FallbackPolicy.REPORT_ONLY,
}


def _present(value: object | None) -> bool:
    return value is not None


def _report_only_lane(
    *,
    lane: ScorerLaneName,
    issue: CapabilityIssue | None,
    report_section: str,
) -> LaneStatus:
    return LaneStatus(
        lane=lane,
        request_state=RequestState.REQUESTED,
        effective_state=EffectiveState.REPORT_ONLY,
        rank_effect=RankEffect.REPORT_ONLY,
        fallback_policy=FallbackPolicy.REPORT_ONLY,
        issues=tuple() if issue is None else (issue,),
        report_section=report_section,
    )


def _status_for_observed_lane(
    *,
    lane: ScorerLaneName,
    requested: bool,
    observed: object | None,
    issue: CapabilityIssue | None,
) -> LaneStatus:
    rank_effect = _RANK_EFFECT[lane]
    fallback_policy = _FALLBACK_POLICY[lane]
    report_section = _REPORT_SECTIONS[lane]

    if not requested:
        return inactive_lane(
            lane,
            rank_effect=rank_effect,
            fallback_policy=FallbackPolicy.DISABLED,
            report_section=report_section,
        )

    if rank_effect is RankEffect.REPORT_ONLY:
        return _report_only_lane(
            lane=lane,
            issue=issue,
            report_section=report_section,
        )

    if _present(observed) and issue is None:
        return active_lane(
            lane,
            rank_effect=rank_effect,
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
        rank_effect=rank_effect,
        fallback_policy=fallback_policy,
        request_state=RequestState.REQUESTED,
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
    extra_report_only_lanes: dict[ScorerLaneName, tuple[object | None, CapabilityIssue | None]] | None = None,
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
            ScorerLaneName.LM_CHAR_WLI,
            request_state=RequestState.REQUIRED,
            rank_effect=RankEffect.PRODUCTION,
            fallback_policy=FallbackPolicy.BLOCK,
            report_section=_REPORT_SECTIONS[ScorerLaneName.LM_CHAR_WLI],
        )
    ]

    observed_by_lane: dict[ScorerLaneName, tuple[Any | None, CapabilityIssue | None]] = {
        ScorerLaneName.HAMMING: (hamming_backend, hamming_issue),
        ScorerLaneName.SPAN_HAMMING_RAW: (span_hamming_backend, span_hamming_issue),
        ScorerLaneName.SPAN_HAMMING_CALIBRATED: (calibrated_assets, calibrated_issue),
        ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY: (word_ngram_judge, word_ngram_issue),
        ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY: extra_report_only_lanes.get(
            ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY,
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
