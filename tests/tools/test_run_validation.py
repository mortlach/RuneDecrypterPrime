from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from tools import run_validation as runner


def _run(tmp_path, jobs, **kwargs):
    root = tmp_path / 'repo'
    root.mkdir(exist_ok=True)
    code, directory = runner.run_jobs(jobs, root=root, output_root=tmp_path / 'evidence', **kwargs)
    return code, directory, json.loads((directory / 'summary.json').read_text())


def _job(name, source, evidence='exit_code'):
    return runner.Job(name, ('-c', source), evidence)


def test_all_catalogue_has_each_example_and_workbook_once_without_campaigns():
    jobs = runner.build_jobs('all')
    modules = [j.args[-1] for j in jobs[1:]]
    assert len(jobs) == 44  # one pytest selection, ten stops, 24 examples, nine workbooks
    assert len(modules) == len(set(modules))
    assert sum(m.startswith('solving.solved_lp.') for m in modules) == 9
    assert not any(name in m for m in modules for name in runner.EXCLUDED_EXAMPLES)
    assert not any('cipher_development' in m or 'campaign' in m for m in modules)
    assert 'tests' in jobs[0].args
    assert all(f'--ignore={p}' in jobs[0].args for p in runner.EXCLUDED_TESTS)
    assert runner.build_jobs('smoke')[0].args[5] == 'tests/tools/test_run_validation.py'
    p7c7 = runner.build_jobs('p7c7')
    assert len(p7c7) == 1
    assert p7c7[0].args[-1] == 'tutorials.v1.examples.periodic_columnar_p7_column_then_substitution'
    with pytest.raises(ValueError, match='Unknown run set'):
        runner.build_jobs('campaign')


def test_unclassified_example_blocks_execution(tmp_path):
    example = tmp_path / 'tutorials/v1/examples/new_campaign.py'
    example.parent.mkdir(parents=True)
    example.write_text('raise RuntimeError("must not execute")')
    with pytest.raises(ValueError, match='catalogue changed'):
        runner.build_jobs('all', tmp_path)


def test_failure_continues_and_preserves_unicode_and_native_evidence(tmp_path, capsys):
    jobs = [_job('bad', 'raise SystemExit(7)'),
            _job('good', "from pathlib import Path; print('áš áš©'); import os; out=Path(os.environ['RDP_OUTPUT_ROOT']); "
                        "(out/'result.txt').write_text('proof')")]
    code, directory, summary = _run(tmp_path, jobs)
    assert code == 1
    assert [r['status'] for r in summary['jobs']] == ['failed', 'passed']
    assert summary['jobs'][0]['exit_code'] == 7
    assert 'áš áš©' in (directory / 'good.log').read_text(encoding='utf-8')
    assert (directory / 'good_artifacts/result.txt').read_text() == 'proof'
    assert not (tmp_path / 'repo/output').exists()
    assert 'áš áš©' in capsys.readouterr().out


def test_no_runner_time_limits():
    import inspect
    assert 'total_timeout' not in inspect.signature(runner.run_jobs).parameters
    assert 'timeout' not in runner.Job.__dataclass_fields__


def test_fail_fast_marks_unstarted_jobs(tmp_path):
    code, _, summary = _run(tmp_path, [_job('bad', 'raise SystemExit(1)'),
                                      _job('never', 'raise RuntimeError()')], stop_on_failure=True)
    assert code == 1
    assert summary['jobs'][1]['status'] == 'not_run'
    assert summary['stop_reason'] == 'stop_on_failure'


def test_summary_reports_no_time_limit(tmp_path):
    code, _, summary = _run(tmp_path, [_job('ordinary', 'pass')])
    assert code == 0
    assert summary['time_limits'] is None


def test_dry_run_does_not_execute(tmp_path):
    code, directory, summary = _run(tmp_path, [_job('never', 'raise RuntimeError()')], dry_run=True)
    assert code == 0 and summary['status'] == 'planned'
    assert not (directory / 'never.log').exists()


def test_existing_output_is_preserved_and_repo_output_is_supported(tmp_path):
    root = tmp_path / 'repo'
    (root / 'output').mkdir(parents=True)
    sentinel = root / 'output/old.txt'
    sentinel.write_text('keep')
    code, directory = runner.run_jobs([_job('x', 'pass')], root=root,
                                      output_root=root / 'output/validation')
    assert code == 0
    assert sentinel.read_text() == 'keep'
    assert directory.is_relative_to(root / 'output/validation')


def test_zero_exit_without_solved_evidence_fails(tmp_path):
    code, _, summary = _run(tmp_path, [_job('unsolved', "print('status: solved')", evidence='workbook')])
    assert code == 1 and 'Workbook did not report' in summary['jobs'][0]['error']


def test_pytest_skip_counts_remain_visible(tmp_path):
    junit = tmp_path / 'tests.xml'
    junit.write_text('<testsuites><testsuite><testcase/><testcase><skipped/></testcase>'
                     '</testsuite></testsuites>')
    counts = runner._evidence(_job('tests', 'pass', evidence='pytest'), tmp_path / 'unused', junit)
    assert counts == {'tests': 2, 'skipped': 1, 'failures': 0, 'errors': 0}


def test_interrupt_preserves_summary_and_unstarted_jobs(tmp_path, monkeypatch):
    def interrupt(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(runner.time, 'sleep', interrupt)
    code, _, summary = _run(tmp_path, [_job('active', 'import time; time.sleep(30)'), _job('next', 'pass')])
    assert code == 130
    assert summary['status'] == 'interrupted'
    assert [r['status'] for r in summary['jobs']] == ['interrupted', 'not_run']


@pytest.mark.parametrize('name', ['two_period_cribs', 'two_period_cribs_interruptors',
                                  'two_period_cribs_p13_p31_search'])
def test_crib_examples_import_without_running_search(name):
    module = importlib.import_module(f'tutorials.v1.examples.{name}')
    assert callable(module.run_tutorial)


def test_gpu_selection_cannot_pass_with_skipped_tests(tmp_path):
    junit = tmp_path / 'tests.xml'
    junit.write_text('<testsuites><testsuite><testcase/><testcase><skipped/></testcase>'
                     '</testsuite></testsuites>')
    with pytest.raises(ValueError, match='incomplete'):
        runner._evidence(_job('gpu', 'pass', 'pytest_gpu'), tmp_path / 'unused', junit)
    assert runner.build_jobs('gpu')[0].evidence == 'pytest_gpu'
