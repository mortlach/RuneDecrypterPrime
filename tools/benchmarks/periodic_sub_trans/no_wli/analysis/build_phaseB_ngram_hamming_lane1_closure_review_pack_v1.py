from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_lane1_closure_review_pack_v1"
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_ngram_hamming_lane1_full_raw_language_asset_closure_review_pack_2026-06-01"
)
ZIP_REL = f"{PACK_DIR_REL}.zip"
ASSET_HOME_REL = "assets/ngram_hamming/phaseB_full_raw_v1"
CONTEXT_FILES_REL = (
    "AGENTS.md",
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md",
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md",
)
COMPONENT_FILES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/output_file_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/missing_shard_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/missing_required_output_combo_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/phrase_length_distribution_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/word_length_distribution_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_checklist.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/normal_strict_row_counts.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/README.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_language_asset_validation_v1/validation_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json",
)
SOURCE_FILES_REL = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_language_asset_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_full_raw_language_asset_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_lane1_closure_review_pack_v1.py",
)
TEST_FILES_REL = (
    "tests/tools/test_phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_language_asset_pack_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_language_asset_validation_v1.py",
)
ASSET_INDEX_FILES_REL = (
    f"{ASSET_HOME_REL}/asset_manifest.json",
    f"{ASSET_HOME_REL}/README.md",
    f"{ASSET_HOME_REL}/provenance/shard_provenance_manifest.json",
    f"{ASSET_HOME_REL}/provenance/shard_rows.csv",
    f"{ASSET_HOME_REL}/provenance/output_file_rows.csv",
    f"{ASSET_HOME_REL}/provenance/missing_shard_rows.csv",
    f"{ASSET_HOME_REL}/provenance/missing_required_output_combo_rows.csv",
    f"{ASSET_HOME_REL}/provenance/phrase_length_distribution_rows.csv",
    f"{ASSET_HOME_REL}/provenance/word_length_distribution_rows.csv",
)


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_data_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _row in reader)


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


