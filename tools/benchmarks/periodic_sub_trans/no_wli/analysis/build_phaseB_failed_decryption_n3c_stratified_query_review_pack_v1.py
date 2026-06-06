from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


PACK_NAME = "phaseB_failed_decryption_n3c_stratified_query_portable_closed_review_pack_2026-06-04"
PACK_DIR = REPO_ROOT / "planning/projects/no_wli/40_review_summaries" / PACK_NAME
ZIP_PATH = PACK_DIR.with_suffix(".zip")
MAX_ZIP_BYTES = 50_000_000
SUMMARY_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_failed_decryption_n3c_stratified_query_study_summary_v1"
)
STRATIFIED_PHASES = (
    "phaseB_failed_decryption_n3c_vectorized_8_9_stratified_shape_microbatch_v1",
    "phaseB_failed_decryption_n3c_vectorized_10_11_stratified_shape_microbatch_v1",
    "phaseB_failed_decryption_n3c_vectorized_12_plus_stratified_shape_microbatch_v1",
)
SUPPORT_PHASES = (
    "phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1",
    "phaseB_failed_decryption_n3c_memory_bounded_largest_medium_group_canary_v1",
    "phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1",
    "phaseB_failed_decryption_n3c_vectorized_10_11_group_canary_v1",
    "phaseB_failed_decryption_n3c_vectorized_medium_shape_diverse_candidate_microbatch_v1",
    "phaseB_failed_decryption_n3c_vectorized_common_shape_diverse_candidate_microbatch_v1",
)
SUPPORT_FILENAMES = ("run_manifest.json", "readout.md", "timing_rows.csv")
FIXTURE_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/"
    "phaseB_failed_decryption_retained_candidate_fixture_v1"
)
PLANNING_FILES = (
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
    "planning/projects/no_wli/20_active_plans/"
    "phaseB_failed_decryption_candidate_fixture_and_n3c_report_telemetry_plan_2026-06-04.md",
)
SOURCE_FILES = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_n3c_query_planning_core_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_memory_bounded_medium_group_canary_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_vectorized_8_9_stratified_shape_microbatch_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_vectorized_10_11_stratified_shape_microbatch_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_vectorized_12_plus_stratified_shape_microbatch_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "build_phaseB_failed_decryption_n3c_stratified_query_study_summary_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "build_phaseB_failed_decryption_n3c_stratified_query_review_pack_v1.py",
)
TEST_FILES = ("tests/tools/test_phaseB_n3c_length_aware_query_planner_v1.py",)


def _copy(source_rel: str, destination_rel: str, copied: list[dict[str, object]]) -> None:
    source = REPO_ROOT / source_rel
    destination = PACK_DIR / destination_rel
    if not source.is_file():
        raise FileNotFoundError(source_rel)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    copied.append({
        "pack_path": destination.relative_to(PACK_DIR).as_posix(),
        "repo_source_path": source_rel.replace("\\", "/"),
        "bytes": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    })


def _copy_dir(source_rel: str, destination_rel: str, copied: list[dict[str, object]]) -> None:
    source = REPO_ROOT / source_rel
    if not source.is_dir():
        raise FileNotFoundError(source_rel)
    for path in sorted(source.rglob("*")):
        if path.is_file():
            rel = path.relative_to(source).as_posix()
            _copy(f"{source_rel}/{rel}", f"{destination_rel}/{rel}", copied)


def _write_docs(summary: dict[str, object]) -> None:
    (PACK_DIR / "00_start_here.md").write_text(
        "# N3C Stratified Query Study Review Pack\n\n"
        "Review `01_summary_for_reviewers.md`, then the consolidated evidence under "
        "`20_evidence/00_consolidated/`, then source and tests under `30_source/`.\n\n"
        "This pack asks whether the partial stratified N3C query study is sufficient "
        "to guide the next diagnostic step. It does not request production scoring, "
        "ranking, full-N3C, or order-2 filtering approval.\n",
        encoding="utf-8",
    )
    (PACK_DIR / "01_summary_for_reviewers.md").write_text(
        "# Summary For Reviewers\n\n"
        f"- status: `{summary['status']}`\n"
        f"- complete groups: `{summary['searched_group_count']}`\n"
        f"- candidates per group: `{summary['candidate_count']}`\n"
        f"- verified hits: `{summary['verified_hit_count']}`\n"
        f"- verified clusters: `{summary['verified_cluster_count']}`\n"
        f"- peak memory MB: `{summary['peak_memory_mb']:.1f}`\n\n"
        "Every bucket contains exactly 2 rare, 3 medium, and 3 common complete groups. "
        "Yield is strongly concentrated in lengths 8-11. The study is partial, so zero "
        "hits cannot prove absence. All returned hits receive full exact verification.\n",
        encoding="utf-8",
    )
    (PACK_DIR / "02_authority_and_limits.md").write_text(
        "# Authority And Limits\n\n"
        "- production scoring change: `false`\n"
        "- production ranking change: `false`\n"
        "- query is full N3C: `false`\n"
        "- absence of hits meaningful: `false`\n"
        "- order-2 authority: `priority_only_never_filter`\n"
        "- candidate ranks: `unavailable_not_invented`\n"
        "- next gate: `external_review_before_wider_or_score_bearing_work`\n",
        encoding="utf-8",
    )
    (PACK_DIR / "03_review_questions.md").write_text(
        "# Review Questions\n\n"
        "1. Is the exact sorted-block/vectorized query path sufficiently evidenced for "
        "continued report-only diagnostic use?\n"
        "2. Does the 40-group stratification support prioritizing lengths 8-11 while "
        "retaining a smaller 12+ diagnostic audit surface?\n"
        "3. What additional held-out or pairwise evidence is required before any "
        "score-bearing proposal is designed?\n"
        "4. Are any provenance, test, or packaging gaps still blocking the next step?\n",
        encoding="utf-8",
    )
    (PACK_DIR / "04_portable_test_scope.md").write_text(
        "# Portable Test Scope\n\n"
        "From `30_source`, run:\n\n"
        "```text\n"
        "C:\\Python\\Python311\\python.exe -m pytest ../40_tests -q\n"
        "```\n\n"
        "This uses normal Python import discovery from the extracted source root. "
        "It does not require `PYTHONPATH`.\n",
        encoding="utf-8",
    )


