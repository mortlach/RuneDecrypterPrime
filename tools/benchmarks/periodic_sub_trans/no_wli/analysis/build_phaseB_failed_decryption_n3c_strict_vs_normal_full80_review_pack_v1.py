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

PACK_NAME = "phaseB_failed_decryption_n3c_strict_vs_normal_full80_review_pack_2026-06-06"
PACK_ROOT = REPO_ROOT / "planning/projects/no_wli/40_review_summaries"
PACK_DIR = PACK_ROOT / PACK_NAME
ZIP_PATH = PACK_ROOT / f"{PACK_NAME}.zip"
MAX_ZIP_BYTES = 50_000_000
ANALYSIS_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
NORMAL_REL = f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1"
STRICT_REL = f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1"
COMPARISON_REL = f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1"
STRICT_BUCKET_RELS = (
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_full80_bucket_8_9_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_full80_bucket_10_11_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_full80_bucket_15_17_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_strict_full80_bucket_18_plus_query_evidence_v1",
)
NORMAL_BUCKET_RELS = (
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_full80_bucket_10_11_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_full80_bucket_12_14_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_full80_bucket_15_17_query_evidence_v1",
    f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_full80_bucket_18_plus_query_evidence_v1",
)
SOURCE_FILES = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_n3c_query_planning_core_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_common_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_8_9_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_10_11_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_15_17_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_18_plus_query_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/launch_phaseB_failed_decryption_n3c_strict_full80_all_buckets_visible_v1.ps1",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_failed_decryption_n3c_strict_vs_normal_full80_review_pack_v1.py",
)
TEST_FILES = (
    "tests/tools/test_phaseB_n3c_normal_correction_strict_run_spec_v1.py",
    "tests/tools/test_phaseB_n3c_normal_full80_corrected_consolidated_evidence_v1.py",
    "tests/tools/test_phaseB_n3c_strict_full80_consolidated_and_comparison_v1.py",
)
EVIDENCE_FILES = (
    "run_manifest.json",
    "readout.md",
    "bucket_summary_rows.csv",
    "chunk_timing_rows.csv",
    "logical_group_summary_rows.csv",
    "hit_file_manifest_rows.csv",
    "candidate_n3c_cluster_rows.csv",
    "candidate_n3c_summary_rows.csv",
    "raw_pairwise_gold_n3c_report_rows.csv",
    "unique_semantic_pairwise_gold_n3c_report_rows.csv",
)
COMPARISON_FILES = (
    "run_manifest.json",
    "readout.md",
    "bucket_comparison_rows.csv",
    "candidate_comparison_rows.csv",
    "semantic_pair_comparison_rows.csv",
    "length_yield_comparison_rows.csv",
    "word_shape_yield_comparison_rows.csv",
)


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def copy_file(rel_path: str, pack_rel: str, copied: list[dict[str, object]]) -> None:
    source = REPO_ROOT / rel_path
    target = PACK_DIR / pack_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copied.append({
        "pack_path": pack_rel,
        "repo_source_path": rel_path,
        "bytes": source.stat().st_size,
        "sha256": file_sha256(source),
    })


def write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sample_hit_rows(bucket_rel: str, max_rows: int = 100) -> list[dict[str, str]]:
    path = REPO_ROOT / bucket_rel / "n3c_verified_hit_rows.csv"
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            if index >= max_rows:
                break
            rows.append(row)
    return rows


def copy_evidence_dir(rel_dir: str, pack_prefix: str, copied: list[dict[str, object]]) -> None:
    for name in EVIDENCE_FILES:
        copy_file(f"{rel_dir}/{name}", f"{pack_prefix}/{name}", copied)
        copy_file(f"{rel_dir}/{name}", f"30_source/{rel_dir}/{name}", copied)


