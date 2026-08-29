from __future__ import annotations
from rdp import api
import json
from pathlib import Path
import pytest
from rune_decrypter_prime.core.types import ObjectiveFamily, ObjectiveSpec, Stat
from rune_decrypter_prime.scoring.scorer_report import ScorerReport
pytestmark = pytest.mark.tier_a

def test_scorer_report_to_json_dict_is_serialisable_and_primitive() -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, raw_score=0.41, telemetry={'impl': 'numpy', 'model_root': Path('data/lm'), 'device': 'cpu'}, metrics={'score_mean': 0.42, 'score_std': 0.1}, time_seconds=12.5 / 1000.0, details={'top_ids': [1, 2, 3]})
    payload = report.to_json_dict()
    dumped = json.dumps(payload)
    assert isinstance(payload['objective_spec'], dict)
    assert payload['objective_spec']['family'] == 'pct'
    assert payload['objective_spec']['stat'] == 'logp'
    assert payload['objective_spec']['win'] == 10
    assert payload['telemetry']['model_root'] == 'data/lm'

def test_scorer_report_rejects_non_finite_numbers() -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=float('nan'))
    with pytest.raises(ValueError, match='finite'):
        report.to_json_dict()

def test_scorer_report_rejects_absolute_path_payload(tmp_path) -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, telemetry={'model_root': tmp_path / 'lm'})
    with pytest.raises(ValueError, match='absolute Path'):
        report.to_json_dict()

def test_scorer_report_rejects_nested_absolute_path_payload(tmp_path) -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, details={'models': [{'root': tmp_path / 'lm'}]})
    with pytest.raises(ValueError, match='absolute Path'):
        report.to_json_dict()

def test_scorer_report_allows_relative_path_mapping_key() -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, telemetry={Path('data/lm'): 'model'})
    payload = report.to_json_dict()
    assert payload['telemetry']['data/lm'] == 'model'

def test_scorer_report_rejects_absolute_path_mapping_key(tmp_path) -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, details={tmp_path / 'lm': 'model'})
    with pytest.raises(ValueError, match='absolute Path'):
        report.to_json_dict()

def test_scorer_report_allows_relative_path_metric_key() -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, metrics={Path('data/score'): 1.0})
    payload = report.to_json_dict()
    assert payload['metrics']['data/score'] == 1.0

def test_scorer_report_rejects_absolute_path_metric_key(tmp_path) -> None:
    report = api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=0.42, metrics={tmp_path / 'score': 1.0})
    with pytest.raises(ValueError, match='absolute Path'):
        report.to_json_dict()
