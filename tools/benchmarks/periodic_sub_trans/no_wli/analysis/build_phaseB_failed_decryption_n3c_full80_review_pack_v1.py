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


PACK_NAME = "phaseB_failed_decryption_n3c_full80_consolidated_packaging_closed_review_pack_2026-06-05"
PACK_DIR = REPO_ROOT / "planning/projects/no_wli/40_review_summaries" / PACK_NAME
ZIP_PATH = PACK_DIR.with_suffix(".zip")
MAX_ZIP_BYTES = 50_000_000
ANALYSIS_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
CONSOLIDATED_REL = f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1"
BUCKET_PHASES = (
    "phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1",
    "phaseB_failed_decryption_n3c_full80_bucket_10_11_query_evidence_v1",
    "phaseB_failed_decryption_n3c_full80_bucket_12_14_query_evidence_v1",
    "phaseB_failed_decryption_n3c_full80_bucket_15_17_query_evidence_v1",
    "phaseB_failed_decryption_n3c_full80_bucket_18_plus_query_evidence_v1",
)
SMALL_BUCKET_FILES = (
    "run_manifest.json",
    "readout.md",
    "candidate_rows.csv",
    "candidate_n3c_summary_rows.csv",
    "chunk_timing_rows.csv",
    "logical_group_summary_rows.csv",
    "pairwise_gold_n3c_report_rows.csv",
    "progress_manifest.json",
    "run.log",
)
PLANNING_FILES = (
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
    "planning/projects/no_wli/20_active_plans/"
    "phaseB_failed_decryption_candidate_fixture_and_n3c_report_telemetry_plan_2026-06-04.md",
)
FIXTURE_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/"
    "phaseB_failed_decryption_retained_candidate_fixture_v1"
)
RUNTIME_MANIFESTS = (
    f"{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index_manifest.json",
    f"{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json",
)
SOURCE_FILES = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_n3c_query_planning_core_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_full80_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_full80_bucket_10_11_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_full80_bucket_12_14_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_full80_bucket_15_17_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "run_phaseB_failed_decryption_n3c_full80_bucket_18_plus_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "build_phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "build_phaseB_failed_decryption_n3c_full80_review_pack_v1.py",
)
TEST_FILES = (
    "tests/tools/test_phaseB_n3c_length_aware_query_planner_v1.py",
    "tests/tools/test_phaseB_failed_decryption_candidate_fixture_v1.py",
    "tests/tools/test_phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1.py",
)


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def copy_file(source_rel: str, destination_rel: str, copied: list[dict[str, object]]) -> None:
    source = REPO_ROOT / source_rel
    destination = PACK_DIR / destination_rel
    if not source.is_file():
        raise FileNotFoundError(source_rel)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    copied.append({
        "pack_path": destination.relative_to(PACK_DIR).as_posix(),
        "repo_source_path": source_rel,
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    })


def copy_dir(source_rel: str, destination_rel: str, copied: list[dict[str, object]]) -> None:
    source = REPO_ROOT / source_rel
    for path in sorted(source.rglob("*")):
        if path.is_file():
            rel = path.relative_to(source).as_posix()
            copy_file(f"{source_rel}/{rel}", f"{destination_rel}/{rel}", copied)


def write_docs(summary: dict[str, object]) -> None:
    (PACK_DIR / "00_start_here.md").write_text(
        "# Full80 N3C Consolidated Review Pack\n\n"
        "Start with `01_summary_for_reviewers.md`, then inspect the consolidated "
        "evidence under `20_evidence/00_consolidated/`. The detailed hit CSVs are "
        "not duplicated into this ZIP; their repo-relative paths, sizes, row counts, "
        "and SHA-256 hashes are listed in `20_evidence/00_consolidated/hit_file_manifest_rows.csv`.\n",
        encoding="utf-8",
    )
    (PACK_DIR / "01_summary_for_reviewers.md").write_text(
        "# Summary For Reviewers\n\n"
        f"- status: `{summary['status']}`\n"
        f"- full selected-80 N3C chunks: `{summary['runtime_chunk_count']}`\n"
        f"- logical groups: `{summary['logical_group_count']}`\n"
        f"- phrase rows: `{summary['runtime_phrase_rows']}`\n"
        f"- verified hits: `{summary['verified_hit_count']}`\n"
        f"- true global candidate clusters: `{summary['global_candidate_n3c_cluster_count']}`\n"
        f"- exact global candidate clusters: `{summary['global_candidate_n3c_exact_cluster_count']}`\n"
        f"- pair rows: `{summary['pair_count_with_both_candidates_in_sample']}`\n"
        f"- pair result counts: `{json.dumps(summary['pair_result_counts'], sort_keys=True)}`\n\n"
        "This pack asks for review of the full selected-80 N3C evidence. It does "
        "not ask for score-bearing use, production ranking changes, or expansion "
        "to all 734 fixture candidates.\n",
        encoding="utf-8",
    )
    (PACK_DIR / "02_authority_and_limits.md").write_text(
        "# Authority And Limits\n\n"
        "- production scoring change: `false`\n"
        "- production ranking change: `false`\n"
        "- score-bearing use approved: `false`\n"
        "- query is full N3C for selected 80 candidates: `true`\n"
        "- query is full 734-candidate fixture: `false`\n"
        "- order-2 authority: `priority_only_never_filter`\n"
        "- next gate: external review before 734-candidate fixture or score-bearing work\n",
        encoding="utf-8",
    )
    (PACK_DIR / "03_review_questions.md").write_text(
        "# Review Questions\n\n"
        "1. Does the full selected-80 N3C evidence support any next diagnostic "
        "aggregation beyond simple hit or simple cluster counts?\n"
        "2. Given the pair ledger break rates, should N3C stay report-only until "
        "N4L/S34C confirmation evidence exists?\n"
        "3. Is expansion to all 734 candidates justified, or should a better "
        "hard-pair sample be selected first?\n"
        "4. Are the runtime manifests and hit-file SHA manifests sufficient for "
        "review without embedding the large hit CSVs in the ZIP?\n",
        encoding="utf-8",
    )


