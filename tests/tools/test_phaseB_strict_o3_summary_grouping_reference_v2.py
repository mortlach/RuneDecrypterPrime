from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.summary_grouping_reference_v2 import (
    actual_changed_fraction_bin,
    calibration_summary_rows,
)


def test_changed_fraction_bins_are_explicit() -> None:
    assert actual_changed_fraction_bin(0.0) == "0.00-0.10"
    assert actual_changed_fraction_bin(0.099) == "0.00-0.10"
    assert actual_changed_fraction_bin(0.30) == "0.30-0.40"
    assert actual_changed_fraction_bin(0.50) == "0.50-0.60"


def test_summary_keeps_damage_level_and_control_class_separate() -> None:
    rows = [
        {
            "lens_name": "HD0_L10",
            "source_kind": "damaged",
            "model_name": "independent_substitution",
            "requested_damage_level": "0.30",
            "actual_changed_fraction": "0.30",
            "selected_weight": "10",
        },
        {
            "lens_name": "HD0_L10",
            "source_kind": "damaged",
            "model_name": "independent_substitution",
            "requested_damage_level": "0.50",
            "actual_changed_fraction": "0.50",
            "selected_weight": "4",
        },
        {
            "lens_name": "HD0_L10",
            "source_kind": "control",
            "model_name": "block_shuffle_50",
            "requested_damage_level": "",
            "actual_changed_fraction": "",
            "selected_weight": "8",
        },
        {
            "lens_name": "HD0_L10",
            "source_kind": "control",
            "model_name": "uniform_random",
            "requested_damage_level": "",
            "actual_changed_fraction": "",
            "selected_weight": "0",
        },
    ]
    summary = calibration_summary_rows(rows)
    keys = {
        (row["model_name"], row["requested_damage_level"], row["null_class"], row["actual_changed_fraction_bin"])
        for row in summary
    }
    assert ("independent_substitution", "0.30", "damaged", "0.30-0.40") in keys
    assert ("independent_substitution", "0.50", "damaged", "0.50-0.60") in keys
    assert ("block_shuffle_50", "", "hard_local_order_control", "") in keys
    assert ("uniform_random", "", "ordinary_null", "") in keys
