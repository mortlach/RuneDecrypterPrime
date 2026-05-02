from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate3_phasec_saved_surface_exact_1511_7004 as mod,
)


def test_require_saved_surface_supported_rejects_rescue_enabled() -> None:
    run_config = {
        "stage3": {
            "two_phase": {
                "phase_c": {
                    "rescue_enabled": True,
                    "cfg": {},
                }
            }
        }
    }

    with pytest.raises(NotImplementedError):
        mod._require_saved_surface_supported(run_config)


def test_require_saved_surface_supported_rejects_rescue_candidates() -> None:
    run_config = {
        "stage3": {
            "two_phase": {
                "phase_c": {
                    "rescue_enabled": False,
                    "cfg": {"rescue_candidates": 4},
                }
            }
        }
    }

    with pytest.raises(NotImplementedError):
        mod._require_saved_surface_supported(run_config)


def test_resolve_phasec_seed_honors_override() -> None:
    run_config = {
        "stage3": {
            "solver": {"seed": 7000},
            "two_phase": {"phase_c": {"seed_offset": 23, "cfg": {}}},
        }
    }

    assert int(mod._resolve_phasec_seed(run_config)) == 7023
    assert int(mod._resolve_phasec_seed(run_config, phasec_seed_override=8123)) == 8123


def test_build_comparison_summary_reports_control_candidate_deltas() -> None:
    case = type(
        "Case",
        (),
        {
            "artifact_path": Path("output/mock/final_instances/mock.json"),
            "artifact": {
                "instance_source_key_seed": 1511,
                "search_seed": 7004,
                "stage3_diagnostics": {
                    "phaseC_best_truth_start_summary": {
                        "final_match": 0.571,
                        "source": "phaseB_topk",
                        "candidate_hash": "topk-2",
                        "source_rank": 2,
                    }
                },
            },
        },
    )()
    control_summary = {
        "best_match_ratio": 0.566,
        "pre_phasec_best_match": 0.568,
        "winner_lane": "anchor",
        "winner_source": "stage3_best_phaseB",
        "winner_source_rank": 1,
        "winner_candidate_hash": "anchor",
        "start_identities": [
            {
                "start_rank": 1,
                "source": "stage3_best_phaseB",
                "source_rank": 1,
                "candidate_hash": "anchor",
            },
            {
                "start_rank": 2,
                "source": "phaseB_topk",
                "source_rank": 2,
                "candidate_hash": "topk-2",
            },
        ],
        "phasec_evals": 9216,
    }
    candidate_summary = {
        "best_match_ratio": 0.571,
        "winner_lane": "anchor",
        "winner_source": "phaseB_topk",
        "winner_source_rank": 2,
        "winner_candidate_hash": "topk-2",
        "start_identities": [
            {
                "start_rank": 1,
                "source": "phaseB_topk",
                "source_rank": 2,
                "candidate_hash": "topk-2",
                "selected_by_phaseb_topk_anchor_policy": 1,
            },
            {
                "start_rank": 2,
                "source": "stage3_best_phaseB",
                "source_rank": 1,
                "candidate_hash": "anchor",
            },
        ],
        "phasec_evals": 9216,
    }

    summary = mod.build_comparison_summary(
        case=case,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )

    assert float(summary["retained_stage3_reference_match_ratio"]) == pytest.approx(0.571)
    assert float(summary["control_delta_vs_retained_stage3_reference"]) == pytest.approx(
        -0.005
    )
    assert float(summary["candidate_delta_vs_retained_stage3_reference"]) == pytest.approx(
        0.0
    )
    assert float(summary["candidate_minus_control_best_match_ratio"]) == pytest.approx(
        0.005
    )
    assert int(summary["candidate_reordered_surface"]) == 1
    assert summary["control_start_hashes"] == ["anchor", "topk-2"]
    assert summary["candidate_start_hashes"] == ["topk-2", "anchor"]
