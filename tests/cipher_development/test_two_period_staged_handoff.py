from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from cipher_development.shared.archive import CandidateProvenance, CandidateRecord, candidate_id_for
from cipher_development.two_period_overlay.scorer_profiles import B1, F1, S2
from cipher_development.two_period_overlay.staged_handoff import (
    BRIDGE_PROFILE,
    FROZEN_LADDER,
    JUDGE_PROFILE,
    PROJECTION_SAFETY_FACTOR,
    SCOUT_PROFILE,
    STAGED_BENCHMARK,
    STAGED_RESTARTS,
    STAGE_SWEEPS,
    _deduplicated_records,
    _first_stage_map,
    _rescore_final_union,
    _run_stage,
    _runtime_projection,
    build_scout_starts,
    stage_seed,
)


def _fake_case():
    particular = np.zeros(STAGED_BENCHMARK.key_length, dtype=np.uint8)
    basis = np.zeros(
        (STAGED_BENCHMARK.key_length, STAGED_BENCHMARK.expected_free_dimension),
        dtype=np.uint8,
    )
    for column in range(STAGED_BENCHMARK.expected_free_dimension):
        basis[column, column] = 1

    target = np.arange(STAGED_BENCHMARK.expected_free_dimension, dtype=np.uint8)

    def evaluate(values: np.ndarray) -> np.ndarray:
        rows = np.asarray(values, dtype=np.uint8)
        return -np.count_nonzero(rows != target[None, :], axis=1).astype(float)

    return SimpleNamespace(
        particular=particular,
        basis=basis,
        evaluate_variables=evaluate,
    )


def _record(value: int, score_name: str, score: float) -> CandidateRecord:
    variables = [value] * STAGED_BENCHMARK.expected_free_dimension
    expanded = [0] * STAGED_BENCHMARK.key_length
    expanded[0] = value
    identity = {"expanded_key": expanded}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={
            "variables": variables,
            "expanded_key": expanded,
            "benchmark_id": STAGED_BENCHMARK.benchmark_id,
        },
        scores={score_name: score},
        provenance=CandidateProvenance(source="test"),
    )


def test_ladder_is_frozen_to_s2_b1_f1() -> None:
    assert FROZEN_LADDER == (S2, B1, F1)
    assert SCOUT_PROFILE is S2
    assert BRIDGE_PROFILE is B1
    assert JUDGE_PROFILE is F1
    assert STAGE_SWEEPS == {
        S2.profile_id: 5,
        B1.profile_id: 4,
        F1.profile_id: 3,
    }


def test_scout_starts_are_deterministic_and_complete() -> None:
    first = build_scout_starts()
    second = build_scout_starts()
    assert first == second
    assert len(first) == STAGED_RESTARTS == 96
    assert len({row["seed"] for row in first}) == STAGED_RESTARTS
    assert all(len(row["variables"]) == 8 for row in first)


def test_stage_seed_is_stable_and_stage_specific() -> None:
    assert stage_seed("scout", "x") == stage_seed("scout", "x")
    assert stage_seed("scout", "x") != stage_seed("bridge", "x")
    assert stage_seed("scout", "x") != stage_seed("scout", "y")


def test_stage_handoff_records_parent_and_preserves_identity() -> None:
    case = _fake_case()
    starts = (
        {"restart_index": 0, "seed": 1, "variables": [28] * 8},
        {"restart_index": 1, "seed": 2, "variables": [27] * 8},
    )
    scout = _run_stage(
        stage_id="scout",
        profile=S2,
        search_case=case,
        inputs=starts,
        sweeps=1,
    )
    bridge = _run_stage(
        stage_id="bridge",
        profile=B1,
        search_case=case,
        inputs=scout.archive.records,
        sweeps=1,
    )
    assert scout.input_count == 2
    assert bridge.input_count == len(scout.archive.records)
    assert all(B1.score_name in record.scores for record in bridge.archive.records)
    assert all(S2.score_name in record.scores for record in bridge.archive.records)
    assert all(
        row["source_candidate_id"] in {record.candidate_id for record in scout.archive.records}
        for row in bridge.attempt_rows
    )
    assert all(row["stage_id"] == "bridge" for row in bridge.attempt_rows)


def test_final_union_deduplicates_and_preserves_first_stage() -> None:
    a = _record(1, S2.score_name, 1.0)
    b = _record(2, S2.score_name, 2.0)
    c = _record(3, B1.score_name, 3.0)
    union = _deduplicated_records((a, b), (b, c), (a, c))
    assert {record.candidate_id for record in union} == {
        a.candidate_id,
        b.candidate_id,
        c.candidate_id,
    }
    first = _first_stage_map((a, b), (b, c), (c,))
    assert first[a.candidate_id] == "scout"
    assert first[b.candidate_id] == "scout"
    assert first[c.candidate_id] == "bridge"


def test_final_union_rescore_keeps_every_candidate() -> None:
    case = _fake_case()
    a = _record(1, S2.score_name, 1.0)
    b = _record(2, B1.score_name, 2.0)
    first = {a.candidate_id: "scout", b.candidate_id: "bridge"}
    archive, elapsed, evaluations = _rescore_final_union((a, b), case, F1, first)
    assert len(archive.records) == 2
    assert evaluations == 2
    assert elapsed >= 0.0
    assert all(F1.score_name in record.scores for record in archive.records)
    assert {record.provenance.details["first_stage"] for record in archive.records} == {
        "scout",
        "bridge",
    }


def test_runtime_projection_is_explicit_and_does_not_authorise_overnight() -> None:
    scout = SimpleNamespace(input_count=96, elapsed_s=96.0)
    bridge = SimpleNamespace(input_count=90, elapsed_s=180.0)
    judge = SimpleNamespace(input_count=170, elapsed_s=510.0)
    payload = _runtime_projection(
        scout=scout,
        bridge=bridge,
        judge=judge,
        final_union_count=250,
        final_rescore_elapsed_s=25.0,
    )
    assert payload["safety_factor"] == PROJECTION_SAFETY_FACTOR
    assert set(payload["projected_panels"]) == {"256", "512", "1024"}
    assert payload["overnight_8h"]["authorised_by_this_experiment"] is False
    assert payload["overnight_8h"]["projected_scout_starts_with_safety_factor"] > 0


def test_search_visible_candidate_records_reject_truth_fields() -> None:
    case = _fake_case()
    starts = ({"restart_index": 0, "seed": 1, "variables": [28] * 8},)
    outcome = _run_stage(
        stage_id="scout",
        profile=S2,
        search_case=case,
        inputs=starts,
        sweeps=1,
    )
    payload = outcome.archive.to_json_dict()
    text = str(payload).lower()
    assert "truth" not in text
    assert "reference_metrics" not in text
    assert "expected_plaintext" not in text
