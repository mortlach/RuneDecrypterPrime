from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.utils.tutorial_benchmark import (
    TutorialRunKind,
    TutorialStopPolicy,
    TutorialTruthPolicy,
    build_tutorial_benchmark_summary,
)
from rune_decrypter_prime.utils.tutorial_report import build_tutorial_run_report, render_tutorial_run_report


def test_tutorial_report_includes_benchmark_summary_section() -> None:
    solution = SimpleNamespace(
        key=[3, 1, 4],
        plaintext_idx=[1, 2, 3, 4],
        plaintext_rune="ᚠᚢᚦᚩ",
        score=0.75,
        meta={},
    )
    benchmark = build_tutorial_benchmark_summary(
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
        stop_policy=TutorialStopPolicy(readable_match_ratio=0.8, target_match_ratio=0.99),
        plaintext_idx=[1, 2, 3, 4],
        reference_idx=[1, 2, 3, 4],
        score=0.75,
        evals=42,
    )

    report = build_tutorial_run_report(
        title="demo",
        cipher="scheduled_stream_lookup",
        solution=solution,
        benchmark_summary=benchmark,
        key_idx=[3, 1, 4],
        pt_idx_ref=[1, 2, 3, 4],
    )

    assert report["benchmark"]["schema"] == "rdp_tutorial_benchmark_summary.v1"
    assert report["benchmark"]["outcome"] == "pass"
    assert report["benchmark"]["truth_policy"] == "known_plaintext_reference"
    assert report["match_ratio"] == 1.0
    assert any(line.startswith("benchmark") for line in render_tutorial_run_report(report))
