from __future__ import annotations

import importlib
import json

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
    # pytest, ten tutorials, three solving starts, six LP lessons,
    # 24 examples (including the long P7/C7 job), and nine workbooks
    assert runner.INCLUDE_LONG_P7C7_EXAMPLE is True
    assert len(jobs) == 53
    assert len(modules) == len(set(modules))
    assert [m for m in modules if m.startswith('solving.getting_started.')] == [
        'solving.getting_started.load_source',
        'solving.getting_started.prepare_search',
        'solving.getting_started.run_search',
    ]
    assert [m for m in modules if m.startswith('solving.lp_getting_started.')] == [
        f'solving.lp_getting_started.0{lesson}_{name}'
        for lesson, name in (
            (1, 'load_welcome_pilgrim'),
            (2, 'try_vigenere'),
            (3, 'add_interruptors'),
            (4, 'try_reverse_shifts'),
            (5, 'let_rdp_search'),
            (6, 'explore_an_end'),
        )
    ]
    assert sum(m.startswith('solving.solved_lp.') for m in modules) == 9
    assert not any(name in m for m in modules for name in runner.EXCLUDED_EXAMPLES)
    assert sum(runner.P7C7_EXAMPLE in m for m in modules) == 1
    assert not any('cipher_development' in m or 'campaign' in m for m in modules)
    assert 'tests' in jobs[0].args
    assert runner.EXCLUDED_TESTS == ()
    assert not any(arg.startswith('--ignore=') for arg in jobs[0].args)
    assert runner.build_jobs('smoke')[0].args[5] == 'tests/tools/test_run_validation.py'
    p7c7 = runner.build_jobs('p7c7')
    assert len(p7c7) == 1
    assert p7c7[0].args[-1] == 'tutorials.v1.examples.periodic_columnar_p7_column_then_substitution'
    with pytest.raises(ValueError, match='Unknown run set'):
        runner.build_jobs('campaign')


def test_documented_selection_lists_every_collected_test_file():
    selection = (runner.ROOT / 'tools/validation_selection.md').read_text(encoding='utf-8')
    listed = {
        line.removeprefix('- `').removesuffix('`')
        for line in selection.splitlines()
        if line.startswith('- `tests/') and line.endswith('.py`')
    }
    expected = {
        path.relative_to(runner.ROOT).as_posix()
        for path in (runner.ROOT / 'tests').rglob('test_*.py')
    }
    assert listed == expected


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


def test_summary_save_retries_a_transient_windows_sharing_violation(tmp_path, monkeypatch):
    destination = tmp_path / 'summary.json'
    destination.write_text('{}\n')
    original_replace = runner.Path.replace
    calls = 0

    def transient_replace(path, target):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise PermissionError('transient sharing violation')
        return original_replace(path, target)

    delays = []
    monkeypatch.setattr(runner.Path, 'replace', transient_replace)
    monkeypatch.setattr(runner.time, 'sleep', delays.append)
    runner._save(destination, {'status': 'running'})

    assert calls == 3
    assert delays == [runner.SUMMARY_REPLACE_RETRY_SECONDS] * 2
    assert json.loads(destination.read_text()) == {'status': 'running'}


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


@pytest.mark.parametrize('evidence', ['pytest', 'pytest_gpu'])
def test_pytest_fixtures_stay_outside_checkout_with_retained_evidence_inside(tmp_path, evidence):
    root = tmp_path / 'checkout'
    root.mkdir()
    (root / 'test_fixture_location.py').write_text(
        'import json, os\n'
        'from pathlib import Path\n'
        'def test_location(tmp_path, tmp_path_factory, pytestconfig):\n'
        '    checkout = Path.cwd().resolve()\n'
        '    artifacts = Path(os.environ["RDP_OUTPUT_ROOT"])\n'
        '    assert artifacts.is_absolute() and artifacts.is_relative_to(checkout)\n'
        '    assert not tmp_path.resolve().is_relative_to(checkout)\n'
        '    assert not tmp_path_factory.getbasetemp().resolve().is_relative_to(checkout)\n'
        '    assert pytestconfig.getoption("basetemp") is None\n'
        '    (artifacts / "fixture.json").write_text(json.dumps({"tmp_path": str(tmp_path)}))\n',
        encoding='utf-8',
    )
    job = runner.Job('tests', ('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                               'test_fixture_location.py'), evidence)
    code, directory = runner.run_jobs([job], root=root, output_root=root / 'output/validation')
    summary = json.loads((directory / 'summary.json').read_text())
    assert code == 0, (directory / 'tests.log').read_text(encoding='utf-8')
    assert summary['status'] == 'passed'
    row = summary['jobs'][0]
    assert row['evidence_result'] == {'tests': 1, 'skipped': 0, 'failures': 0, 'errors': 0}
    assert directory.is_relative_to(root / 'output/validation')
    assert (directory / 'tests.xml').is_file()
    assert (directory / row['artifacts'] / 'fixture.json').is_file()
    assert f'--junitxml={runner.path_from(directory / "tests.xml", root)}' in row['command']
    assert not any(arg.startswith('--basetemp') for arg in row['command'])
    assert not (directory / 'tests_tmp').exists()


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
