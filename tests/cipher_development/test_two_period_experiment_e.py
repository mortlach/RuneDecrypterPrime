from __future__ import annotations
from cipher_development.two_period_overlay.experiment_e import (
    BENCHMARK,
    CANARY_BLOCK_ID,
    PHASE_A_BLOCK_IDS,
    PHASE_B_BLOCK_IDS,
    SCIENCE_BLOCK_IDS,
    STARTS_PER_BLOCK,
    _classify,
    _runtime_gate,
    build_block_starts,
    panel_seed,
    planned_runtime,
)


def test_pack09_is_primary_only_d30():
    assert BENCHMARK.expected_free_dimension == 30
    assert BENCHMARK.additional_cribs == ()
    assert BENCHMARK.crib_word == "uncomfortable"


def test_block_plan_is_six_by_512():
    assert SCIENCE_BLOCK_IDS == (*PHASE_A_BLOCK_IDS, *PHASE_B_BLOCK_IDS)
    assert len(SCIENCE_BLOCK_IDS) == 6
    assert STARTS_PER_BLOCK == 512
    assert CANARY_BLOCK_ID not in SCIENCE_BLOCK_IDS


def test_starts_are_deterministic_unique_and_d30():
    first = build_block_starts(BENCHMARK, SCIENCE_BLOCK_IDS[0], count=32)
    second = build_block_starts(BENCHMARK, SCIENCE_BLOCK_IDS[0], count=32)
    other = build_block_starts(BENCHMARK, SCIENCE_BLOCK_IDS[1], count=32)
    assert first == second
    assert len({row["seed"] for row in first}) == len(first)
    assert len({tuple(row["variables"]) for row in first}) == len(first)
    assert all((len(row["variables"]) == 30 for row in first))
    assert {row["seed"] for row in first}.isdisjoint({row["seed"] for row in other})


def test_seed_namespace_is_stage_and_block_bound():
    values = {
        panel_seed(BENCHMARK.benchmark_id, 91, "start", "restart-0"),
        panel_seed(BENCHMARK.benchmark_id, 92, "start", "restart-0"),
        panel_seed(BENCHMARK.benchmark_id, 91, "scout", "restart-0"),
    }
    assert len(values) == 3


def test_runtime_plan_uses_d22_scout_evidence():
    plan = planned_runtime()
    assert plan["target_dimension"] == 30
    assert plan["science_blocks"] == 6
    assert plan["total_science_starts"] == 3072
    assert 4.0 < plan["central_science_scout_elapsed_hours"] < 6.0


def test_runtime_gate_contains_no_truth_fields():
    gate = _runtime_gate(
        phase_a_elapsed_s=6000.0, completed_blocks=2, elapsed_before_phase_a_s=300.0
    )
    assert gate["terminal_metrics_opened"] is False
    assert "exact" not in repr(gate).lower()
    assert "match" not in repr(gate).lower()


def _terminal_row(*, exact, rank_one, unique, near):
    return {
        "exact_scout_candidate_count": 1 if exact else 0,
        "static_f1": {
            "archive": {
                "top_scored_candidate_terminal": {"exact_plaintext": rank_one},
                "canonical_key_count": 1 if unique else 2,
                "combined_shift_count": 1 if unique else 2,
            },
            "near" + "_solve_candidate_count": 1 if near else 0,
        },
    }


def test_classification_promotes_two_exact_among_four_blocks():
    rows = [
        _terminal_row(exact=True, rank_one=True, unique=True, near=True),
        _terminal_row(exact=True, rank_one=True, unique=True, near=True),
        _terminal_row(exact=False, rank_one=False, unique=False, near=False),
        _terminal_row(exact=False, rank_one=False, unique=False, near=False),
    ]
    assert _classify(rows)["decision"] == "promote"


def test_classification_refines_one_exact_or_ranking_problem():
    rows = [
        _terminal_row(exact=True, rank_one=False, unique=True, near=True),
        _terminal_row(exact=False, rank_one=False, unique=False, near=False),
        _terminal_row(exact=False, rank_one=False, unique=False, near=False),
        _terminal_row(exact=False, rank_one=False, unique=False, near=False),
    ]
    assert _classify(rows)["decision"] == "refine"


def test_classification_closes_only_complete_weak_panel():
    rows = [
        _terminal_row(exact=False, rank_one=False, unique=False, near=False)
        for _ in range(4)
    ]
    result = _classify(rows)
    assert result["decision"] == "close"
    assert result["automatic_fallback_authorised"] is False
