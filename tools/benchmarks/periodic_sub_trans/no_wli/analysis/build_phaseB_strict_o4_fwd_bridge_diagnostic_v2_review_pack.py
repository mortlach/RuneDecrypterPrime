from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_strict_o4_fwd_bridge_diagnostic_v2_review_pack"
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_strict_o4_fwd_bridge_diagnostic_v2_review_pack_2026-06-07"
)
ZIP_REL = f"{PACK_DIR_REL}.zip"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_strict_o4_fwd_nose_bridge_damage_ladder_canary_v2"
)

CONTEXT_FILES_REL = (
    "AGENTS.md",
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/10_full_logs/no_wli_science_run_log_2026-03-26.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_order4_fwd_nose_asset_shards_plan_2026-06-01.md",
    "planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_order4_fwd_nose_runtime_review_pack_2026-06-07/PACK_BUILD_SUMMARY.json",
)
OUTPUT_FILES_REL = (
    f"{OUTPUT_DIR_REL}/run_manifest.json",
    f"{OUTPUT_DIR_REL}/run_state.json",
    f"{OUTPUT_DIR_REL}/progress_rows.csv",
    f"{OUTPUT_DIR_REL}/sample_rows.csv",
    f"{OUTPUT_DIR_REL}/sample_o4_summary_rows.csv",
    f"{OUTPUT_DIR_REL}/failed_sample_rows.csv",
    f"{OUTPUT_DIR_REL}/incomplete_sample_rows.csv",
    f"{OUTPUT_DIR_REL}/final_summary.json",
    f"{OUTPUT_DIR_REL}/readout.md",
    "planning/projects/no_wli/50_console_and_watch_logs/phaseB_strict_o4_fwd_nose_bridge_damage_ladder_canary_v2_2026-06-07.log",
)
RUNTIME_AUTHORITY_FILES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_v1/runtime_index_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_validation_v1/validation_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_fwd_nose_compact_phrase_lookup_asset_v1/compact_asset_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_fwd_nose_compact_phrase_lookup_asset_validation_v1/validation_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_v1/invalid_compact_row_rows.csv",
)
SOURCE_FILES_REL = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_strict_o4_fwd_bridge_reference_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_target_actual_damage_models_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_strict_o4_fwd_nose_bridge_damage_ladder_canary_v2.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_strict_o4_fwd_bridge_diagnostic_v2_review_pack.py",
)
TEST_FILES_REL = (
    "tests/tools/test_phaseB_strict_o4_fwd_bridge_reference_v1.py",
)
LAUNCH_FILES_REL = (
    "planning/projects/no_wli/60_launch_scripts/phaseB_strict_o4_fwd_nose_bridge_damage_ladder_canary_v2_launch_2026-06-07.ps1",
)


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reset_pack_dir(pack_dir: Path) -> None:
    resolved = pack_dir.resolve()
    expected_parent = (REPO_ROOT / "planning/projects/no_wli/40_review_summaries").resolve()
    resolved.relative_to(expected_parent)
    if resolved.exists():
        shutil.rmtree(resolved)


def copy_file(source_rel: str, pack_root: Path, section: str) -> dict[str, Any]:
    source = REPO_ROOT / source_rel
    row = {"source_path": source_rel, "exists": source.exists(), "pack_path": ""}
    if not source.exists():
        return row
    destination = pack_root / section / source_rel
    ensure_under_repo(destination)
    shutil.copy2(source, destination)
    row["pack_path"] = repo_rel(destination)
    return row


def copy_glob(source_dir_rel: str, pattern: str, pack_root: Path, section: str) -> list[dict[str, Any]]:
    source_dir = REPO_ROOT / source_dir_rel
    copied: list[dict[str, Any]] = []
    for source in sorted(source_dir.glob(pattern)):
        if not source.is_file():
            continue
        source_rel = repo_rel(source)
        destination = pack_root / section / source_rel
        ensure_under_repo(destination)
        shutil.copy2(source, destination)
        copied.append({"source_path": source_rel, "exists": True, "pack_path": repo_rel(destination)})
    return copied


def make_zip(pack_dir: Path, zip_path: Path) -> tuple[int, int]:
    ensure_under_repo(zip_path)
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in sorted(path for path in pack_dir.rglob("*") if path.is_file()):
            archive.write(file_path, file_path.relative_to(pack_dir.parent).as_posix())
    with ZipFile(zip_path, mode="r") as archive:
        names = archive.namelist()
    return len(names), sum(1 for name in names if "\\" in name)


