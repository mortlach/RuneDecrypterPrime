from __future__ import annotations
from pathlib import Path
from tutorials.v1.support.tutorial_benchmark import TutorialAcceptanceKind
from tutorials.v1.support.tutorial_runner import TutorialEntry, TutorialResult, evaluate_tutorial_acceptance, repo_relpath

def test_process_success_acceptance_does_not_require_match_ratio() -> None:
    entry = TutorialEntry('Tutorial_A.py', 1.0, TutorialAcceptanceKind.PROCESS_SUCCESS)
    assert evaluate_tutorial_acceptance(entry, process_succeeded=True, match_ratio=None) is True
    result = TutorialResult(path=entry.path, acceptance=entry.acceptance, returncode=0, match_ratio=None, passed=True, output_path=None, process_succeeded=True, acceptance_met=True)
    assert result.process_succeeded is True
    assert result.acceptance_met is True
    assert result.passed is True

def test_exact_acceptance_is_separate_from_process_success() -> None:
    entry = TutorialEntry('Tutorial_A.py', 1.0, TutorialAcceptanceKind.EXACT)
    acceptance_met = evaluate_tutorial_acceptance(entry, process_succeeded=True, match_ratio=0.99)
    result = TutorialResult(path=entry.path, acceptance=entry.acceptance, returncode=0, match_ratio=0.99, passed=False, output_path=None, process_succeeded=True, acceptance_met=acceptance_met)
    assert result.process_succeeded is True
    assert result.acceptance_met is False
    assert result.passed is False

def test_established_six_argument_tutorial_result_still_constructs() -> None:
    result = TutorialResult('Tutorial_A.py', TutorialAcceptanceKind.EXACT, 0, 1.0, True, None)
    assert result.process_succeeded is True
    assert result.acceptance_met is True
    assert result.passed is True

def test_repo_relpath_does_not_leak_external_absolute_path(tmp_path: Path) -> None:
    root = tmp_path / 'repo'
    root.mkdir()
    external = tmp_path / 'private' / 'result.txt'
    external.parent.mkdir()
    external.write_text('x', encoding='utf-8')
    value = repo_relpath(external, repo_root=root)
    assert value == '<external>/result.txt'
    assert str(tmp_path) not in value
