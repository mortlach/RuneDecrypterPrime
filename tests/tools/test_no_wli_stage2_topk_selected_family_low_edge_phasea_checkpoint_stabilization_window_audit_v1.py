from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1 as mod,
)


def _make_row(
    *,
    search_seed: int,
    checkpoint_restart_count: int,
    best_init: float,
    best_final: float | None = None,
    rank1_init: float = 0.243,
    rank1_final: float = 0.243,
    plateau: int = 0,
) -> dict[str, object]:
    return {
        "search_seed": search_seed,
        "checkpoint_restart_count": checkpoint_restart_count,
        "phaseA_best_init_match": best_init,
        "phaseA_best_final_match": best_init if best_final is None else best_final,
        "phaseA_rank1_init_match": rank1_init,
        "phaseA_rank1_final_match": rank1_final,
        "phaseA_rank1_plateau_would_stop": plateau,
        "checkpoint_elapsed_share": 0.2 if checkpoint_restart_count == 16 else 0.4,
        "checkpoint_share_improvement_vs_late_gate": 0.6 if checkpoint_restart_count == 16 else 0.4,
    }


def test_window_audit_selects_restart32_when_7002_stabilizes_late() -> None:
    rows = []
    per_seed_values = {
        7001: {16: 0.378, 32: 0.378, 48: 0.378, 64: 0.378},
        7002: {16: 0.289, 32: 0.329, 48: 0.329, 64: 0.329},
        7003: {16: 0.490, 32: 0.490, 48: 0.490, 64: 0.490},
        7004: {16: 0.415, 32: 0.415, 48: 0.415, 64: 0.415},
        7005: {16: 0.395, 32: 0.395, 48: 0.395, 64: 0.395},
    }
    for seed, by_checkpoint in per_seed_values.items():
        for checkpoint, value in by_checkpoint.items():
            rows.append(
                _make_row(
                    search_seed=seed,
                    checkpoint_restart_count=checkpoint,
                    best_init=value,
                )
            )

    window_rows = mod._window_statistics(rows)
    summary = mod._build_summary(window_rows)

    assert summary["recommendation"] == "advance"
    assert summary["selected_field_name"] == "phaseA_best_init_match"
    assert summary["selected_window_start_restart_count"] == 32
    assert abs(summary["selected_threshold_midpoint"] - 0.3865) < 1e-12


def test_window_audit_holds_when_no_window_separates() -> None:
    rows = []
    per_seed_values = {
        7001: {16: 0.378, 32: 0.378, 48: 0.378, 64: 0.378},
        7002: {16: 0.289, 32: 0.391, 48: 0.391, 64: 0.391},
        7003: {16: 0.390, 32: 0.390, 48: 0.390, 64: 0.390},
        7004: {16: 0.415, 32: 0.415, 48: 0.415, 64: 0.415},
        7005: {16: 0.395, 32: 0.395, 48: 0.395, 64: 0.395},
    }
    for seed, by_checkpoint in per_seed_values.items():
        for checkpoint, value in by_checkpoint.items():
            rows.append(
                _make_row(
                    search_seed=seed,
                    checkpoint_restart_count=checkpoint,
                    best_init=value,
                )
            )

    window_rows = mod._window_statistics(rows)
    summary = mod._build_summary(window_rows)

    assert summary["recommendation"] == "hold"
    assert summary["selected_field_name"] == ""
