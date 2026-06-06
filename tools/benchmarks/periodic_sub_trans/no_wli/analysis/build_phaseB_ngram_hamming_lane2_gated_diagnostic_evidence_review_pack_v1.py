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


RUN_LABEL = "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1"
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_selection_fixed_review_pack_2026-06-03"
)
ZIP_REL = f"{PACK_DIR_REL}.zip"
MAX_ZIP_BYTES = 50_000_000
DEVELOPER_TEST_RESULT = "92 passed with optional fast extension available"
PORTABLE_TEST_RESULT = "77 passed, 15 skipped when optional fast extension is not built"
EVIDENCE_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1"
)
ASSET_HOME_REL = "assets/ngram_hamming/phaseB_full_raw_v1"
COMPACT_ASSET_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1"
)
COMPACT_VALIDATION_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1"
)
RUNTIME_INDEX_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_fast_runtime_lookup_index_v1"
)
RUNTIME_VALIDATION_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1"
)
CONTEXT_FILES_REL = (
    "AGENTS.md",
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md",
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_plan_2026-06-01.md",
)
COMPONENT_FILES_REL = (
    f"{EVIDENCE_DIR_REL}/corpus_manifest.json",
    f"{EVIDENCE_DIR_REL}/run_manifest.json",
    f"{EVIDENCE_DIR_REL}/profile_manifest_rows.csv",
    f"{EVIDENCE_DIR_REL}/selection_manifest.json",
    f"{EVIDENCE_DIR_REL}/selection_manifest_rows.csv",
    f"{EVIDENCE_DIR_REL}/candidate_profile_summary_rows.csv",
    f"{EVIDENCE_DIR_REL}/candidate_cluster_summary_rows.csv",
    f"{EVIDENCE_DIR_REL}/sampled_hit_rows.csv",
    f"{EVIDENCE_DIR_REL}/full_hit_rows.csv",
    f"{EVIDENCE_DIR_REL}/null_comparison_rows.csv",
    f"{EVIDENCE_DIR_REL}/concentration_rows.csv",
    f"{EVIDENCE_DIR_REL}/damage_tier_summary_rows.csv",
    f"{EVIDENCE_DIR_REL}/scan_diagnostic_rows.csv",
    f"{EVIDENCE_DIR_REL}/positive_passages.jsonl",
    f"{EVIDENCE_DIR_REL}/positive_cases.jsonl",
    f"{EVIDENCE_DIR_REL}/boundary_cases.jsonl",
    f"{EVIDENCE_DIR_REL}/diagnostic_cases.jsonl",
    f"{EVIDENCE_DIR_REL}/selected_phrase_entries.jsonl",
    f"{EVIDENCE_DIR_REL}/null_passages.jsonl",
    f"{EVIDENCE_DIR_REL}/damaged_cases.jsonl",
    f"{EVIDENCE_DIR_REL}/review_readout.md",
)
SOURCE_FILES_REL = (
    "pyproject.toml",
    "pytest.ini",
    "README.md",
    "src/rune_decrypter_prime/__init__.py",
    "src/rune_decrypter_prime/scoring/__init__.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/reference.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/fast_bindings.cpp",
    "src/rune_decrypter_prime/scoring/ngram_hamming/FastNgramHamming.h",
    "src/rune_decrypter_prime/scoring/ngram_hamming/setup_ngram_hamming_fast.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_fast_runtime_lookup_index_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_fast_runtime_lookup_index_v1.py",
)
TEST_FILES_REL = (
    "tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py",
    "tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py",
    "tests/scoring/ngram_hamming/test_reference_ngram_hamming.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_fast_runtime_lookup_index_v1.py",
)
ASSET_INDEX_FILES_REL = (
    f"{ASSET_HOME_REL}/asset_manifest.json",
    f"{ASSET_HOME_REL}/README.md",
    f"{ASSET_HOME_REL}/provenance/shard_provenance_manifest.json",
    f"{ASSET_HOME_REL}/provenance/output_file_rows.csv",
    f"{ASSET_HOME_REL}/provenance/phrase_length_distribution_rows.csv",
    f"{ASSET_HOME_REL}/provenance/word_length_distribution_rows.csv",
    f"{COMPACT_ASSET_DIR_REL}/compact_asset_manifest.json",
    f"{COMPACT_ASSET_DIR_REL}/readout.md",
    f"{COMPACT_VALIDATION_DIR_REL}/validation_manifest.json",
    f"{COMPACT_VALIDATION_DIR_REL}/validation_failure_rows.csv",
    f"{COMPACT_VALIDATION_DIR_REL}/readout.md",
    f"{RUNTIME_INDEX_DIR_REL}/runtime_index_manifest.json",
    f"{RUNTIME_INDEX_DIR_REL}/readout.md",
    f"{RUNTIME_VALIDATION_DIR_REL}/validation_manifest.json",
    f"{RUNTIME_VALIDATION_DIR_REL}/validation_failure_rows.csv",
    f"{RUNTIME_VALIDATION_DIR_REL}/readout.md",
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


def write_review_summary(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Lane 2 Gated Diagnostic Evidence Review Summary",
        "",
        f"- status: `{manifest['status']}`",
        f"- phase: `{manifest['phase']}`",
        f"- run authority: `{manifest['run_authority']}`",
        f"- controlled eval corpus scan started: `{manifest['controlled_eval_corpus_scan_started']}`",
        f"- real candidate scan started: `{manifest['real_candidate_scan_started']}`",
        f"- broad candidate scan started: `{manifest['broad_candidate_scan_started']}`",
        f"- production scorer change: `{manifest['production_scorer_change']}`",
        f"- Lane 1 asset id: `{manifest['lane1_asset_id']}`",
        f"- case count: `{manifest['case_count']}`",
        f"- phrase entry count: `{manifest['phrase_entry_count']}`",
        f"- raw hit count: `{manifest['raw_hit_count']}`",
        f"- evidence status: `{manifest['evidence_status']}`",
        f"- selection contract status: `{manifest['selection_contract_status']}`",
        f"- opportunity contract status: `{manifest['opportunity_contract_status']}`",
        f"- compact validation status: `{manifest['compact_validation_status']}`",
        f"- runtime validation status: `{manifest['runtime_validation_status']}`",
        f"- null comparison rows: `{manifest['null_comparison_row_count']}`",
        f"- concentration rows: `{manifest['concentration_row_count']}`",
        f"- missing files: `{len(manifest['missing_files'])}`",
        f"- zip entries: `{manifest.get('entry_count', 'pending')}`",
        f"- zip backslash entries: `{manifest.get('backslash_entries', 'pending')}`",
        f"- zip bytes: `{manifest.get('zip_size_bytes', 'pending')}`",
        f"- maximum zip bytes: `{manifest['maximum_zip_bytes']}`",
        f"- developer test result: `{manifest['developer_test_result']}`",
        f"- portable test result: `{manifest['portable_test_result']}`",
        "",
        "This pack is review-ready for controlled diagnostic evidence only. It does",
        "not approve production scoring, report-only integration, order-2 scoring,",
        "or a broad candidate search.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_review_questions(path: Path) -> None:
    ensure_under_repo(path)
    lines = [
        "# Lane 2 Diagnostic Evidence Review Questions",
        "",
        "1. Do damaged positives separate from matched nulls enough to justify report-only scorer integration?",
        "2. Are diagnostic-only and score-candidate-view clusters separated clearly enough?",
        "3. Are order-2 inflation and concentration risks visible rather than hidden?",
        "4. Are normal and strict cuts separated throughout the evidence?",
        "5. Should the next step be report-only integration, revised diagnostics, order-4 build, more evidence, or redesign?",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_data_scope(path: Path) -> None:
    ensure_under_repo(path)
    lines = [
        "# Review Pack Data Scope",
        "",
        "This pack contains the exact bounded Lane 2 diagnostic inputs and complete",
        "diagnostic outputs needed to review the current result:",
        "",
        "- `selected_phrase_entries.jsonl`: all 144 selected runtime phrase entries",
        "- `positive_passages.jsonl`: all controlled positive passages",
        "- `positive_cases.jsonl`: clearer alias for all controlled positive cases",
        "- `null_passages.jsonl`: all matched null and hard-negative passages",
        "- `boundary_cases.jsonl`: all boundary cases",
        "- `diagnostic_cases.jsonl`: complete case population",
        "- `damaged_cases.jsonl`: all deterministically damaged positive cases",
        "- `full_hit_rows.csv`: all 1,576 diagnostic hit rows",
        "- selection, scan, profile, cluster, concentration, null, and damage summaries",
        "- compact/runtime manifests, validation reports, and the retained gate log",
        "",
        "The complete compact CSV/GZip payload and grouped runtime NPZ payload are",
        "intentionally omitted because they total roughly 150 GB. Their manifests,",
        "hashes, validation results, and the exact bounded rows consumed by Lane 2",
        "are included. This keeps the external review pack portable and below the",
        "hard 50,000,000-byte compressed-size limit.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_lane2_gated_diagnostic_evidence_review_pack(
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

    run_manifest = read_json_if_exists(REPO_ROOT / EVIDENCE_DIR_REL / "run_manifest.json")
    corpus_manifest = read_json_if_exists(REPO_ROOT / EVIDENCE_DIR_REL / "corpus_manifest.json")
    compact_validation = read_json_if_exists(REPO_ROOT / COMPACT_VALIDATION_DIR_REL / "validation_manifest.json")
    runtime_validation = read_json_if_exists(REPO_ROOT / RUNTIME_VALIDATION_DIR_REL / "validation_manifest.json")
    missing_files = [row["source_path"] for row in copied if not row["exists"]]
    safe_state = (
        run_manifest.get("production_scorer_change") is False
        and run_manifest.get("real_candidate_scan_started") is False
        and run_manifest.get("broad_candidate_scan_started") is False
        and run_manifest.get("controlled_eval_corpus_scan_started") is True
        and run_manifest.get("run_authority") == "diagnostic_only"
    )
    row_counts = {
        "candidate_profile_summary_rows": csv_data_row_count(REPO_ROOT / EVIDENCE_DIR_REL / "candidate_profile_summary_rows.csv"),
        "candidate_cluster_summary_rows": csv_data_row_count(REPO_ROOT / EVIDENCE_DIR_REL / "candidate_cluster_summary_rows.csv"),
        "null_comparison_rows": csv_data_row_count(REPO_ROOT / EVIDENCE_DIR_REL / "null_comparison_rows.csv"),
        "concentration_rows": csv_data_row_count(REPO_ROOT / EVIDENCE_DIR_REL / "concentration_rows.csv"),
        "damage_tier_summary_rows": csv_data_row_count(REPO_ROOT / EVIDENCE_DIR_REL / "damage_tier_summary_rows.csv"),
    }
    contract_state = (
        run_manifest.get("evidence_status") == "diagnostic_evidence_ready_for_review"
        and run_manifest.get("selection_contract_status") == "pass"
        and run_manifest.get("opportunity_contract_status") == "pass"
        and compact_validation.get("status") == "pass"
        and runtime_validation.get("status") == "pass"
    )
    review_ready = not missing_files and safe_state and contract_state and all(value > 0 for value in row_counts.values())
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "packed_review_ready" if review_ready else "packed_with_blocks",
        "pack_dir": repo_rel(selected_pack_dir),
        "zip_path": repo_rel(selected_zip_path),
        "missing_files": missing_files,
        "copied_files": copied,
        "phase": run_manifest.get("phase", ""),
        "run_authority": run_manifest.get("run_authority", ""),
        "controlled_eval_corpus_scan_started": run_manifest.get("controlled_eval_corpus_scan_started"),
        "real_candidate_scan_started": run_manifest.get("real_candidate_scan_started"),
        "broad_candidate_scan_started": run_manifest.get("broad_candidate_scan_started"),
        "production_scorer_change": run_manifest.get("production_scorer_change"),
        "lane1_asset_id": run_manifest.get("lane1_asset_id", ""),
        "case_count": corpus_manifest.get("case_count", 0),
        "case_families": corpus_manifest.get("case_families", []),
        "phrase_entry_count": run_manifest.get("phrase_entry_count", 0),
        "raw_hit_count": run_manifest.get("raw_hit_count", 0),
        "evidence_status": run_manifest.get("evidence_status", ""),
        "selection_contract_status": run_manifest.get("selection_contract_status", ""),
        "opportunity_contract_status": run_manifest.get("opportunity_contract_status", ""),
        "compact_validation_status": compact_validation.get("status", ""),
        "runtime_validation_status": runtime_validation.get("status", ""),
        "row_counts": row_counts,
        "null_comparison_row_count": row_counts["null_comparison_rows"],
        "concentration_row_count": row_counts["concentration_rows"],
        "safe_state": safe_state,
        "contract_state": contract_state,
        "maximum_zip_bytes": MAX_ZIP_BYTES,
        "developer_test_result": DEVELOPER_TEST_RESULT,
        "portable_test_result": PORTABLE_TEST_RESULT,
        "review_position": "controlled diagnostic evidence review; do not approve production scoring or broad candidate scans from this pack",
    }
    write_review_summary(selected_pack_dir / "10_context" / "review_summary.md", manifest)
    write_data_scope(selected_pack_dir / "10_context" / "data_scope.md")
    write_review_questions(selected_pack_dir / "50_review_questions" / "review_questions.md")
    write_json(selected_pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = make_zip(selected_pack_dir, selected_zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    manifest["zip_size_bytes"] = selected_zip_path.stat().st_size
    manifest["status"] = (
        "packed_review_ready"
        if review_ready and backslash_entries == 0 and manifest["zip_size_bytes"] <= MAX_ZIP_BYTES
        else "packed_with_blocks"
    )
    write_review_summary(selected_pack_dir / "10_context" / "review_summary.md", manifest)
    write_json(selected_pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = make_zip(selected_pack_dir, selected_zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    manifest["zip_size_bytes"] = selected_zip_path.stat().st_size
    if manifest["zip_size_bytes"] > MAX_ZIP_BYTES:
        raise RuntimeError(
            f"review pack exceeds hard compressed-size limit: {manifest['zip_size_bytes']} > {MAX_ZIP_BYTES}"
        )
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] entry_count={manifest['entry_count']}")
    return manifest


def main() -> None:
    build_lane2_gated_diagnostic_evidence_review_pack()


if __name__ == "__main__":
    main()
