from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.utils.tutorial_report import SCHEMA, build_tutorial_run_report


def test_tutorial_report_top_level_shape_is_stable() -> None:
    solution = SimpleNamespace(
        key=[3, 1, 4],
        plaintext_idx=[1, 2, 3],
        plaintext_rune="abc",
        stop_reason="target_score",
        score=0.7,
        evals=12,
        tokens_processed=99,
        meta={},
    )

    report = build_tutorial_run_report(
        title="contract",
        cipher="scheduled_stream_lookup",
        solution=solution,
        key_idx=[3, 1, 4],
        pt_idx_ref=[1, 2, 3],
    )

    assert report["schema"] == SCHEMA
    assert set(report) == {
        "schema",
        "title",
        "app_version",
        "cipher",
        "recovered",
        "match_ratio",
        "solver",
        "key",
        "benchmark",
        "timings_s",
        "telemetry",
        "solver_report",
        "previews",
    }
    assert {"present", "truth_data_policy", "scorer_lanes"} <= set(report["solver_report"])
    assert {"plaintext_runes", "reference_runes", "plaintext_idx_head"} <= set(report["previews"])
