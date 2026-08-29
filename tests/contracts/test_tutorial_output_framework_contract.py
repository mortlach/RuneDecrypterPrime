from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from rune_decrypter_prime.utils import tutorial_benchmark, tutorial_report
from rune_decrypter_prime.utils.tutorial_benchmark import TutorialRunKind, TutorialStopPolicy
from rune_decrypter_prime.utils.tutorial_reference import TutorialReference
from rune_decrypter_prime.utils.tutorial_session_report import build_tutorial_session_report
REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = {'src/rune_decrypter_prime/utils/tutorial_report.py', 'src/rune_decrypter_prime/utils/tutorial_benchmark.py', 'src/rune_decrypter_prime/utils/tutorial_reference.py', 'src/rune_decrypter_prime/utils/tutorial_session_report.py', 'docs/release_contracts/v1/D7_TUTORIAL_OUTPUT_FRAMEWORK.md'}

def test_tutorial_output_framework_files_exist() -> None:
    missing = sorted((path for path in REQUIRED_FILES if not (REPO_ROOT / path).is_file()))
    assert not missing, f'missing tutorial output framework files: {missing}'

def test_tutorial_output_framework_schema_names_are_stable() -> None:
    assert tutorial_report.SCHEMA == 'rdp_tutorial_run_report.v1'
    summary = tutorial_benchmark.build_tutorial_benchmark_summary(run_kind=tutorial_benchmark.TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK, truth_policy=tutorial_benchmark.TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE, stop_policy=tutorial_benchmark.TutorialStopPolicy(), plaintext_idx=[1, 2, 3], reference_idx=[1, 2, 3])
    assert summary.to_json_dict()['schema'] == 'rdp_tutorial_benchmark_summary.v1'

def test_tutorial_session_report_accepts_attached_reference() -> None:
    solution = SimpleNamespace(key=[3, 1, 4], plaintext_idx=[1, 2, 3], meta={})
    reference = TutorialReference.key_and_plaintext(key_idx=[3, 1, 4], plaintext_idx=[1, 2, 3])
    report = build_tutorial_session_report(title='contract', cipher='scheduled_stream_lookup', solution=solution, reference=reference, run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK, stop_policy=TutorialStopPolicy())
    assert report['schema'] == 'rdp_tutorial_run_report.v1'
    assert report['match_ratio'] == 1.0
    assert report['key']['exact'] is True
    assert report['benchmark']['truth_policy'] == 'known_key_and_plaintext'
