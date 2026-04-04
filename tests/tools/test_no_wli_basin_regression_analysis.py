from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    analyze_basin_regression as mod,
)


pytestmark = pytest.mark.tier_a


def test_extract_stage3_config_fields_handles_old_and_new_shapes() -> None:
    old_cfg = {
        "stage3": {
            "init_keys": 80,
            "two_phase": {
                "phase_a": {"steps": 900, "restarts": 1},
                "phase_b": {"steps": 5200},
                "phase_b_top_n": 24,
            },
        }
    }
    new_cfg = {
        "stage3": {
            "init_keys": 128,
            "two_phase": {
                "phase_a": {"steps": 1000, "restarts": 1},
                "phase_b": {"steps": 3200},
                "phase_b_top_n": 32,
                "phase_c": {"enabled": True, "start_keys": 5},
            },
            "stage35": {"enabled": True, "cfg": {"rounds": 3, "beam_width": 4}},
        }
    }

    old = mod.extract_stage3_config_fields(old_cfg)
    new = mod.extract_stage3_config_fields(new_cfg)

    assert old == {
        "init_keys": 80,
        "phaseA_steps": 900,
        "phaseA_restarts": 1,
        "phaseB_steps": 5200,
        "phaseB_top_n": 24,
        "phaseC_enabled": 0,
        "phaseC_start_keys": 0,
        "stage35_requested": 0,
        "stage35_rounds": 0,
        "stage35_beam_width": 0,
    }
    assert new == {
        "init_keys": 128,
        "phaseA_steps": 1000,
        "phaseA_restarts": 1,
        "phaseB_steps": 3200,
        "phaseB_top_n": 32,
        "phaseC_enabled": 1,
        "phaseC_start_keys": 5,
        "stage35_requested": 1,
        "stage35_rounds": 3,
        "stage35_beam_width": 4,
    }


def test_classify_regression_prefers_inside_stage3_when_stage2_is_flat() -> None:
    out = mod.classify_regression(
        old_summary={
            "stage2_topk_top5_mean": 0.10,
            "stage3_topk_top5_mean": 0.77,
            "best_match_ratio": 0.773,
            "stage3_cfg": {"phaseB_steps": 5200, "init_keys": 80},
        },
        new_summary={
            "stage2_topk_top5_mean": 0.10,
            "stage3_topk_top5_mean": 0.64,
            "best_match_ratio": 0.668,
            "stage3_cfg": {"phaseB_steps": 3200, "init_keys": 128},
        },
    )

    assert str(out["primary_culprit"]) == "inside_stage3_basin_generation"
    assert "Stage-2 candidate quality is effectively unchanged" in str(out["rationale"])


def test_classify_regression_can_flag_pre_stage3_regression() -> None:
    out = mod.classify_regression(
        old_summary={
            "stage2_topk_top5_mean": 0.20,
            "stage3_topk_top5_mean": 0.77,
            "best_match_ratio": 0.773,
            "stage3_cfg": {"phaseB_steps": 5200, "init_keys": 80},
        },
        new_summary={
            "stage2_topk_top5_mean": 0.10,
            "stage3_topk_top5_mean": 0.11,
            "best_match_ratio": 0.15,
            "stage3_cfg": {"phaseB_steps": 3200, "init_keys": 128},
        },
    )

    assert str(out["primary_culprit"]) == "pre_stage3_regression"


def test_classify_regression_can_flag_late_handoff_regression() -> None:
    out = mod.classify_regression(
        old_summary={
            "stage2_topk_top5_mean": 0.10,
            "stage3_topk_top5_mean": 0.77,
            "best_match_ratio": 0.773,
            "stage3_cfg": {"phaseB_steps": 5200, "init_keys": 80},
        },
        new_summary={
            "stage2_topk_top5_mean": 0.10,
            "stage3_topk_top5_mean": 0.769,
            "best_match_ratio": 0.66,
            "stage3_cfg": {"phaseB_steps": 5200, "init_keys": 80},
        },
    )

    assert str(out["primary_culprit"]) == "late_handoff_regression"
