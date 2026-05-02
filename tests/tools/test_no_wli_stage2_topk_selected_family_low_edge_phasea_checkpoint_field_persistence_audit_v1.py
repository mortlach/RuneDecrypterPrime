from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1 as mod,
)


def _make_row(
    *,
    search_seed: int,
    checkpoint_restart_count: int,
    best_init: float,
    best_final: float,
    rank1_init: float = 0.243,
    rank1_final: float = 0.243,
    plateau: int = 0,
) -> dict[str, object]:
    return {
        "search_seed": search_seed,
        "checkpoint_restart_count": checkpoint_restart_count,
        "phaseA_best_init_match": best_init,
        "phaseA_best_final_match": best_final,
        "phaseA_rank1_init_match": rank1_init,
        "phaseA_rank1_final_match": rank1_final,
        "phaseA_rank1_plateau_would_stop": plateau,
    }


def test_field_statistics_prefers_best_init_when_it_separates() -> None:
    rows = []
    values = {
        7001: 0.378,
        7002: 0.329,
        7003: 0.490,
        7004: 0.415,
        7005: 0.395,
    }
    for seed, best_value in values.items():
        for checkpoint in mod.CHECKPOINT_COUNTS:
            rows.append(
                _make_row(
                    search_seed=seed,
                    checkpoint_restart_count=checkpoint,
                    best_init=best_value,
                    best_final=best_value,
                )
            )

    field_rows = mod._field_statistics(rows)
    summary = mod._build_summary(rows=rows, field_rows=field_rows)

    assert summary["recommendation"] == "advance"
    assert summary["selected_field_name"] == "phaseA_best_init_match"
    assert abs(summary["selected_filtered_max"] - 0.378) < 1e-12
    assert abs(summary["selected_kept_min"] - 0.395) < 1e-12
    assert abs(summary["selected_threshold_midpoint"] - 0.3865) < 1e-12


def test_field_statistics_hold_without_separating_field() -> None:
    rows = []
    values = {
        7001: 0.378,
        7002: 0.329,
        7003: 0.360,
        7004: 0.415,
        7005: 0.395,
    }
    for seed, best_value in values.items():
        for checkpoint in mod.CHECKPOINT_COUNTS:
            rows.append(
                _make_row(
                    search_seed=seed,
                    checkpoint_restart_count=checkpoint,
                    best_init=best_value,
                    best_final=best_value,
                )
            )

    field_rows = mod._field_statistics(rows)
    summary = mod._build_summary(rows=rows, field_rows=field_rows)

    assert summary["recommendation"] == "hold"
    assert summary["selected_field_name"] == ""
