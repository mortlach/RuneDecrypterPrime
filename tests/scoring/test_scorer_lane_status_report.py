from __future__ import annotations
from rdp import api
from rune_decrypter_prime.core.component_contracts import (
    CapabilityEffectiveState,
    RankingEffect,
    CapabilityRequestState,
    ScoringLane,
)
from rune_decrypter_prime.scoring.scorer_lane_report import build_scorer_lane_report


def _lane(report, name: ScoringLane):
    matches = [status for status in report.lanes if status.lane is name]
    assert len(matches) == 1
    return matches[0]


def test_scorer_lane_report_has_stable_lane_order_and_required_lm_lane() -> None:
    report = build_scorer_lane_report(api.ScoringConfig())
    assert tuple((status.lane for status in report.lanes)) == tuple(ScoringLane)
    lm = _lane(report, ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH)
    assert lm.request_state is CapabilityRequestState.REQUIRED
    assert lm.effective_state is CapabilityEffectiveState.ACTIVE
    assert lm.ranking_effect is RankingEffect.PRODUCTION


def test_requested_hamming_without_backend_is_blocking_production_lane() -> None:
    report = build_scorer_lane_report(api.ScoringConfig(hamming_enabled=True))
    hamming = _lane(report, ScoringLane.HAMMING)
    assert hamming.request_state is CapabilityRequestState.REQUESTED
    assert hamming.effective_state is CapabilityEffectiveState.BLOCKED
    assert hamming.ranking_effect is RankingEffect.PRODUCTION
    assert hamming.issues


def test_requested_word_ngram_lane_is_report_only(tmp_path) -> None:
    cfg = api.ScoringConfig(
        word_ngram_judge_enabled=True,
        word_ngram_judge_database=tmp_path / "missing.sqlite",
    )
    lane = _lane(
        build_scorer_lane_report(cfg), ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY
    )
    assert lane.request_state is CapabilityRequestState.REQUESTED
    assert lane.effective_state is CapabilityEffectiveState.REPORT_ONLY
    assert lane.ranking_effect is RankingEffect.REPORT_ONLY