def sum_int(rows: Iterable[Mapping[str, str]], field: str) -> int:
    total = 0
    for row in rows:
        text = str(row.get(field, "")).strip()
        if text:
            total += int(float(text))
    return total


def hit_part_ids(output_dir: Path) -> set[str]:
    parts_dir = output_dir / "sample_o4_hit_parts"
    if not parts_dir.exists():
        return set()
    ids: set[str] = set()
    for part in parts_dir.glob("*.csv"):
        rows = csv_rows(part)
        if rows:
            ids.update(row.get("sample_id", "") for row in rows if row.get("sample_id"))
        else:
            # Zero-hit samples still have a part file and are represented by summary rows.
            continue
    return ids


def write_review_summary(path: Path, manifest: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Strict O4 FWD Bridge Diagnostic v2 Review Pack",
        "",
        f"- status: `{manifest['status']}`",
        f"- run mode: `{manifest['run_mode']}`",
        f"- final status: `{manifest['final_status']}`",
        f"- report only: `{manifest['report_only']}`",
        f"- production scorer change: `{manifest['production_scorer_change']}`",
        f"- direction/order/cut: `{manifest['direction']} / {manifest['order']} / {manifest['cut']}`",
        f"- completed samples: `{manifest['completed_samples_total']}`",
        f"- total samples estimate: `{manifest['total_samples_estimate']}`",
        f"- failed samples: `{manifest['failed_sample_rows']}`",
        f"- incomplete samples: `{manifest['incomplete_sample_rows']}`",
        f"- summary rows: `{manifest['summary_rows']}`",
        f"- sample rows: `{manifest['sample_rows']}`",
        f"- hit part files: `{manifest['hit_part_files']}`",
        f"- hit rows: `{manifest['hit_rows']}`",
        f"- progress rows: `{manifest['progress_rows']}`",
        f"- runtime groups selected: `{manifest['runtime_groups_selected']}`",
        f"- zip entries: `{manifest.get('entry_count', 'pending')}`",
        f"- zip backslash entries: `{manifest.get('backslash_entries', 'pending')}`",
        "",
        "Gate: this is a bounded report-only diagnostic pack. It does not approve",
        "production scorer changes or an ungated broad bridge scan.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_review_pack() -> dict[str, Any]:
    pack_dir = REPO_ROOT / PACK_DIR_REL
    zip_path = REPO_ROOT / ZIP_REL
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    reset_pack_dir(pack_dir)

    copied: list[dict[str, Any]] = []
    for section, files in (
        ("10_context", CONTEXT_FILES_REL),
        ("20_outputs", OUTPUT_FILES_REL),
        ("30_runtime_authority", RUNTIME_AUTHORITY_FILES_REL),
        ("40_source", SOURCE_FILES_REL),
        ("50_tests", TEST_FILES_REL),
        ("60_launch_scripts", LAUNCH_FILES_REL),
    ):
        for rel_path in files:
            copied.append(copy_file(rel_path, pack_dir, section))
    copied.extend(copy_glob(f"{OUTPUT_DIR_REL}/sample_o4_hit_parts", "*.csv", pack_dir, "20_outputs"))

    run_manifest = read_json_if_exists(output_dir / "run_manifest.json")
    final_summary = read_json_if_exists(output_dir / "final_summary.json")
    run_state = read_json_if_exists(output_dir / "run_state.json")
    sample_rows = csv_rows(output_dir / "sample_rows.csv")
    summary_rows = csv_rows(output_dir / "sample_o4_summary_rows.csv")
    failed_rows = csv_rows(output_dir / "failed_sample_rows.csv")
    incomplete_rows = csv_rows(output_dir / "incomplete_sample_rows.csv")
    progress_rows = csv_rows(output_dir / "progress_rows.csv")
    parts_dir = output_dir / "sample_o4_hit_parts"
    hit_parts = sorted(parts_dir.glob("*.csv")) if parts_dir.exists() else []
    hit_rows = sum(len(csv_rows(path)) for path in hit_parts)
    summary_hit_parts = {row.get("hit_part_path", "") for row in summary_rows if row.get("hit_part_path")}
    existing_hit_parts = {repo_rel(path) for path in hit_parts}
    summary_group_counts = {row.get("groups_loaded", "") for row in summary_rows if row.get("groups_loaded", "")}
    summary_config_hashes = {row.get("config_hash", "") for row in summary_rows if row.get("sample_id")}
    sample_config_hashes = {row.get("config_hash", "") for row in sample_rows if row.get("sample_id")}
    expected_config_hash = str(final_summary.get("config_hash", ""))

    missing_files = [row["source_path"] for row in copied if not row["exists"]]
    blockers: list[str] = []
    if final_summary.get("status") != "complete":
        blockers.append("final summary is not complete")
    if final_summary.get("run_mode") != "overnight_5_clean_chunks":
        blockers.append("run mode is not overnight_5_clean_chunks")
    if final_summary.get("report_only") is not True:
        blockers.append("report_only is not true")
    if final_summary.get("production_scorer_change") is not False:
        blockers.append("production_scorer_change is not false")
    if (final_summary.get("direction"), int(final_summary.get("order", -1)), final_summary.get("cut")) != ("fwd", 4, "strict"):
        blockers.append("direction/order/cut contract is not fwd/4/strict")
    if int(final_summary.get("completed_samples_total", -1)) != len(summary_rows):
        blockers.append("completed sample total does not match summary rows")
    if int(final_summary.get("total_samples_estimate", -1)) != len(summary_rows):
        blockers.append("summary rows do not match total sample estimate")
    if len(summary_group_counts) != 1:
        blockers.append("summary rows contain mixed groups_loaded values")
    elif summary_group_counts and int(next(iter(summary_group_counts))) != int(final_summary.get("runtime_groups_selected", -1)):
        blockers.append("summary groups_loaded does not match runtime_groups_selected")
    if not expected_config_hash:
        blockers.append("final summary has no config_hash")
    if summary_config_hashes != {expected_config_hash}:
        blockers.append("summary rows do not all match final config_hash")
    if sample_config_hashes != {expected_config_hash}:
        blockers.append("sample rows do not all match final config_hash")
    if failed_rows:
        blockers.append("failed sample rows are present")
    if incomplete_rows:
        blockers.append("incomplete sample rows are present")
    if summary_hit_parts != existing_hit_parts:
        blockers.append("summary hit part paths do not match hit part files")
    if missing_files:
        blockers.append("listed files are missing")

    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_ready" if not blockers else "packed_with_blocks",
        "blockers": blockers,
        "run_mode": final_summary.get("run_mode", ""),
        "final_status": final_summary.get("status", ""),
        "run_state_status": run_state.get("status", ""),
        "report_only": final_summary.get("report_only", ""),
        "production_scorer_change": final_summary.get("production_scorer_change", ""),
        "real_bridge_scan": False,
        "direction": final_summary.get("direction", ""),
        "order": final_summary.get("order", ""),
        "cut": final_summary.get("cut", ""),
        "runtime_groups_selected": final_summary.get("runtime_groups_selected", 0),
        "completed_samples_total": final_summary.get("completed_samples_total", 0),
        "total_samples_estimate": final_summary.get("total_samples_estimate", 0),
        "sample_rows": len(sample_rows),
        "summary_rows": len(summary_rows),
        "failed_sample_rows": len(failed_rows),
        "incomplete_sample_rows": len(incomplete_rows),
        "progress_rows": len(progress_rows),
        "hit_part_files": len(hit_parts),
        "hit_rows": hit_rows,
        "groups_loaded_values": sorted(summary_group_counts),
        "summary_config_hashes": sorted(summary_config_hashes),
        "sample_config_hashes": sorted(sample_config_hashes),
        "config_hash": expected_config_hash,
        "summary_hit_row_sum": sum_int(summary_rows, "hit_count"),
        "exact_hit_row_sum": sum_int(summary_rows, "exact_hit_count"),
        "hit_rows_written_this_process": final_summary.get("hit_rows_written_this_process", 0),
        "samples_committed_this_process": final_summary.get("samples_committed_this_process", 0),
        "samples_skipped_this_process": final_summary.get("samples_skipped_this_process", 0),
        "samples_failed_this_process": final_summary.get("samples_failed_this_process", 0),
        "copied_files": copied,
        "missing_files": missing_files,
        "runtime_manifest": run_manifest.get("runtime_manifest", final_summary.get("runtime_manifest", "")),
        "zip_path": ZIP_REL,
        "notes": [
            "Strict O4 FWD runtime bridge diagnostic remains report-only.",
            "O4 runtime authority accepted for bounded diagnostics only.",
            "No production scorer change.",
            "No ungated broad bridge scan.",
        ],
    }
    write_json(pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    write_review_summary(pack_dir / "README.md", manifest)
    entry_count, backslash_entries = make_zip(pack_dir, zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    write_json(pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    write_review_summary(pack_dir / "README.md", manifest)
    make_zip(pack_dir, zip_path)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] zip={ZIP_REL}")
    print(f"[{RUN_LABEL}] blockers={len(blockers)}")
    return manifest


def main() -> None:
    build_review_pack()


if __name__ == "__main__":
    main()