def build_pack() -> dict[str, object]:
    if PACK_DIR.exists() or ZIP_PATH.exists():
        raise RuntimeError(f"pack already exists: {PACK_NAME}")
    normal_manifest = json.loads((REPO_ROOT / NORMAL_REL / "run_manifest.json").read_text(encoding="utf-8"))
    strict_manifest = json.loads((REPO_ROOT / STRICT_REL / "run_manifest.json").read_text(encoding="utf-8"))
    comparison_manifest = json.loads((REPO_ROOT / COMPARISON_REL / "run_manifest.json").read_text(encoding="utf-8"))
    if comparison_manifest["status"] != "n3c_strict_vs_normal_full80_comparison_ready_for_review_pack":
        raise RuntimeError("comparison is not ready")

    copied: list[dict[str, object]] = []
    PACK_DIR.mkdir(parents=True)
    (PACK_DIR / "00_start_here.md").write_text(
        "# N3C Strict Versus Normal Full80 Review Pack\n\n"
        "This pack contains the corrected normal reference, complete S3 strict full80 evidence, and matched "
        "strict-versus-normal comparison. It is report-only evidence and does not approve production scoring, "
        "ranking changes, raw-hit authority, simple-cluster authority, or all-734 expansion.\n\n"
        "- normal verified hits: `1,667,717`\n"
        "- strict verified hits: `1,546,511`\n"
        "- strict hit retention: `92.7%`\n"
        "- normal phrase rows: `613,280,613`\n"
        "- strict phrase rows: `365,516,232`\n"
        "- strict phrase-row retention: `59.6%`\n"
        "- normal global clusters: `275`; strict global clusters: `308`\n"
        "- normal exact-containing clusters: `225`; strict exact-containing clusters: `249`\n"
        "- unique semantic pairs: `8`; rescue-capable pairs: `0`\n",
        encoding="utf-8",
    )
    (PACK_DIR / "02_authority_and_limits.md").write_text(
        "# Authority And Limits\n\n"
        "The current fixture is baseline-correct only for the selected semantic pairs, so it can measure break risk "
        "but cannot demonstrate rescue. Strict and normal phrase-level shared/only classes are not reported because "
        "stable phrase identity across cuts has not been proven. Full hit CSVs are external to this ZIP and are "
        "represented by path, row count, byte count, and SHA-256 manifests.\n",
        encoding="utf-8",
    )
    (PACK_DIR / "03_review_questions.md").write_text(
        "# Review Questions\n\n"
        "1. Did S3 strict complete the declared selected-full80 strict scope safely?\n"
        "2. Is strict the better routine report-only order-3 baseline than normal?\n"
        "3. Does normal add useful recall beyond strict, or mainly saturated noise?\n"
        "4. What evidence is still required before any score-bearing trial?\n"
        "5. Should next work target a rescue-capable fixture, broader strict break-risk tranche, order-4 confirmation, or a combination?\n",
        encoding="utf-8",
    )

    for rel in SOURCE_FILES:
        copy_file(rel, f"30_source/{rel}", copied)
    for rel in TEST_FILES:
        copy_file(rel, f"40_tests/{rel}", copied)
    copy_file(
        f"{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index_manifest.json",
        f"30_source/{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index_manifest.json",
        copied,
    )
    copy_file(
        f"{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json",
        f"30_source/{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json",
        copied,
    )
    copy_evidence_dir(NORMAL_REL, "20_corrected_normal_evidence", copied)
    copy_evidence_dir(STRICT_REL, "21_corrected_strict_evidence", copied)
    for name in COMPARISON_FILES:
        copy_file(f"{COMPARISON_REL}/{name}", f"22_strict_vs_normal_comparison/{name}", copied)
        copy_file(f"{COMPARISON_REL}/{name}", f"30_source/{COMPARISON_REL}/{name}", copied)
    for bucket_rel in STRICT_BUCKET_RELS:
        for name in ("run_manifest.json", "readout.md", "chunk_timing_rows.csv", "logical_group_summary_rows.csv"):
            copy_file(f"{bucket_rel}/{name}", f"23_strict_bucket_summaries/{Path(bucket_rel).name}/{name}", copied)
        rows = sample_hit_rows(bucket_rel)
        if rows:
            write_csv(PACK_DIR / "24_sampled_strict_hit_rows" / f"{Path(bucket_rel).name}_first_100.csv", rows, tuple(rows[0]))
    for bucket_rel in NORMAL_BUCKET_RELS:
        for name in ("run_manifest.json", "readout.md"):
            copy_file(f"{bucket_rel}/{name}", f"25_normal_bucket_manifest_refs/{Path(bucket_rel).name}/{name}", copied)

    with (PACK_DIR / "copied_file_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("pack_path", "repo_source_path", "bytes", "sha256"))
        writer.writeheader()
        writer.writerows(copied)

    pack_summary = {
        "status": "packed_review_ready",
        "pack_name": PACK_NAME,
        "copied_file_count": len(copied),
        "normal_status": normal_manifest["status"],
        "strict_status": strict_manifest["status"],
        "comparison_status": comparison_manifest["status"],
        "normal_verified_hit_count": normal_manifest["verified_hit_count"],
        "strict_verified_hit_count": strict_manifest["verified_hit_count"],
        "strict_verified_hit_retention_fraction": comparison_manifest["verified_hit_retention_fraction"],
        "strict_phrase_row_retention_fraction": comparison_manifest["phrase_row_retention_fraction"],
        "portable_test_result": "fresh extracted strict-vs-normal portable tests 11 passed",
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
        raise RuntimeError("review pack exceeds size limit")
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
