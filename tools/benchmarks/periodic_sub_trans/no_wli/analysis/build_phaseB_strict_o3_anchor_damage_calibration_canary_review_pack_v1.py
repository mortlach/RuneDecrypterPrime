from __future__ import annotations

import csv
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


PACK_NAME = "phaseB_strict_o3_anchor_damage_calibration_canary_v2_fix_review_pack_2026-06-07"
PACK_ROOT = REPO_ROOT / "planning/projects/no_wli/40_review_summaries" / PACK_NAME
ZIP_PATH = PACK_ROOT.with_suffix(".zip")
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"

OUTPUTS = {
    "strict_320": ANALYSIS_ROOT / "phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1",
    "anchor_quickcheck": ANALYSIS_ROOT / "phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1",
    "joint_sweep": ANALYSIS_ROOT / "phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1",
    "long_hit_floor": ANALYSIS_ROOT / "phaseB_failed_decryption_n3c_strict_320_long_hit_floor_profile_v1",
    "known_damage_canary": ANALYSIS_ROOT / "phaseB_strict_o3_anchor_known_damage_calibration_canary_v2_fix",
}

SOURCE_FILES = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/strict_o3_anchor_reference_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/damage_models_reference_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/damage_models_reference_v2.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/summary_grouping_reference_v2.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/runtime_projection_reference_v2.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_long_hit_floor_profile_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_strict_o3_anchor_known_damage_calibration_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_strict_o3_anchor_known_damage_calibration_canary_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/launch_phaseB_strict_o3_anchor_known_damage_calibration_canary_visible_v1.ps1",
)

TEST_FILES = (
    "tests/tools/test_phaseB_n3c_strict_320_anchor_lens_quickcheck_v1.py",
    "tests/tools/test_phaseB_n3c_strict_320_anchor_joint_rule_sweep_v1.py",
    "tests/tools/test_phaseB_n3c_strict_320_long_hit_floor_profile_v1.py",
    "tests/tools/test_phaseB_strict_o3_anchor_known_damage_calibration_canary_v1.py",
    "tests/tools/test_phaseB_strict_o3_damage_models_reference_v2.py",
    "tests/tools/test_phaseB_strict_o3_summary_grouping_reference_v2.py",
    "tests/tools/test_phaseB_strict_o3_runtime_projection_reference_v2.py",
)

DESIGN_DIR = REPO_ROOT / "planning/projects/no_wli/35_design/strict_o3_anchor_damage_calibration_dev_pack_v1"


def copy_file(src: Path, rel_dest: str) -> None:
    dest = PACK_ROOT / rel_dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(rel_dest: str, text: str) -> None:
    dest = PACK_ROOT / rel_dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


def copy_output_dir(label: str, files: tuple[str, ...]) -> None:
    src_dir = OUTPUTS[label]
    for name in files:
        copy_file(src_dir / name, f"30_outputs/{label}/{name}")