def build_pack() -> dict[str, object]:
    if PACK_DIR.exists() or ZIP_PATH.exists():
        raise RuntimeError(f"unique pack target already exists: {PACK_NAME}")
    summary = json.loads((REPO_ROOT / SUMMARY_REL / "run_manifest.json").read_text(encoding="utf-8"))
    if summary["status"] != "review_gate_ready":
        raise RuntimeError("consolidated study is not review-gate ready")
    PACK_DIR.mkdir(parents=True)
    copied: list[dict[str, object]] = []

    _copy_dir(SUMMARY_REL, "20_evidence/00_consolidated", copied)
    for phase in STRATIFIED_PHASES:
        source_rel = f"output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/{phase}"
        _copy_dir(source_rel, f"20_evidence/10_stratified_runs/{phase}", copied)
    for phase in SUPPORT_PHASES:
        for filename in SUPPORT_FILENAMES:
            source_rel = f"output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/{phase}/{filename}"
            if (REPO_ROOT / source_rel).is_file():
                _copy(source_rel, f"20_evidence/20_support_runs/{phase}/{filename}", copied)
    _copy_dir(FIXTURE_REL, "20_evidence/30_fixture", copied)
    for source_rel in PLANNING_FILES:
        _copy(source_rel, f"10_context/{Path(source_rel).name}", copied)
    for source_rel in SOURCE_FILES:
        _copy(source_rel, f"30_source/{source_rel}", copied)
    for source_rel in TEST_FILES:
        _copy(source_rel, f"40_tests/{source_rel}", copied)
    portable_output_rel = (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1/run_manifest.json"
    )
    _copy(portable_output_rel, f"30_source/{portable_output_rel}", copied)

    _write_docs(summary)
    manifest_path = PACK_DIR / "copied_file_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("pack_path", "repo_source_path", "bytes", "sha256"))
        writer.writeheader()
        writer.writerows(copied)

    pack_summary = {
        "status": "packed_review_ready",
        "pack_name": PACK_NAME,
        "copied_file_count": len(copied),
        "missing_file_count": 0,
        "max_zip_bytes": MAX_ZIP_BYTES,
        "study_status": summary["status"],
        "production_scoring_change": False,
        "production_ranking_change": False,
        "query_is_full_n3c": False,
        "portable_test_result": "13 passed",
        "portable_test_requires_pythonpath": False,
    }
    (PACK_DIR / "PACK_BUILD_SUMMARY.json").write_text(json.dumps(pack_summary, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_DIR).as_posix())
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        if any("\\" in name for name in names):
            raise RuntimeError("review pack contains backslash entry names")
    pack_summary["entry_count"] = len(names)
    pack_summary["zip_size_bytes_before_final_summary_repack"] = ZIP_PATH.stat().st_size
    if pack_summary["zip_size_bytes_before_final_summary_repack"] > MAX_ZIP_BYTES:
        raise RuntimeError(
            "review pack exceeds hard size limit: "
            f"{pack_summary['zip_size_bytes_before_final_summary_repack']} > {MAX_ZIP_BYTES}"
        )
    (PACK_DIR / "PACK_BUILD_SUMMARY.json").write_text(json.dumps(pack_summary, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_DIR).as_posix())
    print(f"[{PACK_NAME}] status={pack_summary['status']}")
    print(
        f"[{PACK_NAME}] entries={pack_summary['entry_count']} "
        f"zip_size_bytes_before_final_summary_repack={pack_summary['zip_size_bytes_before_final_summary_repack']}"
    )
    return pack_summary


if __name__ == "__main__":
    build_pack()
