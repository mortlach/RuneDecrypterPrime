from __future__ import annotations

import pytest

from rune_decrypter_prime.utils.tutorial_benchmark import (
    TutorialBenchmarkOutcome,
    TutorialBenchmarkSummary,
    TutorialRunKind,
    TutorialStopPolicy,
    TutorialStopReason,
    TutorialTruthPolicy,
    build_tutorial_benchmark_summary,
)


def test_tutorial_benchmark_target_match_pass() -> None:
    summary = build_tutorial_benchmark_summary(
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
        stop_policy=TutorialStopPolicy(readable_match_ratio=0.80, target_match_ratio=0.95),
        plaintext_idx=[1, 2, 3, 4],
        reference_idx=[1, 2, 3, 4],
        score=0.57,
        evals=100,
        tokens=1000,
        wall_time_s=2.5,
    )

    assert summary.outcome is TutorialBenchmarkOutcome.PASS
    assert summary.stop_reason is TutorialStopReason.TARGET_MATCH_RATIO
    assert summary.match_ratio == 1.0
    assert summary.to_json_dict()["schema"] == "rdp_tutorial_benchmark_summary.v1"


def test_tutorial_benchmark_readable_match_pass() -> None:
    summary = build_tutorial_benchmark_summary(
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
        stop_policy=TutorialStopPolicy(readable_match_ratio=0.50, target_match_ratio=1.0),
        plaintext_idx=[1, 2, 9, 9],
        reference_idx=[1, 2, 3, 4],
    )

    assert summary.outcome is TutorialBenchmarkOutcome.PASS
    assert summary.stop_reason is TutorialStopReason.READABLE_MATCH_RATIO
    assert summary.readable_reached is True
    assert summary.target_reached is False


def test_tutorial_benchmark_requires_truth_label_for_reference_match() -> None:
    with pytest.raises(ValueError, match="tutorial truth policy"):
        build_tutorial_benchmark_summary(
            run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
            truth_policy=TutorialTruthPolicy.NONE,
            stop_policy=TutorialStopPolicy(),
            plaintext_idx=[1, 2, 3],
            reference_idx=[1, 2, 3],
        )


def test_tutorial_truth_policy_can_be_declared_before_reference_attached() -> None:
    summary = build_tutorial_benchmark_summary(
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
        stop_policy=TutorialStopPolicy(),
        plaintext_idx=[1, 2, 3],
        reference_idx=None,
    )

    assert summary.truth_policy is TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE
    assert summary.match_ratio is None
    assert summary.readable_reached is None
    assert summary.target_reached is None
    assert summary.outcome is TutorialBenchmarkOutcome.INCOMPLETE


def test_direct_tutorial_summary_allows_oracle_attachment_before_match_fields() -> None:
    summary = TutorialBenchmarkSummary(
        schema="rdp_tutorial_benchmark_summary.v1",
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
        stop_policy=TutorialStopPolicy(),
        outcome=TutorialBenchmarkOutcome.INCOMPLETE,
        stop_reason=TutorialStopReason.NOT_REACHED,
        readable_reached=None,
        target_reached=None,
        match_ratio=None,
        score=None,
        evals=None,
        tokens=None,
        wall_time_s=None,
    )

    assert summary.match_ratio is None


def test_direct_tutorial_summary_match_ratio_requires_reached_flags() -> None:
    with pytest.raises(ValueError, match="readable_reached"):
        TutorialBenchmarkSummary(
            schema="rdp_tutorial_benchmark_summary.v1",
            run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
            truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
            stop_policy=TutorialStopPolicy(),
            outcome=TutorialBenchmarkOutcome.INCOMPLETE,
            stop_reason=TutorialStopReason.NOT_REACHED,
            readable_reached=None,
            target_reached=True,
            match_ratio=1.0,
            score=None,
            evals=None,
            tokens=None,
            wall_time_s=None,
        )


def test_tutorial_benchmark_budget_fail_if_not_readable() -> None:
    summary = build_tutorial_benchmark_summary(
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
        stop_policy=TutorialStopPolicy(readable_match_ratio=0.90, target_match_ratio=0.99, max_evals=10),
        plaintext_idx=[9, 9, 9],
        reference_idx=[1, 2, 3],
        evals=10,
    )

    assert summary.outcome is TutorialBenchmarkOutcome.FAIL
    assert summary.stop_reason is TutorialStopReason.WORK_BUDGET


def test_tutorial_stop_policy_rejects_bad_thresholds() -> None:
    with pytest.raises(ValueError, match="target_match_ratio"):
        TutorialStopPolicy(readable_match_ratio=0.90, target_match_ratio=0.80)
    with pytest.raises(ValueError, match="max_evals"):
        TutorialStopPolicy(max_evals=0)