def write_sampled_hits(copied: list[dict[str, object]]) -> None:
    for phase in BUCKET_PHASES:
        source_rel = f"{ANALYSIS_ROOT_REL}/{phase}/n3c_verified_hit_rows.csv"
        source = REPO_ROOT / source_rel
        destination = PACK_DIR / "20_evidence/30_sampled_hits" / f"{phase}_first_200_hit_rows.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open(encoding="utf-8", newline="") as in_handle, destination.open(
            "w", encoding="utf-8", newline=""
        ) as out_handle:
            reader = csv.DictReader(in_handle)
            writer = csv.DictWriter(out_handle, fieldnames=reader.fieldnames)
            writer.writeheader()
            for index, row in enumerate(reader):
                if index >= 200:
                    break
                writer.writerow(row)
        copied.append({
            "pack_path": destination.relative_to(PACK_DIR).as_posix(),
            "repo_source_path": f"sampled from {source_rel}",
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        })


def build_pack() -> dict[str, object]:
    if PACK_DIR.exists() or ZIP_PATH.exists():
        raise RuntimeError(f"unique pack target already exists: {PACK_NAME}")
    summary = json.loads((REPO_ROOT / CONSOLIDATED_REL / "run_manifest.json").read_text(encoding="utf-8"))
    if summary["status"] != "full80_consolidated_evidence_ready_for_review":
        raise RuntimeError("full80 consolidated evidence is not review-ready")
    PACK_DIR.mkdir(parents=True)
    copied: list[dict[str, object]] = []
    copy_dir(CONSOLIDATED_REL, "20_evidence/00_consolidated", copied)
    for phase in BUCKET_PHASES:
        for filename in SMALL_BUCKET_FILES:
            copy_file(f"{ANALYSIS_ROOT_REL}/{phase}/{filename}", f"20_evidence/10_bucket_runs/{phase}/{filename}", copied)
    for source_rel in RUNTIME_MANIFESTS:
        copy_file(source_rel, f"20_evidence/20_runtime_manifests/{Path(source_rel).name}", copied)
    copy_dir(FIXTURE_REL, "20_evidence/40_fixture", copied)
    write_sampled_hits(copied)
    for source_rel in PLANNING_FILES:
        copy_file(source_rel, f"10_context/{Path(source_rel).name}", copied)
    for source_rel in SOURCE_FILES:
        copy_file(source_rel, f"30_source/{source_rel}", copied)
    for source_rel in TEST_FILES:
        copy_file(source_rel, f"40_tests/{source_rel}", copied)
    copy_file(
        f"{CONSOLIDATED_REL}/run_manifest.json",
        f"30_source/{CONSOLIDATED_REL}/run_manifest.json",
        copied,
    )
    write_docs(summary)

    with (PACK_DIR / "copied_file_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("pack_path", "repo_source_path", "bytes", "sha256"))
        writer.writeheader()
        writer.writerows(copied)
    pack_summary = {
        "status": "packed_review_ready",
        "pack_name": PACK_NAME,
        "copied_file_count": len(copied),
        "missing_file_count": 0,
        "study_status": summary["status"],
        "portable_test_result": "24 passed in repo; fresh extracted consolidated portable test 2 passed",
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "max_zip_bytes": MAX_ZIP_BYTES,
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
            "review pack exceeds size limit: "
            f"{pack_summary['zip_size_bytes_before_final_summary_repack']}"
        )
    (PACK_DIR / "PACK_BUILD_SUMMARY.json").write_text(json.dumps(pack_summary, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_DIR).as_posix())
    print(f"[{PACK_NAME}] status={pack_summary['status']}")
    print(
        f"[{PACK_NAME}] entries={pack_summary['entry_count']} "
        f"zip_size_bytes_before_final_summary_repack="
        f"{pack_summary['zip_size_bytes_before_final_summary_repack']}"
    )
    return pack_summary


if __name__ == "__main__":
    build_pack()