def build_start_here() -> str:
    canary_manifest = json.loads((OUTPUTS["known_damage_canary"] / "known_damage_calibration_manifest.json").read_text())
    long_rows = read_csv(OUTPUTS["long_hit_floor"] / "anchor_lens_margin_threshold_rows.csv")
    canary_groups = read_csv(OUTPUTS["known_damage_canary"] / "known_damage_vs_null_summary_rows.csv")

    def find_long(lens: str, margin: str) -> dict[str, str]:
        return next(row for row in long_rows if row["lens_name"] == lens and row["margin"] == margin)

    def find_group(lens: str, source: str, model: str, level: str = "") -> dict[str, str]:
        return next(
            row
            for row in canary_groups
            if row["lens_name"] == lens
            and row["source_kind"] == source
            and row["model_name"] == model
            and row["requested_damage_level"] == level
        )

    hd0_l10_m10 = find_long("HD0_L10_nonoverlap_basic", "10.0")
    hd0_l12_m5 = find_long("HD0_L12_nonoverlap_basic", "5.0")
    clean = find_group("HD0_L10", "clean", "none")
    uniform = find_group("HD0_L10", "ordinary_null", "uniform_random")
    block50 = find_group("HD0_L10", "hard_local_order_control", "block_shuffle_50")
    independent_030 = find_group("HD0_L10", "damaged", "independent_substitution", "0.30")
    independent_050 = find_group("HD0_L10", "damaged", "independent_substitution", "0.50")
    return (
        "# Strict O3 Anchor Damage Calibration Canary v2-fix Review Pack\n\n"
        "This pack collates the strict-320 anchor evidence, the long-hit floor profile, "
        "and the first known-damage/null calibration canary. Full strict hit CSV payloads "
        "are not embedded; manifests include paths, row counts, byte counts, and hashes.\n\n"
        "## Canary Scope\n\n"
        f"- clean FWD chunks: `{canary_manifest['clean_chunk_count']}`\n"
        f"- generated samples: `{canary_manifest['sample_count']}`\n"
        f"- samples per clean chunk: `{canary_manifest['samples_per_clean_chunk']}`\n"
        f"- runtime chunks completed: `{canary_manifest['completed_runtime_chunk_count']}` / "
        f"`{canary_manifest['runtime_chunk_count']}`\n"
        f"- hits: `{canary_manifest['hit_count']}`\n"
        f"- elapsed seconds: `{canary_manifest['elapsed_seconds']}`\n"
        f"- peak memory MB: `{canary_manifest['peak_memory_mb']}`\n\n"
        "## Canary Contract Fixes\n\n"
        f"- damage generation contract: `{canary_manifest['damage_generation_contract']}`\n"
        f"- structured damage shape contract: `{canary_manifest['structured_damage_shape_contract']}`\n"
        f"- damage tolerance: `{canary_manifest['damage_tolerance']}`\n"
        f"- legacy nominal damage models used for damaged samples: "
        f"`{not canary_manifest['legacy_nominal_damage_models_not_used_for_damaged_samples']}`\n"
        f"- phrase rarity weighting active: `{canary_manifest['phrase_rarity_weighting_active']}`\n\n"
        "## Long-Hit Floor Highlights\n\n"
        f"- `HD0_L10_nonoverlap_basic` margin 10: agree `{hd0_l10_m10['agree']}`, "
        f"break `{hd0_l10_m10['break']}`, tie `{hd0_l10_m10['tie']}`\n"
        f"- `HD0_L12_nonoverlap_basic` margin 5: agree `{hd0_l12_m5['agree']}`, "
        f"break `{hd0_l12_m5['break']}`, tie `{hd0_l12_m5['tie']}`\n\n"
        "## Known-Damage Canary Readout\n\n"
        f"- `HD0_L10` clean mean selected weight: `{clean['selected_weight_sum_mean']}`\n"
        f"- `HD0_L10` independent 0.30 mean actual changed fraction: "
        f"`{independent_030['actual_changed_fraction_mean']}`\n"
        f"- `HD0_L10` independent 0.50 mean actual changed fraction: "
        f"`{independent_050['actual_changed_fraction_mean']}`\n"
        f"- `HD0_L10` uniform random mean selected weight: `{uniform['selected_weight_sum_mean']}`\n"
        f"- `HD0_L10` block shuffle 50 mean selected weight: `{block50['selected_weight_sum_mean']}`\n\n"
        "Interpretation: the v2-fix canary proves the end-to-end FWD known-damage pipeline runs "
        "with target-actual damage validation and structured damage-shape preservation. "
        "Uniform/frequency random nulls collapse to zero anchor signal, but block shuffles retain "
        "strong local anchor signal, so larger calibration must treat block-shuffle controls as "
        "hard local-order controls rather than ordinary nulls.\n"
    )


