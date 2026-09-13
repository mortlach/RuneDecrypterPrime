"""Cheap wiring and failure-path contracts; never execute the heavy proof."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / '.github/workflows'
PUSH_GATE = WORKFLOWS / 'rdp_v1_full_ci.yml'
FULL_PROOF = WORKFLOWS / 'rdp_v1_full_proof.yml'
PACKAGES = WORKFLOWS / 'rdp_v1_wheel_build_proof.yml'
SHA = 'a' * 40
pytestmark = pytest.mark.tier_a


def _job(name: str, workflow: Path = FULL_PROOF) -> str:
    text = workflow.read_text(encoding='utf-8')
    match = re.search(rf'^  {re.escape(name)}:\n(.*?)(?=^  [\w-]+:\n|\Z)', text, re.M | re.S)
    assert match, name
    if workflow == FULL_PROOF and name == 'native-packages':
        assert 'uses: ./.github/workflows/rdp_v1_wheel_build_proof.yml' in match[1]
        return _job('build-packages', PACKAGES)
    return match[1]


def _steps(job: str) -> dict[str, str]:
    return dict(re.findall(r'^      - name: ([^\n]+)\n(.*?)(?=^      - name: |\Z)', job, re.M | re.S))


def _run(step: str) -> str:
    match = re.search(r'^        run: (.*)', step, re.M)
    assert match, step
    if match[1] != '|':
        return match[1]
    return textwrap.dedent(step[match.end() + 1:]).strip()


def _code(job: str, step: str) -> str:
    selected = _steps(_job(job))[step]
    assert 'shell: python' in selected
    code = _run(selected)
    assert '$' + '{{' not in code, 'Use env, not Python expression interpolation'
    return code


def _execute(code, tmp_path, monkeypatch, **environment):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_SHA', SHA)
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path / 'step-summary.md'))
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(SystemExit) as stopped:
        exec(compile(code, '<workflow-evidence>', 'exec'), {'__name__': '__main__'})
    return stopped.value.code, (tmp_path / 'step-summary.md').read_text(encoding='utf-8')


def test_normal_gate_remains_automatic_ci_light_and_release_tutorials():
    text = PUSH_GATE.read_text(encoding='utf-8')
    assert 'name: RDP V1 push gate' in text
    for event in ('push', 'pull_request', 'workflow_dispatch'):
        assert f'\n  {event}:\n' in text
    assert '"prelease/**"' in text
    assert 'python tools/ci/install_light.py' in text
    assert '"not full_assets"' in text
    assert 'TutorialRunSet.RELEASE' in text
    assert 'python install.py' not in text
    assert 'python tools/run_validation.py' not in text


def test_full_proof_has_only_dispatch_and_unfiltered_main_push():
    text = FULL_PROOF.read_text(encoding='utf-8')
    triggers = text.split('\non:\n', 1)[1].split('\npermissions:', 1)[0].strip()
    assert triggers == 'workflow_dispatch:\n  push:\n    branches:\n      - main'
    assert '\n  pull_request:' not in text
    assert 'contents: read' in text
    assert 'continue-on-error:' not in text
    assert 'cancel-in-progress: true' not in text


def test_independent_jobs_and_fail_fast_false_matrices():
    text = FULL_PROOF.read_text(encoding='utf-8')
    jobs = re.findall(r'^  ([\w-]+):\n', text.split('\njobs:\n', 1)[1], re.M)
    assert jobs == ['native-validation', 'native-packages', 'pyodide', 'release-proof-summary']
    for name in ('native-validation', 'native-packages'):
        job = _job(name)
        assert 'os: [windows-latest, ubuntu-latest]' in job
        assert 'runs-on: ${{ matrix.os }}' in job
        assert 'fail-fast: false' in job
        assert 'python-version: "3.11"' in job
        if name == 'native-validation':
            assert '\n    needs:' not in job
        else:
            assert 'needs: resolve-source' in job
    for name in ('native-validation', 'pyodide'):
        assert 'ref: ${{ github.sha }}' in _job(name)
    assert 'ref: ${{ needs.resolve-source.outputs.sha }}' in _job('native-packages')


def test_full_native_validation_uses_the_real_catalogue_without_overrides():
    from tools import run_validation as validator
    assert validator.RUN_SET == 'all'
    assert validator.INCLUDE_LONG_P7C7_EXAMPLE is True
    assert validator.DRY_RUN is False
    jobs = validator.build_jobs(validator.RUN_SET)
    assert len(jobs) == 53
    assert jobs[0].args == ('-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests')
    assert sum(job.args[-1] == 'tutorials.v1.examples.' + validator.P7C7_EXAMPLE for job in jobs) == 1
    job = _job('native-validation')
    steps = _steps(job)
    assert _run(steps['Install and verify the canonical full_v1 asset profile']) == 'python install.py'
    assert _run(steps['Run canonical full validation including production P7/C7']) == 'python tools/run_validation.py'
    assert 'install_light.py' not in job and 'not full_assets' not in job
    assert 'RDP_OUTPUT_ROOT: ${{ github.workspace }}/output' in job
    preflight = _code('native-validation', 'Verify the unchanged canonical 53-job selection')
    for token in ("validator.RUN_SET == 'all'", 'validator.INCLUDE_LONG_P7C7_EXAMPLE is True',
                  'validator.DRY_RUN is False', 'len(jobs) == 53'):
        assert token in preflight
    assert 'timeout-minutes: 360' in job
    assert not re.search(r'validator\.(RUN_SET|INCLUDE_LONG_P7C7_EXAMPLE|DRY_RUN) = ', job)
    tutorials = steps['Run representative V1 examples with full assets']
    assert 'TutorialRunSet.FULL_ASSET_EXAMPLES' in tutorials
    assert "!cancelled() && steps.install.outcome == 'success'" in tutorials


def test_native_packages_reuse_qualified_build_and_installed_artifact_contracts():
    job = _job('native-packages')
    for version in ('3.11', '3.12', '3.13', '3.14'):
        tag = 'cp' + version.replace('.', '')
        assert f'{{version: "{version}", tag: "{tag}"}}' in job
        assert f'          - "{version}"' in PUSH_GATE.read_text(encoding='utf-8')
    assert len(re.findall(r'\{version:', job)) == 4
    for setting in ('CIBW_BUILD: "${{ matrix.python.tag }}-*"', 'CIBW_SKIP: "*-musllinux_*"',
                    'python {project}/tools/ci/a5_installed_wheel_smoke.py'):
        assert setting in job
    steps = _steps(job)
    assert _run(steps['Build and isolate-test the selected CPython wheel']) == 'python -m cibuildwheel --output-dir wheelhouse'
    assert _run(steps['Validate wheel and sdist boundaries']) == 'python tools/ci/a5_artifact_contract.py'
    assert 'python install.py' not in job
    assert 'CIBW_ARCHS_WINDOWS: "AMD64"' in job
    assert 'CIBW_ARCHS_LINUX: "x86_64"' in job
    assert 'matrix.python.version' in steps['Upload proven native package artifacts']
    smoke = (REPO_ROOT / 'tools/ci/a5_installed_wheel_smoke.py').read_text(encoding='utf-8')
    for module in ('rdp.scoring.language_model._fastlm', 'rdp.scoring.hamming._hamming',
                   'rdp.scoring.span_hamming._span_hamming_fast'):
        assert module in smoke


def test_catalogue_preflight_runs_from_a_temporary_python_script(tmp_path):
    # GitHub's shell: python writes a temporary script, not python -c.
    script = tmp_path / 'preflight.py'
    script.write_text(_code('native-validation', 'Verify the unchanged canonical 53-job selection'), encoding='utf-8')
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT, text=True).strip()
    environment = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
    environment.update(GITHUB_SHA=sha, PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-B', str(script)], cwd=REPO_ROOT, env=environment,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_pyodide_procedure_is_exactly_the_qualified_manual_recipe():
    qualified = _steps(_job('pyodide-wheel', WORKFLOWS / 'rdp_v1_pyodide_wheel.yml'))
    # The full proof corrects the legacy recipe's stale test count only.
    qualified = {
        name.replace('(28 tests)', '(29 tests)'): step.replace(
            "assert sum(int(s.attrib['tests']) for s in suites) == 28",
            "assert sum(int(s.attrib['tests']) for s in suites) == 29",
        ).replace("('Native tests', '28 PASS')", "('Native tests', '29 PASS')")
        for name, step in qualified.items()
    }
    release = _steps(_job('pyodide'))
    assert release.keys() == qualified.keys()
    for name, step in qualified.items():
        if '\n        run:' in '\n' + step:
            assert _run(release[name]) == _run(step), name
    job = _job('pyodide')
    for token in ('timeout-minutes: 20', 'tools/pyodide/versions.json',
                  'bash tools/pyodide/build_wheel.sh', 'node tools/pyodide/run_smoke.mjs',
                  'dirname -- "$EMSDK_NODE"', "{f'B{i}' for i in range(1, 9)}", '== 29',
                  "('failures', 'errors', 'skipped')", "build['source_revision'] == os.environ['GITHUB_SHA']",
                  "build['sha256'] == smoke['wheel']['sha256'] == digest"):
        assert token in job
    assert 'Focused native safety checks (29 tests)' in job
    assert "('Native tests', '29 PASS')" in job
    text = FULL_PROOF.read_text(encoding='utf-8')
    assert 'Pyodide B1-B8 / 29 native safety tests' in text
    assert not re.search(r'\b28\b', text)


def test_evidence_uploads_are_sha_identified_and_failures_keep_native_logs():
    steps = _steps(_job('native-validation'))
    for name in ('Record and enforce native validation evidence', 'Upload full-proof logs', 'Upload compact native status'):
        assert 'if: always()' in steps[name]
    for path in ('output/install/**/*.log', 'output/install/**/*.json', 'output/validation/**',
                 'output/test_logs/*.log', 'output/tutorial_logs/**/*.txt'):
        assert path in steps['Upload full-proof logs']
    packages = _steps(_job('native-packages'))['Upload proven native package artifacts']
    for path in ('wheelhouse/*.whl', 'dist/*.tar.gz', 'output/package-proof/SHA256SUMS.txt'):
        assert path in packages
    for name in ('native-validation', 'native-packages', 'pyodide'):
        for step in _steps(_job(name)).values():
            if 'uses: actions/upload-artifact@v4' in step:
                artifact_name = re.search(r'^          name: (.*)$', step, re.M)
                source = '${{ needs.resolve-source.outputs.sha }}' if name == 'native-packages' else '${{ github.sha }}'
                assert artifact_name and source in artifact_name[1]
                if name != 'pyodide':
                    assert '${{ matrix.os }}' in artifact_name[1]
                assert 'overwrite: true' in step


def test_final_summary_requires_every_job_and_retains_the_cuda_boundary():
    job = _job('release-proof-summary')
    assert 'if: always()' in job
    assert 'needs: [native-validation, native-packages, pyodide]' in job
    for dependency in ('native-validation', 'native-packages', 'pyodide'):
        assert f'needs.{dependency}.result' in job
    assert 'pattern: rdp-v1-native-status-*-${{ github.sha }}' in job
    assert 'merge-multiple: true' in job
    assert 'prior qualified CUDA validation is separate' in job
    assert 'raise SystemExit(0 if overall else 1)' in job


def test_all_inline_python_steps_compile_without_expression_injection():
    for name in ('native-validation', 'native-packages', 'release-proof-summary'):
        for step_name, step in _steps(_job(name)).items():
            if 'shell: python' in step:
                compile(_code(name, step_name), '<workflow-python>', 'exec')
    code = _run(_steps(_job('collect-packages', PACKAGES))['Verify and collect the complete native package set'])
    assert '$' + '{{' not in code
    compile(code, '<package-collection>', 'exec')


@pytest.mark.parametrize('defect', [None, 'missing', 'malformed', 'short', 'failed_job',
                                  'failed_summary', 'wrong_sha', 'dirty', 'duplicates',
                                  'install', 'tutorials', 'validation'])
def test_native_receipt_enforces_53_real_passes_and_source_identity(tmp_path, monkeypatch, defect):
    summary = {'commit': SHA, 'working_tree_status': [], 'status': 'passed', 'elapsed_seconds': 123.0,
               'jobs': [{'name': f'job-{index}', 'status': 'passed'} for index in range(53)]}
    if defect == 'short':
        summary['jobs'].pop()
    elif defect == 'failed_job':
        summary['jobs'][0]['status'] = 'failed'
    elif defect == 'failed_summary':
        summary['status'] = 'failed'
    elif defect == 'wrong_sha':
        summary['commit'] = 'b' * 40
    elif defect == 'dirty':
        summary['working_tree_status'] = [' M README.md']
    elif defect == 'duplicates':
        summary['jobs'][0]['name'] = summary['jobs'][1]['name']
    if defect != 'missing':
        destination = tmp_path / 'output/validation/fixture/summary.json'
        destination.parent.mkdir(parents=True)
        destination.write_text('{' if defect == 'malformed' else json.dumps(summary), encoding='utf-8')
    environment = {key.upper() + '_RESULT': 'failure' if defect == key else 'success'
                   for key in ('install', 'validation')}
    environment['TUTORIAL_RESULT'] = 'failure' if defect == 'tutorials' else 'success'
    code, output = _execute(_code('native-validation', 'Record and enforce native validation evidence'),
                            tmp_path, monkeypatch, PROOF_OS='windows-latest', **environment)
    receipt = json.loads((tmp_path / 'output/release-proof/windows-latest.json').read_text())
    assert code == (0 if defect is None else 1)
    assert receipt['status'] == ('PASS' if defect is None else 'FAIL')
    assert receipt['source_commit'] == SHA
    assert 'Passed jobs / expected jobs' in output


def _native_receipts(tmp_path):
    directory = tmp_path / 'native-status'
    directory.mkdir()
    for platform in ('windows-latest', 'ubuntu-latest'):
        receipt = {'source_commit': SHA, 'os': platform, 'status': 'PASS',
                   'passed_jobs': 53, 'expected_jobs': 53, 'install': 'success',
                   'validation': 'success', 'tutorials': 'success'}
        (directory / (platform + '.json')).write_text(json.dumps(receipt), encoding='utf-8')


@pytest.mark.parametrize('dependency', ['NATIVE_RESULT', 'PACKAGE_RESULT', 'PYODIDE_RESULT'])
@pytest.mark.parametrize('outcome', ['success', 'failure', 'cancelled', 'skipped'])
def test_final_summary_fails_for_any_nonpassing_required_job(tmp_path, monkeypatch, dependency, outcome):
    _native_receipts(tmp_path)
    environment = dict(NATIVE_RESULT='success', PACKAGE_RESULT='success', PYODIDE_RESULT='success')
    environment[dependency] = outcome
    code, output = _execute(_code('release-proof-summary', 'Summarize and enforce every required hosted proof'),
                            tmp_path, monkeypatch, **environment)
    assert code == (0 if outcome == 'success' else 1)
    assert f'| Overall release proof | {"PASS" if code == 0 else "FAIL"} |' in output
    assert 'prior qualified CUDA validation is separate' in output


@pytest.mark.parametrize('defect', ['missing', 'wrong_sha', 'wrong_os', 'failed', 'short', 'tutorials', 'malformed'])
def test_final_summary_rejects_missing_or_invalid_platform_evidence(tmp_path, monkeypatch, defect):
    _native_receipts(tmp_path)
    path = tmp_path / 'native-status/windows-latest.json'
    receipt = json.loads(path.read_text())
    if defect == 'missing':
        path.unlink()
    else:
        if defect == 'wrong_sha':
            receipt['source_commit'] = 'b' * 40
        elif defect == 'wrong_os':
            receipt['os'] = 'ubuntu-latest'
        elif defect == 'failed':
            receipt['status'] = 'FAIL'
        elif defect == 'short':
            receipt['passed_jobs'] = 52
        elif defect == 'tutorials':
            receipt['tutorials'] = 'skipped'
        path.write_text('{' if defect == 'malformed' else json.dumps(receipt), encoding='utf-8')
    code, output = _execute(_code('release-proof-summary', 'Summarize and enforce every required hosted proof'),
                            tmp_path, monkeypatch, NATIVE_RESULT='success', PACKAGE_RESULT='success', PYODIDE_RESULT='success')
    assert code == 1
    assert '| 53-job validation matrix | FAIL |' in output
    assert '| Overall release proof | FAIL |' in output


def test_native_checksum_step_binds_both_artifacts_to_source_sha(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_SHA', 'b' * 40)
    monkeypatch.setenv('SOURCE_SHA', SHA)
    monkeypatch.setenv('WHEEL_TAG', 'cp312')
    monkeypatch.setenv('PROOF_OS', 'windows-latest')
    monkeypatch.setattr(subprocess, 'check_output', lambda *args, **kwargs: SHA + '\n')
    names = ('wheelhouse/fixture-1.0.0-cp312-cp312-win_amd64.whl', 'dist/fixture.tar.gz')
    for name in names:
        path = tmp_path / name
        path.parent.mkdir()
        path.write_bytes(name.encode())
    exec(compile(_code('native-packages', 'Record native artifact identity and checksums'), '<checksums>', 'exec'), {})
    evidence = (tmp_path / 'output/package-proof/SHA256SUMS.txt').read_text()
    assert evidence.startswith(f'# Source commit: {SHA}\n')
    for name in names:
        assert f'{hashlib.sha256(name.encode()).hexdigest()}  {name}' in evidence


def test_selected_source_is_resolved_once_for_builds_tests_and_collection(tmp_path, monkeypatch):
    packages = PACKAGES.read_text(encoding='utf-8')
    for event in ('workflow_dispatch', 'workflow_call'):
        assert f'  {event}:\n    inputs:\n      source_ref:' in packages
    resolver = _job('resolve-source', PACKAGES)
    assert 'ref: ${{ inputs.source_ref || github.sha }}' in resolver
    code = _run(_steps(resolver)['Record resolved source commit'])
    monkeypatch.setenv('GITHUB_SHA', 'b' * 40)
    monkeypatch.setenv('GITHUB_OUTPUT', str(tmp_path / 'output'))
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path / 'summary'))
    monkeypatch.setattr(subprocess, 'check_output', lambda *args, **kwargs: SHA + '\n')
    exec(compile(code, '<resolve-source>', 'exec'), {})
    assert (tmp_path / 'output').read_text() == f'sha={SHA}\n'
    assert SHA in (tmp_path / 'summary').read_text()
    assert 'b' * 40 in (tmp_path / 'summary').read_text()
    selected = _job('validate-source', PACKAGES)
    assert "if: ${{ inputs.source_ref != '' }}" in selected
    assert 'uses: ./.github/workflows/rdp_v1_full_ci.yml' in selected
    assert 'source_ref: ${{ needs.resolve-source.outputs.sha }}' in selected
    gate = PUSH_GATE.read_text(encoding='utf-8')
    assert 'ref: ${{ inputs.source_ref || github.sha }}' in gate
    assert "assert sha == os.environ['SOURCE_SHA']" in gate
    assert "'pip', 'install', 'setuptools'" in gate
    for job in ('build-packages', 'collect-packages'):
        assert 'SOURCE_SHA: ${{ needs.resolve-source.outputs.sha }}' in _job(job, PACKAGES)
    collection = _job('collect-packages', PACKAGES)
    assert 'needs: [resolve-source, build-packages, validate-source]' in collection
    assert "needs.build-packages.result == 'success'" in collection
    assert "needs.validate-source.result == 'success' || needs.validate-source.result == 'skipped'" in collection


def test_native_checksums_reject_a_checkout_that_is_not_the_selected_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SOURCE_SHA', SHA)
    monkeypatch.setattr(subprocess, 'check_output', lambda *args, **kwargs: 'b' * 40 + '\n')
    with pytest.raises(AssertionError):
        exec(compile(_code('native-packages', 'Record native artifact identity and checksums'), '<checksums>', 'exec'), {})
    assert not (tmp_path / 'output/package-proof/SHA256SUMS.txt').exists()


@pytest.mark.parametrize('filename', [
    'fixture-1.0.0-cp311-cp311-win_amd64.whl',
    'fixture-1.0.0-cp312-cp312-win32.whl',
    'fixture-1.0.0-cp312-cp312-manylinux_2_28_x86_64.whl',
])
def test_native_checksum_step_rejects_wrong_python_or_platform(tmp_path, monkeypatch, filename):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_SHA', 'b' * 40)
    monkeypatch.setenv('SOURCE_SHA', SHA)
    monkeypatch.setenv('WHEEL_TAG', 'cp312')
    monkeypatch.setenv('PROOF_OS', 'windows-latest')
    monkeypatch.setattr(subprocess, 'check_output', lambda *args, **kwargs: SHA + '\n')
    for name in ('wheelhouse/' + filename, 'dist/fixture.tar.gz'):
        path = tmp_path / name
        path.parent.mkdir()
        path.write_bytes(b'fixture')
    with pytest.raises(AssertionError):
        exec(compile(_code('native-packages', 'Record native artifact identity and checksums'), '<checksums>', 'exec'), {})
    assert not (tmp_path / 'output/package-proof/SHA256SUMS.txt').exists()


@pytest.mark.parametrize('defect', [None, 'missing', 'wrong_sha', 'corrupt', 'duplicate', 'wrong_python'])
def test_native_bundle_requires_all_eight_verified_wheels(tmp_path, monkeypatch, defect):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_SHA', 'b' * 40)
    monkeypatch.setenv('SOURCE_SHA', SHA)
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path / 'summary.md'))
    last_wheel = None
    for platform in ('windows-latest', 'ubuntu-latest'):
        for version in ('3.11', '3.12', '3.13', '3.14'):
            folder = tmp_path / 'packages' / f'rdp-v1-packages-{platform}-py{version}-{SHA}'
            tag = 'cp' + version.replace('.', '')
            suffix = 'win_amd64' if platform == 'windows-latest' else 'manylinux_2_28_x86_64'
            wheel = folder / 'wheelhouse' / f'fixture-1.0.0-{tag}-{tag}-{suffix}.whl'
            sdist = folder / 'dist/fixture-1.0.0.tar.gz'
            lines = [f'# Source commit: {SHA}']
            for path in (wheel, sdist):
                path.parent.mkdir(parents=True)
                path.write_bytes(f'{platform} {version}'.encode())
                lines.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(folder).as_posix()}')
            checksum = folder / 'output/package-proof/SHA256SUMS.txt'
            checksum.parent.mkdir(parents=True)
            checksum.write_text('\n'.join(lines) + '\n')
            last_wheel = wheel
    if defect == 'missing':
        last_wheel.unlink()
    elif defect == 'wrong_sha':
        checksum.write_text(checksum.read_text().replace(SHA, 'b' * 40))
    elif defect == 'corrupt':
        last_wheel.write_bytes(b'tampered')
    elif defect == 'duplicate':
        (last_wheel.parent / 'extra.whl').write_bytes(b'extra')
    elif defect == 'wrong_python':
        last_wheel.rename(last_wheel.with_name(last_wheel.name.replace('cp314', 'cp310')))
    code = _run(_steps(_job('collect-packages', PACKAGES))['Verify and collect the complete native package set'])
    if defect:
        with pytest.raises((AssertionError, FileNotFoundError)):
            exec(compile(code, '<package-collection>', 'exec'), {})
        assert not (tmp_path / 'release-packages/SHA256SUMS.txt').exists()
    else:
        exec(compile(code, '<package-collection>', 'exec'), {})
        destination = tmp_path / 'release-packages'
        assert len(list(destination.glob('*.whl'))) == 8
        assert len(list(destination.glob('*.tar.gz'))) == 1
        assert len((destination / 'SHA256SUMS.txt').read_text().splitlines()) == 10
        assert (destination / 'fixture-1.0.0.tar.gz').read_bytes() == b'ubuntu-latest 3.11'
