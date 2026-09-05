"""Run repository checks. Configure below; no command-line arguments."""
from __future__ import annotations

import codecs
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from rdp.core.config.output_paths import resolve_output_root, path_from
OUTPUT_ROOT = None  # Optional explicit validation destination; otherwise shared root/validation.
RUN_SET = 'all'  # 'smoke', 'all', 'p7c7', or 'gpu'
SHOW_JOB_OUTPUT = True
DRY_RUN = False
STOP_ON_FAILURE = False
HEARTBEAT_SECONDS = 10

# Explicit admission prevents a new campaign from silently entering the suite.
EXAMPLES = (
    'autokey', 'autokey_robust', 'columnar_transposition', 'lp_welcome_pilgrim_solve',
    'mono_substitution_ga_ltr', 'mono_substitution_ga_robust', 'mono_substitution_ga_rtl',
    'mono_substitution_hybrid_rtl', 'mono_substitution_sa_ltr', 'rail_fence',
    'repeating_multiply', 'periodic_columnar_p7_column_then_substitution',
    'scheduled_stream_lookup_p13_p31_segmented',
    'scheduled_stream_lookup_p13_primes', 'scheduled_stream_lookup_p13_sequence',
    'two_period_cribs', 'two_period_cribs_interruptors', 'two_period_cribs_p13_p31_search',
    'vigenere_general_map', 'vigenere_interruptors_exact', 'vigenere_interruptors_nontrivial',
    'vigenere_interruptors_robust', 'vigenere_interruptors_solve',
    'vigenere_known_key_and_general_map',
)
EXCLUDED_EXAMPLES = {
    'periodic_substitution': 'long qualification',
    'periodic_substitution_p7': 'long qualification',
}
EXCLUDED_TESTS = (
    'tests/cipher_development',
    'tests/tools/test_cipher_solver_campaign.py',
    'tests/tools/test_cipher_solver_campaign_rail_interruptors.py',
)


GPU_TEST_FILES = (
    'tests/ciphers/test_torch_cipher_boundary.py',
    'tests/ciphers/test_generic_map_degeneracy.py',
    'tests/scoring/test_avg_ecdf_runtime_separation.py',
    'tests/scoring/test_backend_selection_and_parity.py',
    'tests/scoring/test_objective_input_compat_runtime.py',
    'tests/scoring/test_pct_win10_stats_and_telemetry.py',
    'tests/scoring/test_scoring_integrity.py',
    'tests/scoring/test_span_hamming_integration.py',
    'tests/scoring/test_torch_avg_fulltext_stability.py',
    'tests/scoring/test_torch_batch_score_numpy_input.py',
    'tests/scoring/test_torch_hash_helpers_validation.py',
    'tests/scoring/test_torch_input_validation.py',
    'tests/scoring/test_torch_objective_contracts.py',
    'tests/scoring/test_torch_probe_loop_safety.py',
    'tests/scoring/test_torch_short_text_hamming.py',
    'tests/smoke/test_cuda_solver.py',
    'tests/torch/test_torch_scorer_optional_runtime.py',
)


@dataclass(frozen=True)
class Job:
    name: str
    args: tuple[str, ...]
    evidence: str = 'exit_code'


