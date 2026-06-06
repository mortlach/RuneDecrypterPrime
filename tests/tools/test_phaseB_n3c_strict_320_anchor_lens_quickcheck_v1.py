from __future__ import annotations

import ast
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "run_phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1.py"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1"
)


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_anchor_lens_script_uses_hardcoded_repo_configuration() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "argparse" not in imported_modules


def test_anchor_lens_manifest_is_report_only_and_complete() -> None:
    manifest = json.loads((OUTPUT_DIR / "anchor_lens_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "anchor_lens_quickcheck_complete"
    assert manifest["input_hit_rows_read"] == 6_415_767
    assert manifest["expected_hit_rows"] == 6_415_767
    assert manifest["input_file_count"] == 20
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False
    assert manifest["report_only"] is True


def test_anchor_lens_margin_table_contains_requested_lenses_and_thresholds() -> None:
    rows = read_csv("anchor_lens_margin_threshold_rows.csv")
    lenses = {row["lens_name"] for row in rows}
    thresholds_by_lens: dict[str, set[str]] = {}
    for row in rows:
        thresholds_by_lens.setdefault(row["lens_name"], set()).add(row["min_absolute_score_margin"])

    assert lenses == {
        "hd0_len8",
        "hd0_len10",
        "hd0_len12",
        "hd0_len15",
        "hd_le1_len12",
        "hd_le1_len15",
        "hd_le2_len12",
        "hd_le2_len15",
    }
    for thresholds in thresholds_by_lens.values():
        assert thresholds == {
            "0.000000",
            "1.000000",
            "2.000000",
            "5.000000",
            "10.000000",
            "20.000000",
            "50.000000",
            "100.000000",
        }


def test_anchor_lens_quickcheck_headline_result_is_stable() -> None:
    rows = read_csv("anchor_lens_margin_threshold_rows.csv")
    by_key = {
        (row["lens_name"], row["min_absolute_score_margin"]): row
        for row in rows
    }

    hd0_len10_margin20 = by_key[("hd0_len10", "20.000000")]
    assert hd0_len10_margin20["covered_pair_count"] == "251"
    assert hd0_len10_margin20["agree_count"] == "227"
    assert hd0_len10_margin20["break_count"] == "24"
    assert hd0_len10_margin20["break_rate"] == "0.095618"

    hd0_len12_all = by_key[("hd0_len12", "0.000000")]
    assert hd0_len12_all["covered_pair_count"] == "22"
    assert hd0_len12_all["break_count"] == "0"
    assert hd0_len12_all["break_rate"] == "0.000000"
