from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1 as mod,
)


pytestmark = pytest.mark.tier_a


def test_gate_verdict_uses_refined_rule() -> None:
    assert mod._gate_verdict(rank1_init_match=0.31, best_init_match=0.31) == "keep"
    assert mod._gate_verdict(rank1_init_match=0.24, best_init_match=0.44) == "keep"
    assert mod._gate_verdict(rank1_init_match=0.24, best_init_match=0.43) == "filter"


def test_trigger_source_reports_rescue_path() -> None:
    assert (
        mod._trigger_source(rank1_init_match=0.31, best_init_match=0.44)
        == "rank1_floor"
    )
    assert (
        mod._trigger_source(rank1_init_match=0.24, best_init_match=0.44)
        == "high_best_rescue"
    )
    assert mod._trigger_source(rank1_init_match=0.24, best_init_match=0.43) == "filter"


def test_build_summary_advances_on_shared_confirmation_checkpoint() -> None:
    rows = [
        {
            "search_seed": 7001,
            "checkpoint_restart_count": 16,
            "verdict_matches_expected": 1,
            "checkpoint_elapsed_share": 0.21,
            "checkpoint_share_improvement_vs_late_gate": 0.67,
        },
        {
            "search_seed": 7005,
            "checkpoint_restart_count": 16,
            "verdict_matches_expected": 1,
            "checkpoint_elapsed_share": 0.23,
            "checkpoint_share_improvement_vs_late_gate": 0.65,
        },
    ]

    out = mod._build_summary(rows)

    assert out["recommendation"] == "advance"
    assert out["earliest_shared_checkpoint_restart_count"] == 16
