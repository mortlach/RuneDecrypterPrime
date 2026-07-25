from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from cipher_development.two_period_overlay.matched_pilot import (
    PILOT_BENCHMARK,
    PILOT_FIXED_CORE_SWEEPS,
    PILOT_RESTARTS,
    SHELL_DISTANCES,
    SHELL_SAMPLES_PER_DISTANCE,
    _pilot_starts,
    _shell_deltas,
    _shell_indices,
    _static_profile_rates,
    build_perturbation_shells,
    calibrated_sweeps,
    run_profile_arm,
)
from cipher_development.two_period_overlay.scorer_profiles import S1


def test_shell_variable_schedule_is_exactly_balanced() -> None:
    dimension = 16
    for distance in SHELL_DISTANCES:
        counts = [0] * dimension
        for sample_index in range(SHELL_SAMPLES_PER_DISTANCE):
            indices = _shell_indices(dimension, distance, sample_index)
            assert len(indices) == distance
            assert len(set(indices)) == distance
            for index in indices:
                counts[index] += 1
        assert counts == [2 * distance] * dimension


def test_shell_delta_schedule_is_nonzero_and_balanced() -> None:
    for distance in SHELL_DISTANCES:
        counts = {delta: 0 for delta in range(1, 29)}
        for sample_index in range(SHELL_SAMPLES_PER_DISTANCE):
            deltas = _shell_deltas(distance, sample_index)
            assert len(deltas) == distance
            assert all(1 <= delta <= 28 for delta in deltas)
            for delta in deltas:
                counts[delta] += 1
        assert max(counts.values()) - min(counts.values()) <= 1


def test_shell_builder_changes_exact_declared_affine_distance() -> None:
    base = np.arange(16, dtype=np.uint8)
    vectors, metadata = build_perturbation_shells(base)

    assert vectors.shape == (
        len(SHELL_DISTANCES) * SHELL_SAMPLES_PER_DISTANCE,
        16,
    )
    assert len(metadata) == len(vectors)
    assert len({row["sample_id"] for row in metadata}) == len(metadata)

    for vector, row in zip(vectors, metadata, strict=True):
        distance = int(row["distance"])
        assert int(np.count_nonzero(vector != base)) == distance
        assert len(row["changed_variable_indices"]) == distance
        assert len(row["modulo_29_deltas"]) == distance


def test_calibrated_sweeps_is_deterministic_and_bounded() -> None:
    assert calibrated_sweeps(100.0) == 6
    assert calibrated_sweeps(1.0) == 1
    assert calibrated_sweeps(10_000.0) == 8


def test_static_profile_rates_use_surface_medians() -> None:
    surfaces = {}
    for surface_index in range(3):
        profiles = {}
        for profile_index, profile in enumerate(
            __import__(
                "cipher_development.two_period_overlay.scorer_profiles",
                fromlist=["SCORER_PANEL"],
            ).SCORER_PANEL
        ):
            profiles[profile.profile_id] = {
                "candidate_evaluations_per_s": 10.0 * (profile_index + 1) + surface_index
            }
        surfaces[f"surface_{surface_index}"] = {"profiles": profiles}

    rates = _static_profile_rates({"surfaces": surfaces})

    assert rates[S1.profile_id] == 21.0


def test_pilot_starts_are_deterministic_and_shared() -> None:
    first = _pilot_starts()
    second = _pilot_starts()

    assert first == second
    assert len(first) == PILOT_RESTARTS
    assert [row["restart_index"] for row in first] == list(range(PILOT_RESTARTS))
    assert all(len(row["variables"]) == PILOT_BENCHMARK.expected_free_dimension for row in first)