def build_jobs(run_set: str, root: Path = ROOT) -> list[Job]:
    if run_set not in {'smoke', 'all', 'p7c7', 'gpu'}:
        raise ValueError(f'Unknown run set: {run_set}')
    if run_set == 'gpu':
        return [Job('gpu_tests', ('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                                 *GPU_TEST_FILES), 'pytest_gpu')]
    examples_root = root / 'tutorials/v1/examples'
    found = {p.stem for p in examples_root.glob('*.py') if p.name != '__init__.py'}
    if found != set(EXAMPLES) | set(EXCLUDED_EXAMPLES):
        raise ValueError(f'Example catalogue changed; classify new/missing files: '
                         f'{sorted(found ^ (set(EXAMPLES) | set(EXCLUDED_EXAMPLES)))}')
    if run_set == 'p7c7':
        return [Job('tutorials__v1__examples__periodic_columnar_p7_column_then_substitution',
                    ('-m', 'tutorials.v1.examples.periodic_columnar_p7_column_then_substitution'))]
    getting_started = sorted((root / 'tutorials/v1/getting_started').glob('[0-9][0-9]_*.py'))
    workbooks = sorted((root / 'solving/solved_lp').glob('[0-9][0-9]_*.py'))
    if not getting_started or not workbooks:
        raise ValueError('Missing getting-started or solved-workbook catalogue')
    test_target = 'tests/tools/test_run_validation.py' if run_set == 'smoke' else 'tests'
    if not (root / test_target).exists():
        raise ValueError(f'Missing test target: {test_target}')
    pytest_args = ('-m', 'pytest', '-q', '-p', 'no:cacheprovider', test_target)
    pytest_args += tuple(f'--ignore={p}' for p in EXCLUDED_TESTS)
    jobs = [Job('tests', pytest_args, 'pytest')]
    paths = getting_started + [examples_root / f'{name}.py' for name in EXAMPLES] + workbooks
    if run_set == 'smoke':
        paths = [root / 'tutorials/v1/getting_started/01_known_key.py',
                 root / 'solving/solved_lp/01_A_Warning.py']
    for path in paths:
        relative = path.relative_to(root).with_suffix('').as_posix()
        jobs.append(Job(relative.replace('/', '__'), ('-m', relative.replace('/', '.')),
                        'workbook' if path in workbooks else 'exit_code'))
    return jobs


def _save(path: Path, value: dict) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def _stop_process_tree(process: subprocess.Popen) -> None:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def _evidence(job: Job, log: Path, junit: Path) -> dict:
    if job.evidence in {'pytest', 'pytest_gpu'}:
        cases = ET.parse(junit).getroot().findall('.//testcase')
        counts = {'tests': len(cases), 'skipped': 0, 'failures': 0, 'errors': 0}
        for case in cases:
            for tag, key in [('skipped', 'skipped'), ('failure', 'failures'), ('error', 'errors')]:
                counts[key] += int(case.find(tag) is not None)
        if not cases or counts['failures'] or counts['errors'] or counts['skipped'] == len(cases):
            raise ValueError(f'Pytest did not establish a passing test run: {counts}')
        if job.evidence == 'pytest_gpu' and counts['skipped']:
            raise ValueError(f'GPU coverage is incomplete: {counts}')
        return counts
    if job.evidence == 'workbook':
        output = log.read_text(encoding='utf-8', errors='replace')
        statuses = re.findall(r'^status:\s*(\S+)\s*$', output, re.MULTILINE)
        ratios = re.findall(r'^match_ratio:\s*([0-9.]+)\s*$', output, re.MULTILINE)
        if not statuses or not ratios or statuses[-1] != 'solved' or float(ratios[-1]) != 1.0:
            raise ValueError('Workbook did not report status: solved and match_ratio: 1.0')
        return {'status': statuses[-1], 'match_ratio': float(ratios[-1])}
    return {}


def run_jobs(jobs: list[Job], *, root: Path = ROOT, output_root: Path | None = OUTPUT_ROOT,
             stop_on_failure: bool = STOP_ON_FAILURE,
             dry_run: bool = False) -> tuple[int, Path]:
    root = root.resolve()
    output_root = (resolve_output_root(output_root) if output_root is not None
                   else resolve_output_root() / 'validation')
    if not jobs or len({j.name for j in jobs}) != len(jobs):
        raise ValueError('Jobs must be nonempty with unique names')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', j.name) for j in jobs):
        raise ValueError('Job names must be safe file names')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    run_dir = output_root / stamp
    run_dir.mkdir(parents=True)
    try:
        git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True)
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True)
    except FileNotFoundError:
        git = subprocess.CompletedProcess([], 1, '', '')
        dirty = subprocess.CompletedProcess([], 1, '', '')
    summary = {'status': 'planned' if dry_run else 'running', 'python': sys.version,
               'commit': git.stdout.strip() if git.returncode == 0 else None,
               'working_tree_status': dirty.stdout.splitlines(), 'time_limits': None,
               'excluded_examples': EXCLUDED_EXAMPLES, 'excluded_tests': list(EXCLUDED_TESTS),
               'excluded_roots': ['tools/robustness', 'cipher_development', 'solving/attempts'],
               'jobs': [dict(asdict(j), status='pending', log=f'{j.name}.log') for j in jobs]}
    summary_path = run_dir / 'summary.json'
    _save(summary_path, summary)
    print(f'Run evidence: {path_from(run_dir, root)}', flush=True)
    if dry_run:
        for job in jobs:
            print(f'[PLAN] {job.name}', flush=True)
        return 0, run_dir
    started = time.monotonic()
    interrupted = False
    stop_reason = 'completed'
    for index, (job, row) in enumerate(zip(jobs, summary['jobs']), 1):
        log_path = run_dir / row['log']
        junit = run_dir / f'{job.name}.xml'
        command = [sys.executable, '-X', 'utf8', '-u', *job.args]
        if job.evidence in {'pytest', 'pytest_gpu'}:
            command += [f'--junitxml={path_from(junit, root)}',
                        f'--basetemp={path_from(run_dir / (job.name + "_tmp"), root)}']
        env = os.environ.copy()
        for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTEST_ADDOPTS'):
            env.pop(key, None)
        artifact_dir = run_dir / (job.name + '_artifacts')
        artifact_dir.mkdir()
        row['artifacts'] = artifact_dir.name
        env['RDP_OUTPUT_ROOT'] = str(artifact_dir)
        env.update(PYTHONUTF8='1', PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        row.update(status='running', command=['python', *command[1:]])
        _save(summary_path, summary)
        print(f'[{index}/{len(jobs)} RUN] {job.name}', flush=True)
        step_start = time.monotonic()
        process = None
        reader = None
        decoder = io.IncrementalNewlineDecoder(
            codecs.getincrementaldecoder('utf-8')(errors='replace'), translate=True)
        try:
            with log_path.open('w', encoding='utf-8') as log:
                process = subprocess.Popen(command, cwd=root, env=env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
                if SHOW_JOB_OUTPUT:
                    reader = log_path.open('rb')
                heartbeat = step_start
                while process.poll() is None:
                    if reader is not None:
                        print(decoder.decode(reader.read(65536)), end='', flush=True)
                    now = time.monotonic()
                    if now - heartbeat >= HEARTBEAT_SECONDS:
                        print(f'[{index}/{len(jobs)} RUN] {job.name}: {now-step_start:.0f}s; '
                              f'log={path_from(log_path, root)}', flush=True)
                        heartbeat = now
                    time.sleep(0.05)
                row['exit_code'] = process.wait()
            row['status'] = 'passed' if row['exit_code'] == 0 else 'failed'
            if row['status'] == 'passed':
                row['evidence_result'] = _evidence(job, log_path, junit)
        except KeyboardInterrupt:
            if process is not None:
                _stop_process_tree(process)
            row['status'] = 'interrupted'
            interrupted = True
        except Exception as exc:
            if process is not None and process.poll() is None:
                _stop_process_tree(process)
            row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        finally:
            if reader is not None:
                try:
                    while chunk := reader.read(65536):
                        print(decoder.decode(chunk), end='', flush=True)
                    print(decoder.decode(b'', final=True), end='', flush=True)
                finally:
                    reader.close()
            row['elapsed_seconds'] = round(time.monotonic() - step_start, 3)
            _save(summary_path, summary)
        print(f'[{index}/{len(jobs)} {row["status"].upper()}] {job.name} '
              f'({row["elapsed_seconds"]:.2f}s)', flush=True)
        if interrupted or (stop_on_failure and row['status'] != 'passed'):
            stop_reason = 'interrupted' if interrupted else 'stop_on_failure'
            break
    for row in summary['jobs']:
        if row['status'] == 'pending':
            row['status'] = 'not_run'
    passed = all(row['status'] == 'passed' for row in summary['jobs'])
    summary.update(status='interrupted' if interrupted else ('passed' if passed else 'failed'),
                   stop_reason=stop_reason,
                   elapsed_seconds=round(time.monotonic() - started, 3))
    _save(summary_path, summary)
    print(f'Suite {summary["status"]}: {sum(r["status"] == "passed" for r in summary["jobs"])}'
          f'/{len(jobs)} passed', flush=True)
    return (130 if interrupted else (0 if passed else 1)), run_dir


def main() -> int:
    if len(sys.argv) != 1:
        raise ValueError('Configure constants in tools/run_validation.py; no CLI arguments')
    code, _ = run_jobs(build_jobs(RUN_SET), dry_run=DRY_RUN)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
