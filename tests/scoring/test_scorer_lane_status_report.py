from __future__ import annotations

from rune_decrypter_prime.core.component_contracts import EffectiveState, RankEffect, RequestState, ScorerLaneName
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.scoring.scorer_lane_report import build_scorer_lane_report


def _lane(report, name: ScorerLaneName):
    matches = [status for status in report.lanes if status.lane is name]
    assert len(matches) == 1
    return matches[0]


def test_scorer_lane_report_has_stable_lane_order_and_required_lm_lane() -> None:
    report = build_scorer_lane_report(ScoringConfig())

    assert tuple(status.lane for status in report.lanes) == tuple(ScorerLaneName)
    lm = _lane(report, ScorerLaneName.LM_CHAR_WLI)
    assert lm.request_state is RequestState.REQUIRED
    assert lm.effective_state is EffectiveState.ACTIVE
    assert lm.rank_effect is RankEffect.PRODUCTION


def test_requested_hamming_without_backend_is_blocking_production_lane() -> None:
    report = build_scorer_lane_report(ScoringConfig(hamming_enabled=True))
    hamming = _lane(report, ScorerLaneName.HAMMING)

    assert hamming.request_state is RequestState.REQUESTED
    assert hamming.effective_state is EffectiveState.BLOCKED
    assert hamming.rank_effect is RankEffect.PRODUCTION
    assert hamming.issues


def test_requested_word_ngram_lane_is_report_only(tmp_path) -> None:
    cfg = ScoringConfig(word_ngram_judge_enabled=True, word_ngram_judge_sqlite_path=tmp_path / "missing.sqlite")
    lane = _lane(build_scorer_lane_report(cfg), ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)

    assert lane.request_state is RequestState.REQUESTED
    assert lane.effective_state is EffectiveState.REPORT_ONLY
    assert lane.rank_effect is RankEffect.REPORT_ONLY
