from __future__ import annotations

import ast
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "run_phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1.py"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1"
)


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_joint_rule_script_uses_hardcoded_repo_configuration() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "argparse" not in imported_modules


def test_joint_rule_manifest_is_report_only() -> None:
    manifest = json.loads((OUTPUT_DIR / "anchor_joint_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "anchor_joint_rule_sweep_complete"
    assert manifest["input_pairwise_rows"] == 2_284
    assert manifest["unique_semantic_pairs"] == 590
    assert manifest["rule_rows"] == 14
    assert manifest["conflict_rows"] == 48
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False
    assert manifest["report_only"] is True


def test_joint_rule_headline_rows_are_stable() -> None:
    rows = read_csv("anchor_joint_rule_summary_rows.csv")
    by_rule = {row["rule_name"]: row for row in rows}

    margin30 = by_rule["hd0_len10_m30"]
    assert margin30["covered_pair_count"] == "162"
    assert margin30["agree_count"] == "161"
    assert margin30["break_count"] == "1"
    assert margin30["break_rate"] == "0.006173"

    margin50 = by_rule["hd0_len10_m50"]
    assert margin50["covered_pair_count"] == "87"
    assert margin50["agree_count"] == "87"
    assert margin50["break_count"] == "0"
    assert margin50["break_rate"] == "0.000000"

    confirmed = by_rule["hd0_len10_m20__hd_le1_len12_agree_required"]
    assert confirmed["covered_pair_count"] == "147"
    assert confirmed["agree_count"] == "146"
    assert confirmed["break_count"] == "1"
    assert confirmed["break_rate"] == "0.006803"


def test_joint_conflict_table_shows_secondary_conflicts_are_not_the_main_signal() -> None:
    rows = read_csv("anchor_joint_conflict_rows.csv")
    target = next(
        row
        for row in rows
        if row["primary_margin_threshold"] == "20.000000"
        and row["secondary_lens"] == "hd0_len8"
        and row["secondary_margin_threshold"] == "0.000000"
    )

    assert target["primary_pairs"] == "251"
    assert target["secondary_available"] == "251"
    assert target["secondary_conflicts_with_primary"] == "9"
    assert target["break_rate_when_secondary_conflicts"] == "0.000000"
