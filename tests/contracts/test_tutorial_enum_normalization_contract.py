from __future__ import annotations
from rune_decrypter_prime.utils.tutorial_benchmark import TutorialBenchmarkOutcome, TutorialBenchmarkSummary, TutorialRunKind, TutorialStopPolicy, TutorialStopReason, TutorialTruthPolicy, build_tutorial_benchmark_summary
from rune_decrypter_prime.utils.tutorial_reference import TutorialReference

def test_tutorial_boundary_strings_normalize_to_enum_instances() -> None:
    summary = build_tutorial_benchmark_summary(run_kind='real_key_recovery_benchmark', truth_policy='known_plaintext_reference', stop_policy=TutorialStopPolicy(), plaintext_idx=[1, 2, 3], reference_idx=[1, 2, 3])
    reference = TutorialReference(truth_policy='known_key_and_plaintext')
    assert summary.run_kind is TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK
    assert summary.truth_policy is TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE
    assert reference.truth_policy is TutorialTruthPolicy.KNOWN_KEY_AND_PLAINTEXT

def test_direct_tutorial_summary_strings_normalize_to_enum_instances() -> None:
    summary = TutorialBenchmarkSummary(schema='rdp_tutorial_benchmark_summary.v1', run_kind='real_key_recovery_benchmark', truth_policy='known_plaintext_reference', stop_policy=TutorialStopPolicy(), outcome='pass', stop_reason='target_match_ratio', readable_reached=True, target_reached=True, match_ratio=1.0, score=None, evals=None, tokens=None, wall_time_s=None)
    assert summary.outcome is TutorialBenchmarkOutcome.PASS
    assert summary.stop_reason is TutorialStopReason.TARGET_MATCH_RATIO
    assert summary.to_json_dict()['stop_reason'] == 'target_match_ratio'
