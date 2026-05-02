from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1 as mod,
)


pytestmark = pytest.mark.tier_a


def test_gate_verdict_uses_current_threshold() -> None:
    assert mod._gate_verdict(0.30) == "keep"
    assert mod._gate_verdict(0.299) == "filter"
    assert mod._gate_verdict(float("nan")) == "unknown"


def test_build_summary_advances_for_shared_early_checkpoint() -> None:
    rows = [
        {
            "search_seed": 7002,
            "checkpoint_restart_count": 32,
            "verdict_matches_expected": 1,
            "checkpoint_elapsed_share": 0.42,
            "checkpoint_share_improvement_vs_late_gate": 0.46,
        },
        {
            "search_seed": 7003,
            "checkpoint_restart_count": 32,
            "verdict_matches_expected": 1,
            "checkpoint_elapsed_share": 0.47,
            "checkpoint_share_improvement_vs_late_gate": 0.41,
        },
    ]
    late_gate_reference_rows = {
        7002: {"late_gate_elapsed_share": 0.88},
        7003: {"late_gate_elapsed_share": 0.89},
    }

    out = mod._build_summary(
        checkpoint_rows=rows,
        late_gate_reference_rows=late_gate_reference_rows,
    )

    assert out["recommendation"] == "advance"
    assert out["earliest_shared_checkpoint_restart_count"] == 32


def test_build_summary_holds_when_no_shared_checkpoint_matches() -> None:
    rows = [
        {
            "search_seed": 7002,
            "checkpoint_restart_count": 32,
            "verdict_matches_expected": 1,
            "checkpoint_elapsed_share": 0.42,
            "checkpoint_share_improvement_vs_late_gate": 0.46,
        },
        {
            "search_seed": 7003,
            "checkpoint_restart_count": 32,
            "verdict_matches_expected": 0,
            "checkpoint_elapsed_share": 0.47,
            "checkpoint_share_improvement_vs_late_gate": 0.41,
        },
    ]
    late_gate_reference_rows = {
        7002: {"late_gate_elapsed_share": 0.88},
        7003: {"late_gate_elapsed_share": 0.89},
    }

    out = mod._build_summary(
        checkpoint_rows=rows,
        late_gate_reference_rows=late_gate_reference_rows,
    )

    assert out["recommendation"] == "hold"
    assert out["earliest_shared_checkpoint_restart_count"] == 0
