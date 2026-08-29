from __future__ import annotations
import pytest
from rune_decrypter_prime.utils.tutorial_benchmark import TutorialBenchmarkOutcome, TutorialBenchmarkSummary, TutorialRunKind, TutorialStopPolicy, TutorialStopReason, TutorialTruthPolicy, build_tutorial_benchmark_summary

def test_builder_normalizes_string_enum_domains() -> None:
    summary = build_tutorial_benchmark_summary(run_kind='real_key_recovery_benchmark', truth_policy='known_plaintext_reference', stop_policy=TutorialStopPolicy(), plaintext_idx=[1, 2, 3], reference_idx=[1, 2, 3])
    assert summary.run_kind is TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK
    assert summary.truth_policy is TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE
    assert summary.to_json_dict()['run_kind'] == 'real_key_recovery_benchmark'

def test_direct_summary_normalizes_string_enum_domains() -> None:
    summary = TutorialBenchmarkSummary(schema='rdp_tutorial_benchmark_summary.v1', run_kind='real_key_recovery_benchmark', truth_policy='known_plaintext_reference', stop_policy=TutorialStopPolicy(), outcome='pass', stop_reason='target_match_ratio', readable_reached=True, target_reached=True, match_ratio=1.0, score=None, evals=None, tokens=None, wall_time_s=None)
    assert summary.outcome is TutorialBenchmarkOutcome.PASS
    assert summary.stop_reason is TutorialStopReason.TARGET_MATCH_RATIO

def test_unknown_string_enum_domain_is_rejected() -> None:
    with pytest.raises(ValueError, match='unknown run_kind'):
        build_tutorial_benchmark_summary(run_kind='banana', truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE, stop_policy=TutorialStopPolicy())
