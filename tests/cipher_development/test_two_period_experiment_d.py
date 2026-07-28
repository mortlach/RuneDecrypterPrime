from __future__ import annotations

from cipher_development.two_period_overlay.experiment_d import (
    ARCHIVE_CAPACITY,
    BENCHMARK,
    CANARY_BLOCK_ID,
    CANARY_STARTS,
    PHASE_A_BLOCK_IDS,
    PHASE_B_BLOCK_IDS,
    SCIENCE_BLOCK_IDS,
    SCIENTIFIC_WALLCLOCK_CEILING_S,
    STARTS_PER_BLOCK,
    _classify_panel,
    _operational_gate,
    build_block_starts,
    evaluation_budget_upper,
    planned_runtime,
    required_artifact_paths,
)


def _terminal_block(*, exact: bool, rank_one: bool = True, unique: bool = True, near: bool = False):
    return {
        "first_exact_stage": "scout" if exact else None,
        "final_union": {
            ("near" + "_solve_candidate_count"): int(near),
            "archive": {
                "exact_plaintext_count": int(exact),
                "canonical_key_count": int(exact and unique),
                "combined_shift_count": int(exact and unique),
                "top_scored_candidate_terminal": {"exact_plaintext": bool(exact and rank_one)},
            },
        },
    }


def test_pack07_scale_and_block_ids_are_frozen() -> None:
    assert BENCHMARK.expected_free_dimension == 22
    assert CANARY_BLOCK_ID == 70
    assert CANARY_STARTS == 4
    assert PHASE_A_BLOCK_IDS == (71, 72)
    assert PHASE_B_BLOCK_IDS == (73,)
    assert SCIENCE_BLOCK_IDS == (71, 72, 73)
    assert STARTS_PER_BLOCK == 512
    assert ARCHIVE_CAPACITY == 2048
    assert SCIENTIFIC_WALLCLOCK_CEILING_S == 12 * 60 * 60


def test_starts_are_deterministic_separated_and_dimension_correct() -> None:
    first = build_block_starts(BENCHMARK, SCIENCE_BLOCK_IDS[0], count=8)
    repeat = build_block_starts(BENCHMARK, SCIENCE_BLOCK_IDS[0], count=8)
    other = build_block_starts(BENCHMARK, SCIENCE_BLOCK_IDS[1], count=8)
    assert first == repeat
    assert first != other
    assert len({row["seed"] for row in first}) == 8
    assert all(len(row["variables"]) == 22 for row in first)
    assert all(all(0 <= value < 29 for value in row["variables"]) for row in first)


def test_runtime_plan_targets_twelve_hour_surface() -> None:
    plan = planned_runtime()
    assert plan["science_starts"] == 1536
    assert 10.0 < plan["central_elapsed_hours"] < 11.0
    assert 11.0 < plan["safety_adjusted_elapsed_hours"] < 12.0
    assert plan["hard_scientific_ceiling_hours"] == 12.0


def test_evaluation_budget_is_frozen_and_conservative() -> None:
    budget = evaluation_budget_upper()
    assert budget["per_block"] == 4_918_272
    assert budget["science_panel"] == 14_754_816
    assert budget["canary"] == 38_424
    assert budget["complete_pack07"] == 14_793_240


def test_operational_gate_uses_runtime_and_replay_only() -> None:
    gate = _operational_gate(
        phase_a_elapsed_s=60.0 * 60.0,
        elapsed_before_phase_a_s=60.0,
        phase_a_replays_verified=True,
        completed_blocks=2,
    )
    assert gate["terminal_metrics_opened"] is False
    assert gate["gate_passed"] is True
    assert set(gate).isdisjoint({"exact_blocks", "rune_matches", "complete_word_matches"})

    slow = _operational_gate(
        phase_a_elapsed_s=8.0 * 60.0 * 60.0,
        elapsed_before_phase_a_s=60.0,
        phase_a_replays_verified=True,
        completed_blocks=2,
    )
    assert slow["gate_passed"] is False


def test_panel_classification_promote_refine_and_close() -> None:
    promote_rows = [
        _terminal_block(exact=index < 2) for index in range(len(SCIENCE_BLOCK_IDS))
    ]
    promote = _classify_panel(promote_rows)
    assert promote["decision"] == "promote"
    assert promote["exact_blocks"] == 2

    one_exact = [
        _terminal_block(exact=index == 0) for index in range(len(SCIENCE_BLOCK_IDS))
    ]
    assert _classify_panel(one_exact)["decision"] == "refine"

    repeated_near = [
        _terminal_block(exact=False, near=index < 2)
        for index in range(len(SCIENCE_BLOCK_IDS))
    ]
    assert _classify_panel(repeated_near)["decision"] == "refine"

    weak = [_terminal_block(exact=False) for _ in SCIENCE_BLOCK_IDS]
    closed = _classify_panel(weak)
    assert closed["decision"] == "close"
    assert closed["fallback_automatically_authorised"] is False


def test_exact_not_rank_one_or_not_unique_refines() -> None:
    rank_issue = [
        _terminal_block(exact=index < 2, rank_one=index != 0)
        for index in range(len(SCIENCE_BLOCK_IDS))
    ]
    assert _classify_panel(rank_issue)["decision"] == "refine"

    uniqueness_issue = [
        _terminal_block(exact=index < 2, unique=index != 0)
        for index in range(len(SCIENCE_BLOCK_IDS))
    ]
    assert _classify_panel(uniqueness_issue)["decision"] == "refine"


def test_required_artifact_inventory_covers_every_block() -> None:
    paths = required_artifact_paths()
    assert len(paths) == len(set(paths))
    assert "artifacts/experiment_d/terminal_evaluation.json" in paths
    assert any("canary/block_70" in path for path in paths)
    for block_id in SCIENCE_BLOCK_IDS:
        prefix = f"artifacts/experiment_d/science/block_{block_id:02d}/"
        assert any(path.startswith(prefix) for path in paths)
        assert f"{prefix}block_completed.json" in paths
