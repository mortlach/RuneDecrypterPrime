from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_candidate3_saved_surface_exact_matrix_v1 as mod,
)


def test_classify_control_fidelity_distinguishes_stable_near_stable_and_drifted() -> None:
    assert mod.classify_control_fidelity(control_delta_vs_retained=0.0) == "stable"
    assert mod.classify_control_fidelity(control_delta_vs_retained=-0.002) == "near_stable"
    assert mod.classify_control_fidelity(control_delta_vs_retained=-0.050) == "drifted"


def test_classify_candidate_effect_distinguishes_positive_neutral_and_negative() -> None:
    assert mod.classify_candidate_effect(candidate_minus_control=0.004) == "positive"
    assert mod.classify_candidate_effect(candidate_minus_control=0.0) == "neutral"
    assert mod.classify_candidate_effect(candidate_minus_control=-0.002) == "negative"


def test_build_case_row_marks_usable_gate_only_for_stable_or_near_stable() -> None:
    row = mod.build_case_row(
        bundle_rel_path=mod.CASE_BUNDLE_REL_PATHS[0],
        comparison_summary={
            "fixture_seed": 1111,
            "search_seed": 7002,
            "source_artifact_relpath": "output/mock.json",
            "retained_stage3_reference_match_ratio": 0.752,
            "control_best_match_ratio": 0.750,
            "candidate_best_match_ratio": 0.754,
            "control_delta_vs_retained_stage3_reference": -0.002,
            "candidate_delta_vs_retained_stage3_reference": 0.002,
            "candidate_minus_control_best_match_ratio": 0.004,
            "candidate_reordered_surface": 1,
            "control_winner_source": "phaseB_topk",
            "candidate_winner_source": "phaseB_topk",
            "control_winner_candidate_hash": "a",
            "candidate_winner_candidate_hash": "b",
        },
    )

    assert row["control_fidelity_quality"] == "near_stable"
    assert int(row["usable_decision_gate"]) == 1
    assert row["decision_gate_read"] == "positive"


def test_build_summary_counts_gate_and_context_rows() -> None:
    rows = [
        {
            "fixture_seed": 1511,
            "usable_decision_gate": 1,
            "candidate_effect": "negative",
            "decision_gate_read": "negative",
        },
        {
            "fixture_seed": 1111,
            "usable_decision_gate": 1,
            "candidate_effect": "positive",
            "decision_gate_read": "positive",
        },
        {
            "fixture_seed": 1111,
            "usable_decision_gate": 0,
            "candidate_effect": "neutral",
            "decision_gate_read": "context_only",
        },
    ]

    summary = mod.build_summary(rows)

    assert int(summary["case_count"]) == 3
    assert int(summary["usable_decision_gate_cases"]) == 2
    assert int(summary["drifted_context_cases"]) == 1
    assert int(summary["positive_on_decision_gate"]) == 1
    assert int(summary["negative_on_decision_gate"]) == 1
    fixture_rows = list(summary["fixture_summary_rows"])
    assert fixture_rows == [
        {
            "fixture_seed": 1111,
            "case_count": 2,
            "usable_decision_gate_cases": 1,
            "positive_cases": 1,
            "neutral_cases": 0,
            "negative_cases": 0,
            "context_only_cases": 1,
        },
        {
            "fixture_seed": 1511,
            "case_count": 1,
            "usable_decision_gate_cases": 1,
            "positive_cases": 0,
            "neutral_cases": 0,
            "negative_cases": 1,
            "context_only_cases": 0,
        },
    ]
