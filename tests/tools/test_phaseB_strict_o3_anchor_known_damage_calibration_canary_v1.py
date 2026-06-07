from __future__ import annotations

import ast
import csv
import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "run_phaseB_strict_o3_anchor_known_damage_calibration_canary_v1.py"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "phaseB_strict_o3_anchor_known_damage_calibration_canary_v2_fix"
)


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_known_damage_canary_runner_uses_hardcoded_repo_configuration() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "argparse" not in imported_modules


def test_known_damage_canary_manifest_is_complete_and_report_only() -> None:
    manifest = json.loads((OUTPUT_DIR / "known_damage_calibration_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "known_damage_canary_complete"
    assert manifest["clean_chunk_count"] == 2
    assert manifest["sample_count"] == 38
    assert manifest["samples_per_clean_chunk"] == 19
    assert manifest["runtime_chunk_count"] == 774
    assert manifest["completed_runtime_chunk_count"] == 774
    assert manifest["hit_count"] > 0
    assert manifest["damage_generation_contract"] == "target_actual_changed_fraction"
    assert manifest["structured_damage_shape_contract"] == "preserve_model_shape_and_requested_global_changed_fraction"
    assert manifest["damage_tolerance"] == 0.01
    assert manifest["legacy_nominal_damage_models_not_used_for_damaged_samples"] is True
    assert manifest["ordinary_null_models"] == [
        "uniform_random",
        "global_frequency_random",
        "within_chunk_shuffle",
    ]
    assert manifest["hard_local_order_control_models"] == [
        "block_shuffle_10",
        "block_shuffle_25",
        "block_shuffle_50",
    ]
    assert manifest["lens_names"] == ["HD0_L10", "HD0_L12", "HDle1_L12", "HDle2_L15"]
    assert manifest["phrase_rarity_weighting_active"] is False
    assert len(manifest["runtime_projection_rows"]) == 6
    assert manifest["report_only"] is True
    assert manifest["require_fwd_only"] is True
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False


def test_known_damage_canary_sample_and_summary_shapes_are_stable() -> None:
    samples = read_csv("calibration_sample_rows.csv")
    summaries = read_csv("known_damage_anchor_summary_rows.csv")
    group_rows = read_csv("known_damage_vs_null_summary_rows.csv")

    assert len(samples) == 38
    assert len(summaries) == 152
    assert len(group_rows) == 76

    source_counts: dict[str, int] = {}
    for sample in samples:
        source_counts[sample["source_kind"]] = source_counts.get(sample["source_kind"], 0) + 1
    assert source_counts == {
        "clean": 2,
        "damaged": 24,
        "ordinary_null": 6,
        "hard_local_order_control": 6,
    }

    for sample in samples:
        assert sample["source_kind"] != "null"
        if sample["source_kind"] == "damaged":
            requested = float(sample["requested_damage_level"])
            actual = float(sample["actual_changed_fraction"])
            assert math.isclose(actual, requested, abs_tol=0.01)
            assert sample["damage_contract_status"] == "pass"
            assert sample["damage_shape"]
            assert sample["damage_shape_metadata"]


def test_known_damage_canary_headline_group_rows_are_stable() -> None:
    rows = read_csv("known_damage_vs_null_summary_rows.csv")
    by_key = {
        (row["lens_name"], row["source_kind"], row["model_name"], row["requested_damage_level"]): row
        for row in rows
    }

    clean = by_key[("HD0_L10", "clean", "none", "")]
    assert clean["row_count"] == "2"
    assert int(clean["nonzero_selected_region_count"]) > 0

    uniform = by_key[("HD0_L10", "ordinary_null", "uniform_random", "")]
    assert uniform["row_count"] == "2"
    assert uniform["selected_weight_sum_mean"] == "0.0"
    assert uniform["nonzero_selected_region_count"] == "0"

    block50 = by_key[("HD0_L10", "hard_local_order_control", "block_shuffle_50", "")]
    assert block50["row_count"] == "2"
    assert int(block50["nonzero_selected_region_count"]) > 0


def test_known_damage_canary_summaries_do_not_collapse_damage_levels() -> None:
    rows = read_csv("known_damage_vs_null_summary_rows.csv")
    damage_keys = {
        (row["lens_name"], row["model_name"], row["requested_damage_level"])
        for row in rows
        if row["source_kind"] == "damaged"
    }
    assert ("HD0_L10", "independent_substitution", "0.30") in damage_keys
    assert ("HD0_L10", "independent_substitution", "0.50") in damage_keys
    assert len([key for key in damage_keys if key[0] == "HD0_L10"]) == 12