def write_review_summary(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Lane 1 Full Raw Language Asset Closure Review Summary",
        "",
        f"- status: `{manifest['status']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- phrase length distribution rows: `{manifest['phrase_length_distribution_rows']}`",
        f"- word length distribution rows: `{manifest['word_length_distribution_rows']}`",
        f"- provenance review pack status: `{manifest['provenance_review_pack_status']}`",
        f"- asset validation status: `{manifest['asset_validation_status']}`",
        f"- Lane 2 launch decision status: `{manifest['lane2_launch_decision_status']}`",
        f"- real bridge scan started: `{manifest['real_bridge_scan_started']}`",
        f"- production scorer change: `{manifest['production_scorer_change']}`",
        "",
        "This is a Lane 1 closure pack only. It does not approve a Lane 2 real",
        "bridge scan and does not approve a production scorer change.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_questions(path: Path) -> None:
    ensure_under_repo(path)
    lines = [
        "# Lane 1 Closure Review Questions",
        "",
        "1. Is the permanent asset manifest sufficient to replay or verify the full raw order-2/order-3 payload from retained outputs?",
        "2. Are phrase and word length distributions adequate provenance evidence for this Lane 1 tranche?",
        "3. Are the normal and strict cuts kept separate throughout the asset contract?",
        "4. Does the pack avoid implying Lane 2 or production scoring authority?",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def component_no_production_change(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    if "no_production_scorer_changes" in payload:
        return payload.get("no_production_scorer_changes") is True
    if "no_production_scorer_change" in payload:
        return payload.get("no_production_scorer_change") is True
    return True


def component_no_real_scan(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    if payload.get("real_candidate_scan_started") is True:
        return False
    if payload.get("no_broad_scan_launched") is False:
        return False
    return True


def build_lane1_closure_review_pack(
    pack_dir: Path | None = None,
    zip_path: Path | None = None,
) -> dict[str, Any]:
    selected_pack_dir = pack_dir or (REPO_ROOT / PACK_DIR_REL)
    selected_zip_path = zip_path or (REPO_ROOT / ZIP_REL)
    reset_pack_dir(selected_pack_dir)
    copied: list[dict[str, Any]] = []
    for rel_path in CONTEXT_FILES_REL:
        copied.append(copy_file(rel_path, selected_pack_dir, "10_context"))
    for rel_path in COMPONENT_FILES_REL:
        copied.append(copy_file(rel_path, selected_pack_dir, "20_component_outputs"))
    for rel_path in SOURCE_FILES_REL:
        copied.append(copy_file(rel_path, selected_pack_dir, "30_source"))
    for rel_path in TEST_FILES_REL:
        copied.append(copy_file(rel_path, selected_pack_dir, "40_tests"))
    for rel_path in ASSET_INDEX_FILES_REL:
        copied.append(copy_file(rel_path, selected_pack_dir, "50_asset_index"))

    provenance = read_json_if_exists(REPO_ROOT / COMPONENT_FILES_REL[0])
    review = read_json_if_exists(
        REPO_ROOT
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json"
    )
    validation = read_json_if_exists(
        REPO_ROOT
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_language_asset_validation_v1/validation_manifest.json"
    )
    launch = read_json_if_exists(
        REPO_ROOT
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json"
    )
    gated = read_json_if_exists(
        REPO_ROOT
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json"
    )
    readiness = read_json_if_exists(
        REPO_ROOT
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json"
    )
    asset = read_json_if_exists(REPO_ROOT / f"{ASSET_HOME_REL}/asset_manifest.json")
    component_payloads = {
        "provenance_review_pack": review,
        "asset_manifest": asset,
        "asset_validation": validation,
        "readiness": readiness,
        "launch_decision": launch,
        "gated_diagnostic": gated,
    }
    missing_files = [row["source_path"] for row in copied if not row["exists"]]
    no_production_component_status = {
        name: component_no_production_change(payload)
        for name, payload in component_payloads.items()
    }
    no_real_scan_component_status = {
        name: component_no_real_scan(payload)
        for name, payload in component_payloads.items()
    }
    no_production_state = all(no_production_component_status.values())
    no_real_scan_state = all(no_real_scan_component_status.values())
    lane1_ready = (
        provenance.get("status") == "pass"
        and review.get("status") == "review_ready"
        and validation.get("status") == "pass"
        and not missing_files
        and no_production_state
        and no_real_scan_state
        and launch.get("status") == "blocked"
    )
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "packed_review_ready" if lane1_ready else "packed_with_blocks",
        "pack_dir": repo_rel(selected_pack_dir),
        "zip_path": repo_rel(selected_zip_path),
        "missing_files": missing_files,
        "copied_files": copied,
        "completed_shards": provenance.get("completed_shards", 0),
        "total_shards": provenance.get("total_shards", 0),
        "missing_shards": provenance.get("missing_shards", 0),
        "failed_shards": provenance.get("failed_shards", 0),
        "missing_output_files": provenance.get("missing_output_files", 0),
        "missing_required_output_combos": provenance.get("missing_required_output_combos", 0),
        "phrase_length_distribution_rows": csv_data_row_count(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/phrase_length_distribution_rows.csv"
        ),
        "word_length_distribution_rows": csv_data_row_count(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/word_length_distribution_rows.csv"
        ),
        "provenance_review_pack_status": review.get("status", ""),
        "pending_review_checks": review.get("pending_review_checks", []),
        "asset_validation_status": validation.get("status", ""),
        "asset_validation_blocked_reasons": validation.get("blocked_reasons", []),
        "lane2_launch_decision_status": launch.get("status", ""),
        "real_bridge_scan_started": gated.get("real_candidate_scan_started", True),
        "production_scorer_change": not no_production_state,
        "no_production_component_status": no_production_component_status,
        "no_real_scan_component_status": no_real_scan_component_status,
        "no_production_state": no_production_state,
        "no_real_scan_state": no_real_scan_state,
    }
    write_review_summary(selected_pack_dir / "10_context" / "review_summary.md", manifest)
    write_questions(selected_pack_dir / "10_context" / "review_questions.md")
    write_json(selected_pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = make_zip(selected_pack_dir, selected_zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    manifest["status"] = (
        "packed_review_ready"
        if lane1_ready and backslash_entries == 0
        else "packed_with_blocks"
    )
    write_json(selected_pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = make_zip(selected_pack_dir, selected_zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] entry_count={manifest['entry_count']}")
    return manifest


def main() -> None:
    build_lane1_closure_review_pack()


if __name__ == "__main__":
    main()