def build_authority_text() -> str:
    return (
        "# Authority And Limits\n\n"
        "This pack is report-only scientific telemetry. It does not approve production scoring, "
        "production ranking, score-bearing use, all-734 expansion, or raw-hit authority.\n\n"
        "The known-damage v2-fix canary has only 2 clean chunks and 38 generated samples. It proves wiring, "
        "runtime, FWD contract, target-actual damage validation, structured damage-shape preservation, and first signal shape. It is not "
        "large enough for final calibration.\n\n"
        "The previous v1 canary/review pack is superseded for calibration decisions because it used "
        "nominal damage calls and collapsed damage levels in grouped summaries.\n"
    )


def build_pack() -> dict[str, object]:
    if PACK_ROOT.exists():
        shutil.rmtree(PACK_ROOT)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    PACK_ROOT.mkdir(parents=True, exist_ok=True)

    write_text("00_start_here.md", build_start_here())
    write_text("02_authority_and_limits.md", build_authority_text())

    for src in SOURCE_FILES:
        copy_file(REPO_ROOT / src, f"50_source/{src}")
    for src in TEST_FILES:
        copy_file(REPO_ROOT / src, f"40_tests/{src}")
    for path in sorted(DESIGN_DIR.glob("*.md")):
        copy_file(path, f"10_design/{path.name}")

    copy_output_dir(
        "strict_320",
        (
            "bucket_summary_rows.csv",
            "candidate_n3c_summary_rows.csv",
            "hit_file_manifest_rows.csv",
            "run_manifest.json",
            "unique_semantic_pairwise_gold_n3c_report_rows.csv",
        ),
    )
    copy_output_dir(
        "anchor_quickcheck",
        (
            "anchor_lens_manifest.json",
            "anchor_lens_margin_threshold_rows.csv",
            "candidate_anchor_summary_rows.csv",
            "candidate_anchor_pairwise_rows.csv",
        ),
    )
    copy_output_dir(
        "joint_sweep",
        (
            "anchor_joint_manifest.json",
            "anchor_joint_rule_summary_rows.csv",
            "anchor_joint_conflict_rows.csv",
        ),
    )
    copy_output_dir(
        "long_hit_floor",
        (
            "anchor_lens_manifest.json",
            "anchor_lens_margin_threshold_rows.csv",
            "candidate_anchor_summary_rows.csv",
            "candidate_anchor_region_rows.csv",
        ),
    )
    copy_output_dir(
        "known_damage_canary",
        (
            "calibration_clean_chunk_rows.csv",
            "calibration_sample_rows.csv",
            "known_damage_anchor_summary_rows.csv",
            "known_damage_anchor_region_rows.csv",
            "known_damage_calibration_canary_v2_fix_2026-06-07.log",
            "known_damage_calibration_manifest.json",
            "known_damage_runtime_chunk_rows.csv",
            "known_damage_runtime_projection_rows.csv",
            "known_damage_vs_null_summary_rows.csv",
        ),
    )

    pack_files = [path for path in PACK_ROOT.rglob("*") if path.is_file()]
    summary = {
        "status": "packed_review_ready",
        "pack_name": PACK_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "entry_count_before_summary": len(pack_files),
        "report_only": True,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "full_hit_csv_payloads_embedded": False,
    }
    write_text("PACK_BUILD_SUMMARY.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_ROOT).as_posix())

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
    final_summary = {
        **summary,
        "entry_count": len(names),
        "zip_path": ZIP_PATH.relative_to(REPO_ROOT).as_posix(),
        "zip_size_note": "Read ZIP byte size from filesystem after pack build; it is not embedded to avoid self-referential drift.",
        "backslash_entry_count": sum(1 for name in names if "\\" in name),
    }
    write_text("PACK_BUILD_SUMMARY.json", json.dumps(final_summary, indent=2, sort_keys=True) + "\n")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_ROOT).as_posix())
    return final_summary


def main() -> int:
    summary = build_pack()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
