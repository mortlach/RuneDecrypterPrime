from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from cipher_development.two_period_overlay import review_pack
from cipher_development.two_period_overlay.config import EXACT_EXTRA_CRIB_BENCHMARKS
from cipher_development.two_period_overlay.experiment_a import (
    ARCHIVE_CAPACITY,
    OVERNIGHT_RATE_THRESHOLD,
    POSITIONAL_BLOCK_IDS,
    POSITIONAL_BENCHMARK,
    PRIMARY_BLOCK_IDS,
    PRIMARY_BENCHMARK,
    STARTS_PER_BLOCK,
    _aggregate_panel,
    build_block_starts,
    panel_seed,
    planned_runtime,
)
from cipher_development.two_period_overlay.scorer_profiles import S2
from cipher_development.two_period_overlay.staged_handoff import _run_stage


def _fake_case(benchmark):
    particular = np.zeros(benchmark.key_length, dtype=np.uint8)
    basis = np.zeros(
        (benchmark.key_length, benchmark.expected_free_dimension),
        dtype=np.uint8,
    )
    for column in range(benchmark.expected_free_dimension):
        basis[column, column] = 1
    target = np.arange(benchmark.expected_free_dimension, dtype=np.uint8)

    def evaluate(values: np.ndarray) -> np.ndarray:
        rows = np.asarray(values, dtype=np.uint8)
        return -np.count_nonzero(rows != target[None, :], axis=1).astype(float)

    return SimpleNamespace(
        particular=particular,
        basis=basis,
        evaluate_variables=evaluate,
    )


def _baseline_terminal(exact: bool):
    return {"archive": {"exact_plaintext_count": int(exact)}}


def _staged_terminal(exact: bool):
    return {
        "final_union": {
            "archive": {"exact_plaintext_count": int(exact)}
        }
    }


def test_panel_blocks_and_benchmarks_are_frozen() -> None:
    assert PRIMARY_BENCHMARK is EXACT_EXTRA_CRIB_BENCHMARKS[0]
    assert POSITIONAL_BENCHMARK is EXACT_EXTRA_CRIB_BENCHMARKS[1]
    assert PRIMARY_BLOCK_IDS == tuple(range(31, 39))
    assert POSITIONAL_BLOCK_IDS == tuple(range(41, 45))
    assert not set(PRIMARY_BLOCK_IDS) & set(POSITIONAL_BLOCK_IDS)
    assert STARTS_PER_BLOCK == 128
    assert ARCHIVE_CAPACITY == 512


def test_block_starts_are_deterministic_and_separated() -> None:
    first = build_block_starts(PRIMARY_BENCHMARK, PRIMARY_BLOCK_IDS[0], count=4)
    second = build_block_starts(PRIMARY_BENCHMARK, PRIMARY_BLOCK_IDS[0], count=4)
    other_block = build_block_starts(PRIMARY_BENCHMARK, PRIMARY_BLOCK_IDS[1], count=4)
    positional = build_block_starts(POSITIONAL_BENCHMARK, POSITIONAL_BLOCK_IDS[0], count=4)
    assert first == second
    assert first != other_block
    assert first != positional
    assert len({row["seed"] for row in first}) == 4
    assert all(len(row["variables"]) == 8 for row in first)


def test_panel_seed_is_stable_and_namespaced() -> None:
    seed = panel_seed(PRIMARY_BENCHMARK.benchmark_id, 31, "scout", "x")
    assert seed == panel_seed(PRIMARY_BENCHMARK.benchmark_id, 31, "scout", "x")
    assert seed != panel_seed(PRIMARY_BENCHMARK.benchmark_id, 32, "scout", "x")
    assert seed != panel_seed(POSITIONAL_BENCHMARK.benchmark_id, 31, "scout", "x")
    assert seed != panel_seed(PRIMARY_BENCHMARK.benchmark_id, 31, "bridge", "x")


def test_generalised_stage_records_the_requested_benchmark() -> None:
    case = _fake_case(POSITIONAL_BENCHMARK)
    starts = (
        {"restart_index": 0, "seed": 1, "variables": [28] * 8},
        {"restart_index": 1, "seed": 2, "variables": [27] * 8},
    )

    def fixed_seed(stage_id: str, token: str) -> int:
        return panel_seed(POSITIONAL_BENCHMARK.benchmark_id, 41, stage_id, token)

    outcome = _run_stage(
        stage_id="scout",
        profile=S2,
        search_case=case,
        inputs=starts,
        sweeps=1,
        benchmark=POSITIONAL_BENCHMARK,
        seed_factory=fixed_seed,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=30.0,
        provenance_source="experiment_a_standard_panel",
    )
    assert outcome.input_count == 2
    assert all(
        record.payload["benchmark_id"] == POSITIONAL_BENCHMARK.benchmark_id
        for record in outcome.archive.records
    )
    assert all(
        record.provenance.source == "experiment_a_standard_panel"
        for record in outcome.archive.records
    )


