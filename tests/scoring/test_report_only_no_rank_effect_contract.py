from __future__ import annotations

from pathlib import Path

from rune_decrypter_prime.core.component_contracts import (
    EffectiveState,
    RankEffect,
    ScorerLaneName,
)
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.scoring.scorer_lane_report import build_scorer_lane_report
from rune_decrypter_prime.scoring.scorer_report_builder import build_scorer_report


class _Scorer:
    win = 10
    objective = "pct.logp.win10"

    def telemetry(self) -> dict[str, object]:
        return {}

    def last_stats(self) -> dict[str, float]:
        return {"rank_metric": 3.0}


def _lane(report, lane_name: ScorerLaneName):
    return next(lane for lane in report.lanes if lane.lane is lane_name)


def test_report_only_lane_contract_has_no_production_rank_effect() -> None:
    cfg = ScoringConfig(
        word_ngram_judge_enabled=True,
        word_ngram_judge_sqlite_path=Path("word-ngram.sqlite"),
    )

    report = build_scorer_lane_report(cfg, word_ngram_judge=object())
    lane = _lane(report, ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)

    assert lane.effective_state is EffectiveState.REPORT_ONLY
    assert lane.rank_effect is RankEffect.REPORT_ONLY
    assert lane.to_json_dict()["rank_effect"] == "report_only"


def test_report_only_details_do_not_change_score_raw_score_or_metrics() -> None:
    scorer = _Scorer()

    plain = build_scorer_report(
        scorer=scorer,
        objective_str="pct.logp.win10",
        score=10.0,
        raw_score=9.5,
    )
    with_report_only = build_scorer_report(
        scorer=scorer,
        objective_str="pct.logp.win10",
        score=10.0,
        raw_score=9.5,
        extra_details={
            "ngram_hamming_experimental": {
                "report_integration_mode": "report_only_no_rank_effect",
                "production_rank_effect": "none",
            }
        },
    )

    assert with_report_only.score == plain.score
    assert with_report_only.raw_score == plain.raw_score
    assert with_report_only.metrics == plain.metrics
    assert with_report_only.details["ngram_hamming_experimental"]["production_rank_effect"] == "none"
