from __future__ import annotations
from rdp import api
from rdp.core.component_contracts import RankingEffect, ScoringLane
from rdp.scoring.scorer_lane_report import build_scorer_lane_report

def _production_lane_json(report):
    return [
        lane.to_json_dict()
        for lane in report.lanes
        if lane.ranking_effect is RankingEffect.PRODUCTION
    ]


def test_word_ngram_report_only_does_not_change_production_lane_report(tmp_path) -> None:
    hamming_backend = object()
    base_report = build_scorer_lane_report(api.ScoringConfig(hamming_enabled=True), hamming_backend=hamming_backend)
    diagnostic_report = build_scorer_lane_report(api.ScoringConfig(hamming_enabled=True, word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'word_ngram.sqlite'), hamming_backend=hamming_backend, word_ngram_judge=object())
    assert _production_lane_json(diagnostic_report) == _production_lane_json(base_report)

def test_word_ngram_report_only_remains_non_production(tmp_path) -> None:
    report = build_scorer_lane_report(
        api.ScoringConfig(
            word_ngram_judge_enabled=True,
            word_ngram_judge_database=tmp_path / "word_ngram.sqlite",
        ),
        word_ngram_judge=object(),
    )
    lane = [
        item
        for item in report.lanes
        if item.lane is ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY
    ][0]
    assert lane.ranking_effect is RankingEffect.REPORT_ONLY
    assert not lane.is_blocking
    report.raise_if_blocked()
