from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialRunKind, TutorialStopPolicy
from rune_decrypter_prime.utils.tutorial_reference import TutorialReference


def test_tutorial_reference_can_be_created_before_vectors_are_attached() -> None:
    ref = TutorialReference.plaintext(label="demo")

    assert ref.match_ratio([1, 2, 3]) is None
    assert ref.to_json_dict()["has_plaintext"] is False

    attached = ref.with_plaintext([1, 2, 3])
    assert attached.match_ratio([1, 2, 9]) == 2 / 3


def test_tutorial_reference_builds_benchmark_summary_from_solution() -> None:
    ref = TutorialReference.plaintext([1, 2, 3, 4])
    solution = SimpleNamespace(
        plaintext_idx=[1, 2, 3, 4],
        score=0.7,
        evals=12,
        tokens_processed=99,
        stop_reason="target_score",
    )

    summary = ref.build_summary(
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        stop_policy=TutorialStopPolicy(readable_match_ratio=0.8, target_match_ratio=0.99),
        solution=solution,
    )

    assert summary.match_ratio == 1.0
    assert summary.evals == 12
