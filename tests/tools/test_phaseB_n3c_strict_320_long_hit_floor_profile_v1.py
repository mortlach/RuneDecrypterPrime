from __future__ import annotations

import ast
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "run_phaseB_failed_decryption_n3c_strict_320_long_hit_floor_profile_v1.py"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "phaseB_failed_decryption_n3c_strict_320_long_hit_floor_profile_v1"
)


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_long_hit_floor_runner_uses_hardcoded_repo_configuration() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "argparse" not in imported_modules


def test_long_hit_floor_manifest_is_report_only_and_full_strict_320() -> None:
    manifest = json.loads((OUTPUT_DIR / "anchor_lens_manifest.json").read_text(encoding="utf-8"))

    assert manifest["hit_rows"] == 6_415_767
    assert manifest["candidate_groups"] == 320
    assert manifest["pair_rows"] == 590
    assert len(manifest["input_files"]) == 20
    assert manifest["report_only"] is True
    assert manifest["require_fwd_only"] is True
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False


def test_long_hit_floor_margin_headlines_are_stable() -> None:
    rows = read_csv("anchor_lens_margin_threshold_rows.csv")
    by_key = {(row["lens_name"], row["margin"]): row for row in rows}

    hd0_l10_m5 = by_key[("HD0_L10_nonoverlap_basic", "5.0")]
    assert hd0_l10_m5["covered"] == "590"
    assert hd0_l10_m5["agree"] == "355"
    assert hd0_l10_m5["break"] == "25"
    assert hd0_l10_m5["tie"] == "210"

    hd0_l12_m0 = by_key[("HD0_L12_nonoverlap_basic", "0.0")]
    assert hd0_l12_m0["covered"] == "590"
    assert hd0_l12_m0["agree"] == "573"
    assert hd0_l12_m0["break"] == "17"
    assert hd0_l12_m0["tie"] == "0"

    hd0_l12_m5 = by_key[("HD0_L12_nonoverlap_basic", "5.0")]
    assert hd0_l12_m5["agree"] == "130"
    assert hd0_l12_m5["break"] == "0"
    assert hd0_l12_m5["tie"] == "460"
