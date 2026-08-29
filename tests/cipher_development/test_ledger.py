from __future__ import annotations
import json
import math
from pathlib import Path
import pytest
from cipher_development.shared.ledger import ExperimentLedgerRow, append_ledger_row, read_ledger

def _row(**overrides) -> ExperimentLedgerRow:
    values = {'schema': 'rdp_cipher_development_experiment_ledger.v1', 'recorded_at': '2026-07-21T12:00:00+00:00', 'run_id': 'run-1', 'campaign_id': 'two_period_overlay', 'experiment_id': 'wp1', 'benchmark_id': 'alice_308', 'question': 'Does this retain evidence?', 'hypothesis': 'The evidence contract is sufficient.', 'alternative': 'The evidence contract omits required fields.', 'configuration_hash': 'abc123', 'wli_mode': 'with_wli', 'truth_policy': 'benchmark_only', 'mechanisms': ('evidence_reproducibility',), 'budget_seconds': 10.0, 'budget_evaluations': 100, 'lesson_ids': ('CSL-001',), 'status': 'completed', 'decision': 'refine', 'stop_category': 'budget', 'stop_reason': 'time_budget', 'elapsed_s': 1.5, 'telemetry': {'eval_keys': 10}, 'result_summary': {'best_score': 0.5}, 'result_relpath': 'run-1/artifacts/experiment_result.json', 'git_commit': None, 'git_dirty': None}
    values.update(overrides)
    return ExperimentLedgerRow(**values)

def test_missing_ledger_is_empty(tmp_path: Path) -> None:
    assert read_ledger(tmp_path / 'missing.jsonl') == ()

def test_append_is_ordered_and_preserves_existing_line_exactly(tmp_path: Path) -> None:
    path = tmp_path / 'campaign' / 'experiment_ledger.jsonl'
    first = _row()
    second = _row(run_id='run-2', experiment_id='wp1b', decision='promote')
    append_ledger_row(path, first)
    first_line = path.read_text(encoding='utf-8')
    append_ledger_row(path, second)
    text = path.read_text(encoding='utf-8')
    assert text.startswith(first_line)
    rows = read_ledger(path)
    assert [row.run_id for row in rows] == ['run-1', 'run-2']

def test_blank_and_malformed_lines_report_line_number(tmp_path: Path) -> None:
    path = tmp_path / 'ledger.jsonl'
    path.write_text(json.dumps(_row().to_json_dict()) + '\n\n', encoding='utf-8')
    with pytest.raises(ValueError, match='line 2'):
        read_ledger(path)
    path.write_text(json.dumps(_row().to_json_dict()) + '\n{bad\n', encoding='utf-8')
    with pytest.raises(ValueError, match='line 2'):
        read_ledger(path)

def test_completed_requires_decision_but_failed_may_omit_it() -> None:
    with pytest.raises(ValueError, match='require a decision'):
        _row(decision=None)
    failed = _row(status='failed', decision=None, stop_category='error', stop_reason='exception')
    assert failed.decision is None

@pytest.mark.parametrize('field', ['wli_mode', 'truth_policy', 'mechanisms', 'stop_category'])
def test_ledger_enum_domains_are_validated(field: str) -> None:
    value = ('nonsense',) if field == 'mechanisms' else 'nonsense'
    with pytest.raises(ValueError, match=field):
        _row(**{field: value})

def test_result_relpath_must_be_campaign_relative_posix(tmp_path: Path) -> None:
    absolute = (tmp_path.resolve() / 'result.json').as_posix()
    for bad in (absolute, '../outside/result.json', 'run\\result.json'):
        with pytest.raises(ValueError):
            _row(result_relpath=bad)

def test_non_finite_values_and_invalid_rows_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _row(elapsed_s=math.inf)
    with pytest.raises(ValueError):
        _row(result_summary={'score': math.nan})
    with pytest.raises(ValueError):
        _row(budget_seconds=math.inf)
    with pytest.raises(ValueError):
        _row(budget_evaluations=0)
    with pytest.raises(ValueError, match='CSL-NNN'):
        _row(lesson_ids=('CSL-1',))
    with pytest.raises(ValueError, match='unique'):
        _row(lesson_ids=('CSL-001', 'CSL-001'))
    path = tmp_path / 'ledger.jsonl'
    payload = _row().to_json_dict()
    payload['status'] = 'mystery'
    path.write_text(json.dumps(payload) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='line 1'):
        read_ledger(path)

def test_ledger_line_contains_no_absolute_paths(tmp_path: Path) -> None:
    path = tmp_path / 'ledger.jsonl'
    append_ledger_row(path, _row())
    line = path.read_text(encoding='utf-8')
    assert str(tmp_path.resolve()) not in line
    assert 'result_relpath' in line
