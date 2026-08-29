from __future__ import annotations
from rdp import api
from rune_decrypter_prime.core.component_contracts import RankEffect, ScorerLaneName
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.scoring.scorer_lane_report import build_scorer_lane_report

def _lane(report, name: ScorerLaneName):
    matches = [status for status in report.lanes if status.lane is name]
    assert len(matches) == 1
    return matches[0]

def test_word_ngram_report_only_section_has_no_production_rank_effect(tmp_path) -> None:
    cfg = api.ScoringConfig(word_ngram_judge_enabled=True, word_ngram_judge_database=tmp_path / 'missing.sqlite')
    lane = _lane(build_scorer_lane_report(cfg), ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)
    assert lane.rank_effect is RankEffect.REPORT_ONLY
    assert lane.report_section == 'word_ngram_judge'
    assert lane.to_json_dict()['rank_effect'] == 'report_only'

def test_experimental_ngram_lane_name_and_default_status_are_report_only_boundary() -> None:
    report = build_scorer_lane_report(api.ScoringConfig())
    lane = _lane(report, ScorerLaneName.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY)
    assert lane.rank_effect is RankEffect.REPORT_ONLY
    assert lane.report_section == 'ngram_hamming_experimental'
    assert 'experimental_report_only' in lane.to_json_dict()['lane']
