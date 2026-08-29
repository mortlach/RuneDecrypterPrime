from __future__ import annotations
import importlib
import pytest

def _build_report(**kwargs):
    module = importlib.import_module('rdp.api.solver_report')
    return module.build_solver_report(**kwargs)

def test_test_key_stop_reason_reports_truth_data_use() -> None:
    report = _build_report(solver_name='beam', requested_seed=123, effective_seed=123, normalized_params={'beam_width': 4, 'test_key': [1, 2, 3]}, stop_reason='test_key')
    assert report.details['report_contract'] == {'version': 'api_solver_report_details.v1'}
    assert report.details['oracle_use'] == 'test_key'
    assert report.details['truth_data_policy'] == 'reported_test_or_tutorial_only'

def test_production_report_defaults_truth_data_use_to_none() -> None:
    report = _build_report(solver_name='beam', requested_seed=None, effective_seed=0, normalized_params={'beam_width': 4}, stop_reason='max_evals')
    assert report.details['oracle_use'] == 'none'
    assert report.details['truth_data_policy'] == 'none'
    reproducibility = report.details['reproducibility']
    assert reproducibility['deterministic_seed_policy'] == 'explicit_or_default_zero'
    assert reproducibility['requested_seed'] is None
    assert reproducibility['effective_seed'] == 0
    assert reproducibility['solver_name'] == 'beam'
    assert reproducibility['stop_category'] == 'budget'
    assert reproducibility['stop_reason'] == 'max_evaluations_reached'
    for field in ('run_id', 'created_at_utc', 'rdp_version', 'git_branch', 'git_commit', 'python_version', 'backend', 'device', 'dtype', 'seed', 'stochastic', 'solver_config', 'scoring_config', 'objective', 'cipher', 'asset_ids', 'asset_hashes', 'dictionary_policy', 'stop_category', 'stop_reason'):
        assert field in reproducibility

def test_known_key_fastpath_is_reported_and_existing_details_survive() -> None:
    report = _build_report(solver_name='beam', requested_seed=None, effective_seed=None, normalized_params={'beam_width': 1}, stop_reason='known_key_execution_completed', details={'execution_route': 'known_key_fastpath', 'scorer_lanes': {'lanes': []}})
    payload = report.to_json_dict()
    assert payload['details']['oracle_use'] == 'known_key_fastpath'
    assert payload['details']['truth_data_policy'] == 'reported_test_or_tutorial_only'
    assert payload['details']['scorer_lanes'] == {'lanes': []}
    assert payload['details']['oracle'] == {'available': True, 'used_for_scoring': False, 'used_for_ranking': False, 'used_for_stop': True, 'stop_reason': 'known_key_execution_completed', 'mode': 'unknown'}

@pytest.mark.parametrize('reserved_key', ['report_contract', 'oracle_use', 'truth_data_policy', 'reproducibility'])
def test_caller_details_cannot_overwrite_generated_solver_report_contract_sections(reserved_key: str) -> None:
    with pytest.raises(ValueError, match=reserved_key):
        _build_report(solver_name='beam', requested_seed=None, effective_seed=0, normalized_params={'beam_width': 4}, details={reserved_key: 'caller supplied'})