def test_profile_arm_retains_search_evidence_without_terminal_fields() -> None:
    dimension = PILOT_BENCHMARK.expected_free_dimension
    particular = np.zeros(PILOT_BENCHMARK.key_length, dtype=np.uint8)
    basis = np.zeros((PILOT_BENCHMARK.key_length, dimension), dtype=np.uint8)
    for index in range(dimension):
        basis[index, index] = 1

    def evaluate(values: np.ndarray) -> np.ndarray:
        batch = np.asarray(values, dtype=np.uint8)
        batch = batch[None, :] if batch.ndim == 1 else batch
        return -np.sum(batch.astype(np.float64), axis=1)

    search_case = SimpleNamespace(
        particular=particular,
        basis=basis,
        evaluate_variables=evaluate,
    )
    starts = _pilot_starts()[:2]
    outcome = run_profile_arm(
        search_case,
        S1,
        starts,
        arm_id="fixed_core",
        sweeps=PILOT_FIXED_CORE_SWEEPS,
    )

    assert outcome.generated_candidates == 2
    assert outcome.evaluations > 0
    assert outcome.elapsed_s > 0.0
    summary = outcome.search_summary()
    assert summary["attempt_count"] == 2
    assert summary["attempt_elapsed_s_summary"]["minimum"] > 0.0
    assert summary["attempt_candidate_evaluations_per_s_summary"]["minimum"] > 0.0
    assert outcome.archive.records
    for row in outcome.restart_rows:
        assert row["elapsed_s"] > 0.0
        assert row["candidate_evaluations_per_s"] > 0.0

    for record in outcome.archive.records:
        assert S1.score_name in record.scores
        assert record.payload["benchmark_id"] == PILOT_BENCHMARK.benchmark_id
        assert record.provenance.details["arm_id"] == "fixed_core"
        serialised = record.to_json_dict()
        assert "truth" not in str(serialised).lower()
        assert "reference" not in str(serialised).lower()
        assert "oracle" not in str(serialised).lower()


def test_pack02a_review_pack_contracts_are_registered() -> None:
    import cipher_development.two_period_overlay.review_pack as review_pack

    shell_required = review_pack._required_artifacts(
        "multiscale_perturbation_shells_v1"
    )
    assert "artifacts/perturbation_shell_design.json" in shell_required
    assert "artifacts/execution_timing.json" in shell_required
    required = review_pack._required_artifacts("matched_d8_profile_pilot_v1")
    assert "artifacts/matched_d8_pilot_summary.json" in required
    assert "artifacts/matched_d8_pilot/starts.json" in required
    assert "artifacts/matched_d8_pilot/source_static_panel_summary.json" in required
    assert "artifacts/execution_timing.json" in required
    assert "artifacts/matched_d8_pilot/attempt_timing.json" in required


def test_review_markdown_makes_timing_explicit() -> None:
    import cipher_development.two_period_overlay.review_pack as review_pack

    manifest = {
        "campaign_id": "two_period_overlay",
        "experiment_id": "matched_d8_profile_pilot_v1",
        "benchmark_id": PILOT_BENCHMARK.benchmark_id,
        "run_id": "test_run",
        "run_status": "completed",
        "decision": "refine",
        "stop_reason": "done",
        "configuration_hash": "abc",
        "experiment": {
            "question": "question",
            "hypothesis": "hypothesis",
            "alternative": "alternative",
            "decision_rule": "rule",
            "wli_mode": "with_wli",
            "truth_policy": "benchmark_only",
            "budget_seconds": None,
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
                "started_at_utc": "2026-07-25T00:00:00+00:00",
                "finished_at_utc": "2026-07-25T00:01:00+00:00",
                "elapsed_s": 60.0,
                "scope": "test",
                "phases": {"search_and_replay_elapsed_s": 55.0},
                "profiles": {
                    "S1": {
                        "fixed_core": {
                            "elapsed_s": 5.0,
                            "attempt_count": 2,
                            "attempt_elapsed_s_summary": {
                                "median": 2.5,
                                "maximum": 3.0,
                            },
                            "candidate_evaluations_per_s": 100.0,
                        }
                    }
                },
                "attempt_timing_artifact": (
                    "artifacts/matched_d8_pilot/attempt_timing.json"
                ),
            }
        }
    }

    rendered = review_pack._review_markdown(manifest, result)

    assert "## Timing" in rendered
    assert "scientific-work elapsed seconds: `60.0`" in rendered
    assert "`S1/fixed_core`" in rendered
    assert "individual attempt log" in rendered
