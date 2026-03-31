from __future__ import annotations

import pytest
from rune_decrypter_prime.api.specs import SolverSpec

from tools.benchmarks.periodic_sub_trans.no_wli.stage3_seeding import (
    prepare_stage3_refine_inputs,
)


pytestmark = pytest.mark.tier_a


def _build_promoted_keys(**kwargs):
    _ = kwargs
    return [
        [1, 1, 1],
        [2, 2, 2],
        [3, 3, 3],
    ]


def _mutate_full_key(seed_key, *, period, columns, seed, n):
    _ = (period, columns, seed)
    out = []
    for idx in range(int(n)):
        mutated = list(map(int, seed_key))
        mutated[-1] = int(seed_key[0]) * 10 + int(idx) + 1
        out.append(mutated)
    return out


def _resolve_stage3_gap_and_band(**kwargs):
    _ = kwargs
    return (
        float("nan"),
        {
            "name": "mid",
            "steps": 2400,
            "restarts": 2,
            "plateau_rounds": 260,
            "col_batch": 112,
            "inner_batch": 128,
        },
        False,
    )


def _base_kwargs() -> dict[str, object]:
    return dict(
        tier_period=9,
        tier_columns=3,
        key_len=3,
        key_seed=211,
        best2_key=[9, 9, 9],
        best2_match=0.2,
        stage2_promoted=[
            {"key": [1, 1, 1], "match": 0.11},
            {"key": [2, 2, 2], "match": 0.12},
            {"key": [3, 3, 3], "match": 0.13},
        ],
        stage2_entry_score=-4.9,
        stage2_entry_score_judge=-4.8,
        scorer_stage2={"objective": "avg.logp.win20"},
        scorer_full={"objective": "avg.logp.win20"},
        stage3_dynamic_bands=[],
        oracle_s3=float("nan"),
        oracle_decision_paths_enabled=False,
        stage2_entry_band_by_stage3_judge=False,
        stage3_c1_focus_enabled_cfg=False,
        stage3_c1_init_keys=96,
        stage3_initial_keys=4,
        stage3_initial_keys_by_columns={3: 4},
        stage3_period_init_mult_by_period={},
        stage3_period_step_mult_by_period={},
        stage3_period_restart_bonus_by_period={},
        stage3_init_keys_cap=0,
        stage3_phasea_cfg={"steps": 800},
        stage3_phaseb_cfg={"steps": 2200},
        stage3_phaseb_top_n=8,
        stage3_phaseb_gate_delta_floor=0.003,
        stage3_phaseb_gate_end_gain_floor=0.001,
        stage3_c1_phasea_steps=1200,
        stage3_c1_phaseb_steps=6000,
        stage3_c1_phaseb_top_n=24,
        stage3_c1_phaseb_gate_delta_floor=0.01,
        stage3_c1_phaseb_gate_end_gain_floor=0.006,
        solver_stage3_cfg={
            "steps": 3200,
            "restarts": 2,
            "plateau_rounds": 320,
            "col_batch": 128,
            "inner_batch": 128,
        },
        stage3_entry_allocation_policy="legacy_fixed_budget",
        stage3_entry_mutations_per_promoted=1,
        build_stage3_promoted_keys_fn=_build_promoted_keys,
        mutate_full_key_fn=_mutate_full_key,
        objective_space_key_fn=lambda cfg: str(cfg.get("objective", "")),
        resolve_stage3_gap_and_band_fn=_resolve_stage3_gap_and_band,
    )


def test_prepare_stage3_refine_inputs_preserves_legacy_fixed_budget_behavior() -> None:
    out = prepare_stage3_refine_inputs(**_base_kwargs())

    assert str(out["stage3_entry_allocation_policy"]) == "legacy_fixed_budget"
    assert int(out["stage3_entry_base_budget"]) == 4
    assert int(out["stage3_entry_target_before_cap"]) == 4
    assert int(out["stage3_entry_mutations_per_promoted_cfg"]) == 1
    assert int(out["stage3_entry_mutation_calls_per_promoted"]) == 2
    assert int(out["init3_n"]) == 4
    assert "entry_allocation_policy" not in dict(out["solver_stage3_cfg"])
    assert "entry_mutations_per_promoted" not in dict(out["solver_stage3_cfg"])
    solver = SolverSpec.kaeding(**dict(out["solver_stage3_cfg"]))
    assert str(solver.name) == "kaeding"
    assert out["init3"] == [
        [1, 1, 1],
        [1, 1, 11],
        [1, 1, 12],
        [2, 2, 2],
    ]


def test_prepare_stage3_refine_inputs_constant_local_depth_scales_budget_and_round_robins() -> None:
    kwargs = _base_kwargs()
    kwargs["stage3_entry_allocation_policy"] = "constant_local_depth"
    kwargs["stage3_entry_mutations_per_promoted"] = 2

    out = prepare_stage3_refine_inputs(**kwargs)

    assert str(out["stage3_entry_allocation_policy"]) == "constant_local_depth"
    assert int(out["stage3_entry_base_budget"]) == 4
    assert int(out["stage3_entry_target_before_cap"]) == 9
    assert int(out["stage3_entry_mutations_per_promoted_cfg"]) == 2
    assert int(out["stage3_entry_mutation_calls_per_promoted"]) == 2
    assert int(out["init3_n"]) == 9
    assert "entry_allocation_policy" not in dict(out["solver_stage3_cfg"])
    assert "entry_mutations_per_promoted" not in dict(out["solver_stage3_cfg"])
    solver = SolverSpec.kaeding(**dict(out["solver_stage3_cfg"]))
    assert str(solver.name) == "kaeding"
    assert out["init3"] == [
        [1, 1, 1],
        [2, 2, 2],
        [3, 3, 3],
        [1, 1, 11],
        [2, 2, 21],
        [3, 3, 31],
        [1, 1, 12],
        [2, 2, 22],
        [3, 3, 32],
    ]


def test_prepare_stage3_refine_inputs_constant_local_depth_respects_cap() -> None:
    kwargs = _base_kwargs()
    kwargs["stage3_init_keys_cap"] = 7
    kwargs["stage3_entry_allocation_policy"] = "constant_local_depth"
    kwargs["stage3_entry_mutations_per_promoted"] = 2

    out = prepare_stage3_refine_inputs(**kwargs)

    assert int(out["stage3_entry_target_before_cap"]) == 9
    assert int(out["stage3_entry_cap"]) == 7
    assert bool(out["stage3_entry_cap_applied"]) is True
    assert int(out["init3_n"]) == 7
    assert "entry_allocation_policy" not in dict(out["solver_stage3_cfg"])
    assert "entry_mutations_per_promoted" not in dict(out["solver_stage3_cfg"])
    solver = SolverSpec.kaeding(**dict(out["solver_stage3_cfg"]))
    assert str(solver.name) == "kaeding"
    assert out["init3"] == [
        [1, 1, 1],
        [2, 2, 2],
        [3, 3, 3],
        [1, 1, 11],
        [2, 2, 21],
        [3, 3, 31],
        [1, 1, 12],
    ]
