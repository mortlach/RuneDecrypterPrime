from __future__ import annotations
'Run V1 tutorials from one editable runner file.\n\nNormal tutorial control lives in the constants below. There are no command-line\nswitches, RDP environment variables, or separate config files for public V1\ntutorial runs.\n'
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
TUTORIAL_DIR = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from tutorials.v1.support.tutorial_benchmark import TutorialAcceptanceKind
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_runner import ConsoleOutput, TutorialEntry, TutorialResult, TutorialRunSet, evaluate_tutorial_acceptance, parse_match_ratio, repo_relpath, select_tutorials, tail_text, validate_tutorial_entries
RUN_SET = TutorialRunSet.RELEASE
CONSOLE_OUTPUT = ConsoleOutput.COMPACT
STOP_ON_FIRST_FAILURE = False
WRITE_OUTPUT_LOGS = True
CLEAN_OUTPUT_LOGS = True
OUTPUT_DIR = Path('output/tutorial_logs')
FAILURE_TAIL_LINES = 80
TUTORIALS: tuple[TutorialEntry, ...] = (TutorialEntry('Tutorial_TwoPeriodCribs.py', 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE, TutorialRunSet.FULL_ASSETS), required_asset_profile='full_v1'), TutorialEntry('Tutorial_TwoPeriodCribs_Interruptors.py', 1.0, run_sets=(TutorialRunSet.RELEASE, TutorialRunSet.FULL_ASSETS), required_asset_profile='full_v1'), TutorialEntry('Tutorial_TwoPeriodCribs_P13P31_Search.py', 1.0, run_sets=(TutorialRunSet.EXTENDED, TutorialRunSet.FULL_ASSETS), required_asset_profile='full_v1'), TutorialEntry('Tutorial_Start_Here.py', 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_Autokey.py', 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_Autokey_Robust.py', 1.0, run_sets=(TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_Railfence.py', 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_Vigenere_Interruptors_Exact.py', 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_ColumnarTransposition.py', 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_Vigenere_GeneralMap.py', 1.0, run_sets=(TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_Vigenere_Interruptors_Solve.py', 1.0, run_sets=(TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_MonoSubstitution_GA_RTL.py', 0.97, TutorialAcceptanceKind.HUMAN_READABLE, (TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_MonoSubstitution_GA_LTR.py', 0.97, TutorialAcceptanceKind.HUMAN_READABLE, (TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_MonoSubstitution_GA_Robust.py', 0.97, TutorialAcceptanceKind.HUMAN_READABLE, (TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_Repeating_multiply.py', 1.0, run_sets=(TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_MonoSubstitution_HYBRID_RTL.py', 0.995, TutorialAcceptanceKind.NEAR_EXACT, (TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_Vigenere_Interruptors_NonTrivial.py', 1.0, run_sets=(TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_Vigenere_Interruptors_Robust.py', 1.0, run_sets=(TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py', 1.0, run_sets=(TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py', 1.0, run_sets=(TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py', 0.9, TutorialAcceptanceKind.PARTIAL_RECOVERY, (TutorialRunSet.PARTIAL_RECOVERY,)), TutorialEntry('Tutorial_LP_Welcome_Pilgrim_Solve.py', 1.0, run_sets=(TutorialRunSet.RELEASE, TutorialRunSet.CI_LIGHT)), TutorialEntry('Tutorial_MonoSubstitution_SA_LTR.py', 0.995, TutorialAcceptanceKind.NEAR_EXACT, (TutorialRunSet.EXTENDED,)), TutorialEntry('Tutorial_PeriodicSubstitution.py', 0.995, TutorialAcceptanceKind.NEAR_EXACT, (TutorialRunSet.FULL_ASSETS,), required_asset_profile='full_v1'), TutorialEntry('Tutorial_PeriodicSubstitution_Simple_P7.py', 0.995, TutorialAcceptanceKind.NEAR_EXACT, (TutorialRunSet.FULL_ASSETS,), required_asset_profile='full_v1'), TutorialEntry('Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py', 1.0, run_sets=(TutorialRunSet.FULL_ASSETS,), required_asset_profile='full_v1'))
LONG_RUNNING_KAEDING_TUTORIALS = frozenset({
    'Tutorial_PeriodicSubstitution.py',
    'Tutorial_PeriodicSubstitution_Simple_P7.py',
    'Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py',
})

def _selected_tutorials() -> tuple[TutorialEntry, ...]:
    return select_tutorials(TUTORIALS, RUN_SET)

def _validate_tutorials(entries: tuple[TutorialEntry, ...]) -> None:
    validate_tutorial_entries(entries, tutorial_dir=TUTORIAL_DIR, run_set=RUN_SET)

def _output_dir() -> Path:
    if OUTPUT_DIR.is_absolute():
        raise ValueError('OUTPUT_DIR must be repo-relative, not absolute.')
    return ROOT / OUTPUT_DIR

def _prepare_output_dir() -> None:
    if not WRITE_OUTPUT_LOGS:
        return
    output_dir = _output_dir().resolve()
    output_root = (ROOT / 'output').resolve()
    if output_root not in output_dir.parents:
        raise ValueError('OUTPUT_DIR must stay under output/ for cleanup.')
    output_dir.mkdir(parents=True, exist_ok=True)
    if CLEAN_OUTPUT_LOGS:
        for path in output_dir.glob('*.txt'):
            if path.is_file():
                path.unlink()

def _parse_match_ratio(text: str) -> float | None:
    return parse_match_ratio(text)

def _tail(text: str, *, lines: int) -> str:
    return tail_text(text, lines=lines)

def _relpath(path: Path) -> str:
    return repo_relpath(path, repo_root=ROOT)

def _write_output_log(entry: TutorialEntry, output: str) -> Path | None:
    if not WRITE_OUTPUT_LOGS:
        return None
    output_dir = _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (Path(entry.path).stem + '.txt')
    output_path.write_text(output, encoding='utf-8')
    return output_path

def _run_one(entry: TutorialEntry) -> TutorialResult:
    script = TUTORIAL_DIR / entry.path
    proc = subprocess.run([sys.executable, '-X', 'utf8', str(script)], cwd=ROOT, text=True, encoding='utf-8', errors='replace', capture_output=True, check=False)
    output = (proc.stdout or '') + (proc.stderr or '')
    output_path = _write_output_log(entry, output)
    if CONSOLE_OUTPUT == ConsoleOutput.FULL or proc.returncode != 0:
        print(f'\n--- output: {entry.path} ---')
        print(output.rstrip())
    match_ratio = _parse_match_ratio(output)
    process_succeeded = proc.returncode == 0
    acceptance_met = evaluate_tutorial_acceptance(entry, process_succeeded=process_succeeded, match_ratio=match_ratio)
    passed = process_succeeded and acceptance_met
    if not passed and CONSOLE_OUTPUT != ConsoleOutput.FULL:
        print(f'\n--- tail: {entry.path} ---')
        print(_tail(output, lines=FAILURE_TAIL_LINES))
    return TutorialResult(path=entry.path, acceptance=entry.acceptance, returncode=proc.returncode, match_ratio=match_ratio, passed=passed, output_path=output_path, process_succeeded=process_succeeded, acceptance_met=acceptance_met)

def main() -> int:
    selected = _selected_tutorials()
    _validate_tutorials(selected)
    _prepare_output_dir()
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_result_note('Tutorial runner setup', [('runner', 'tutorials/v1/run_tutorials.py'), ('run set', RUN_SET.value), ('asset profile', 'full_v1' if RUN_SET in {TutorialRunSet.FULL_ASSETS, TutorialRunSet.ALL_WORKING} else 'ci_light' if RUN_SET == TutorialRunSet.CI_LIGHT else 'mixed by tutorial'), ('console output', CONSOLE_OUTPUT.value), ('selected', len(selected)), ('output logs', _relpath(_output_dir()) if WRITE_OUTPUT_LOGS else 'disabled')])
    long_running = [entry.path for entry in selected if entry.path in LONG_RUNNING_KAEDING_TUTORIALS]
    if long_running:
        pretty.print_result_note(
            'Long-running Kaeding qualification warning',
            [
                ('runtime', 'may take several hours per tutorial'),
                ('tutorials', ', '.join(long_running)),
            ],
        )
    results: list[TutorialResult] = []
    for entry in selected:
        print(f'[RUN ] {entry.path}')
        result = _run_one(entry)
        results.append(result)
        status = 'PASS' if result.passed else 'FAIL'
        match_text = 'none' if result.match_ratio is None else f'{result.match_ratio:.3f}'
        log_text = '' if result.output_path is None else f' log={_relpath(result.output_path)}'
        print(f"[{status}] {entry.path} process={('PASS' if result.process_succeeded else 'FAIL')} acceptance={entry.acceptance.value}:{('PASS' if result.acceptance_met else 'FAIL')} match_ratio={match_text} min={entry.min_match_ratio:.3f}{log_text}")
        if not result.passed and STOP_ON_FIRST_FAILURE:
            break
    passed = sum((1 for result in results if result.passed))
    failed = len(results) - passed
    print('\nTutorial summary')
    print(f'selected={len(selected)} run={len(results)} passed={passed} failed={failed}')
    return 0 if failed == 0 and len(results) == len(selected) else 1
if __name__ == '__main__':
    raise SystemExit(main())
