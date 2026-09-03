from __future__ import annotations
from types import SimpleNamespace
from tutorials.v1.support.tutorial_benchmark import TutorialRunKind, TutorialStopPolicy
from tutorials.v1.support.tutorial_reference import TutorialReference
from tutorials.v1.support.tutorial_session_report import build_tutorial_session_report

def _solution() -> SimpleNamespace:
    return SimpleNamespace(key=[3, 1, 4], plaintext_idx=[1, 2, 3, 4], plaintext_rune='ᚠᚢᚦᚩ', score=0.7, evals=12, tokens_processed=99, meta={})

def test_tutorial_session_report_works_without_reference() -> None:
    report = build_tutorial_session_report(title='demo', cipher='vigenere', solution=_solution())
    assert report['title'] == 'demo'
    assert report['cipher'] == 'vigenere'
    assert report['benchmark'] == {}

def test_tutorial_session_report_attaches_reference_benchmark() -> None:
    reference = TutorialReference.key_and_plaintext(key_idx=[3, 1, 4], plaintext_idx=[1, 2, 3, 4])
    report = build_tutorial_session_report(title='demo', cipher='scheduled_stream_lookup', solution=_solution(), reference=reference, run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK, stop_policy=TutorialStopPolicy(readable_match_ratio=0.8, target_match_ratio=0.99))
    assert report['match_ratio'] == 1.0
    assert report['key']['exact'] is True
    assert report['benchmark']['truth_policy'] == 'known_key_and_plaintext'
    assert report['benchmark']['outcome'] == 'pass'