def test_runtime_plan_is_explicitly_one_to_two_hours() -> None:
    payload = planned_runtime()
    assert 60.0 * 60.0 < payload["central_elapsed_s"] < 2.0 * 60.0 * 60.0
    assert payload["safety_adjusted_elapsed_s"] < 3.0 * 60.0 * 60.0
    assert payload["primary_starts_per_arm"] == 8 * 128
    assert payload["positional_staged_starts"] == 4 * 128


def test_aggregate_promotes_only_after_primary_and_positional_exact_solves() -> None:
    baseline = [_baseline_terminal(False) for _ in range(8)]
    primary = [_staged_terminal(index == 0) for index in range(8)]
    positional = [_staged_terminal(index == 0) for index in range(4)]
    payload = _aggregate_panel(
        primary_baseline=baseline,
        primary_staged=primary,
        positional_staged=positional,
    )
    assert payload["promotion_gate_passed"] is True
    assert payload["source_exact_solve_replicated"] is True
    assert payload["offset_81_position_confirmed"] is True


def test_overnight_recommendation_depends_on_replication_rate() -> None:
    assert OVERNIGHT_RATE_THRESHOLD == 0.50
    baseline = [_baseline_terminal(False) for _ in range(8)]
    weak_primary = [_staged_terminal(index == 0) for index in range(8)]
    weak_positional = [_staged_terminal(index == 0) for index in range(4)]
    weak = _aggregate_panel(
        primary_baseline=baseline,
        primary_staged=weak_primary,
        positional_staged=weak_positional,
    )
    assert weak["overnight_strategy"]["experiment_a_overnight_recommended"] is True

    strong_primary = [_staged_terminal(index < 6) for index in range(8)]
    strong_positional = [_staged_terminal(index < 3) for index in range(4)]
    strong = _aggregate_panel(
        primary_baseline=baseline,
        primary_staged=strong_primary,
        positional_staged=strong_positional,
    )
    assert strong["overnight_strategy"]["experiment_a_overnight_recommended"] is False
    assert "Experiment B" in strong["overnight_strategy"]["recommended_target"]


def test_review_pack_contract_covers_experiment_a() -> None:
    required = review_pack._required_artifacts("experiment_a_standard_panel_v1")
    assert "artifacts/experiment_a_standard_panel_summary.json" in required
    assert "artifacts/experiment_a/attempt_timing.json" in required
    assert (
        "artifacts/experiment_a/"
        "alice_308_p13_p17_crib188x13_plus081x8_d08/"
        "block_41/staged/final_union/replay_evidence.json"
    ) in required
    review_pack._guard_run_json(
        review_pack.Path(
            "artifacts/experiment_a/source_pack02b_experiment_result.json"
        ),
        b'{"reference_evaluation":{"exact_plaintext":true}}',
    )


def test_review_markdown_uses_scientific_work_elapsed_seconds() -> None:
    manifest = {
        "campaign_id": "two_period_overlay",
        "experiment_id": "experiment_a_standard_panel_v1",
        "benchmark_id": PRIMARY_BENCHMARK.benchmark_id,
        "run_id": "run",
        "run_status": "completed",
        "decision": "promote",
        "stop_reason": "done",
        "configuration_hash": "abc",
        "experiment": {
            "question": "q",
            "hypothesis": "h",
            "alternative": "a",
            "decision_rule": "d",
            "wli_mode": "with_wli",
            "truth_policy": "benchmark_only",
            "budget_seconds": 1,
            "budget_evaluations": 1,
            "lesson_ids": [],
        },
        "evidence_quality": {
            "required_artifacts_complete": True,
            "source_snapshot_complete": True,
            "tests_passed": True,
            "validation_source_matches": True,
            "working_tree_clean": False,
        },
        "pack_complete": True,
        "review_ready": True,
        "missing_artifacts": [],
        "missing_sources": [],
        "missing_source_run_artifacts": [],
    }
    result = {
        "result_summary": {
            "timing": {
                "scientific_work_elapsed_s": 123.5,
                "elapsed_s": 999.0,
                "scope": "test",
            }
        }
    }
    rendered = review_pack._review_markdown(manifest, result)
    assert "scientific-work elapsed seconds: `123.5`" in rendered
