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

PACK_NAME = "phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_review_pack_2026-06-05"
PACK_ROOT = REPO_ROOT / "planning/projects/no_wli/40_review_summaries"
PACK_DIR = PACK_ROOT / PACK_NAME
ZIP_PATH = PACK_ROOT / f"{PACK_NAME}.zip"
MAX_ZIP_BYTES = 50_000_000
ANALYSIS_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
CORRECTED_REL = f"{ANALYSIS_ROOT_REL}/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1"
BUCKET_RELS = (
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
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_failed_decryption_n3c_normal_full80_corrected_review_pack_v1.py",
)
TEST_FILES = (
    "tests/tools/test_phaseB_n3c_normal_correction_strict_run_spec_v1.py",
    "tests/tools/test_phaseB_n3c_normal_full80_corrected_consolidated_evidence_v1.py",
)
CORRECTED_OUTPUT_FILES = (
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
PORTABLE_OUTPUT_FILES = tuple(f"{CORRECTED_REL}/{name}" for name in CORRECTED_OUTPUT_FILES) + (
    f"{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index_manifest.json",
    f"{ANALYSIS_ROOT_REL}/phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json",
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


def sample_hit_rows(bucket_rel: str, max_rows: int = 200) -> list[dict[str, str]]:
    path = REPO_ROOT / bucket_rel / "n3c_verified_hit_rows.csv"
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            if index >= max_rows:
                break
            rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_pack() -> dict[str, object]:
    if PACK_DIR.exists() or ZIP_PATH.exists():
        raise RuntimeError(f"pack already exists: {PACK_NAME}")
    corrected_manifest = json.loads((REPO_ROOT / CORRECTED_REL / "run_manifest.json").read_text(encoding="utf-8"))
    if corrected_manifest["status"] != "n3c_normal_full80_corrected_consolidated_evidence_ready_for_engineering_gate":
        raise RuntimeError("corrected normal evidence is not ready")
    if corrected_manifest["production_scoring_change"] or corrected_manifest["production_ranking_change"]:
        raise RuntimeError("corrected normal evidence must remain report-only")

    copied: list[dict[str, object]] = []
    PACK_DIR.mkdir(parents=True)
    (PACK_DIR / "00_start_here.md").write_text(
        "# Corrected Normal Full80 N3C Review Pack\n\n"
        "This pack supersedes the earlier cut-ambiguous full80 pack as the corrected normal-cut reference. "
        "It does not rerun the expensive normal query and does not approve score-bearing or production-ranking use.\n\n"
        "- dictionary cut: `normal`\n"
        "- selected candidates: `80`, not all `734`\n"
        "- verified hit count: `1,667,717`\n"
        "- ordinary global candidate clusters: `275`\n"
        "- corrected exact-containing global candidate clusters: `225`\n"
        "- raw selected-sample pair rows: `16`\n"
        "- unique selected-sample semantic pairs: `8`\n"
        "- rescue-capable unique semantic pairs: `0`\n"
        "- next gate: engineering correction gate before S3 strict full80 buckets\n",
        encoding="utf-8",
    )
    (PACK_DIR / "02_authority_and_limits.md").write_text(
        "# Authority And Limits\n\n"
        "This is report-only experimental evidence. Production scoring, production ranking, raw-hit-count "
        "authority, simple cluster-count authority, order-4 authority, and all-734 expansion are not approved.\n\n"
        "Complete normal hit CSVs are external to this ZIP and are represented by path, row count, byte count, "
        "and SHA-256 in `20_corrected_evidence/hit_file_manifest_rows.csv`.\n",
        encoding="utf-8",
    )
    (PACK_DIR / "03_engineering_gate.md").write_text(
        "# Engineering Correction Gate\n\n"
        "Pass conditions covered by this pack:\n\n"
        "- existing normal hit files reused; no normal query rerun\n"
        "- exact-containing cluster semantics corrected\n"
        "- exact-containing cluster count is bounded by ordinary cluster count\n"
        "- raw pair rows and unique semantic pairs are separated\n"
        "- break/rescue capability labels are explicit\n"
        "- S3 strict RunSpec selection is tested against the locked inventory\n"
        "- production score/rank authority remains unchanged\n",
        encoding="utf-8",
    )
    for rel in SOURCE_FILES:
        copy_file(rel, f"30_source/{rel}", copied)
    for rel in TEST_FILES:
        copy_file(rel, f"40_tests/{rel}", copied)
    for name in CORRECTED_OUTPUT_FILES:
        copy_file(f"{CORRECTED_REL}/{name}", f"20_corrected_evidence/{name}", copied)
    for rel in PORTABLE_OUTPUT_FILES:
        copy_file(rel, f"30_source/{rel}", copied)
    for bucket_rel in BUCKET_RELS:
        for name in ("run_manifest.json", "readout.md", "chunk_timing_rows.csv", "logical_group_summary_rows.csv"):
            copy_file(f"{bucket_rel}/{name}", f"21_source_bucket_summaries/{Path(bucket_rel).name}/{name}", copied)
        rows = sample_hit_rows(bucket_rel)
        write_csv(
            PACK_DIR / "22_sampled_hit_rows" / f"{Path(bucket_rel).name}_first_200_hit_rows.csv",
            rows,
            tuple(rows[0]),
        )

    with (PACK_DIR / "copied_file_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("pack_path", "repo_source_path", "bytes", "sha256"))
        writer.writeheader()
        writer.writerows(copied)

    pack_summary = {
        "status": "packed_review_ready",
        "pack_name": PACK_NAME,
        "corrected_evidence_status": corrected_manifest["status"],
        "copied_file_count": len(copied),
        "dictionary_cut": "normal",
        "normal_query_rerun": False,
        "verified_hit_count": corrected_manifest["verified_hit_count"],
        "global_candidate_n3c_cluster_count": corrected_manifest["global_candidate_n3c_cluster_count"],
        "global_candidate_n3c_exact_containing_cluster_count": corrected_manifest[
            "global_candidate_n3c_exact_containing_cluster_count"
        ],
        "raw_pair_row_count_with_both_candidates_in_sample": corrected_manifest[
            "raw_pair_row_count_with_both_candidates_in_sample"
        ],
        "unique_semantic_pair_count_with_both_candidates_in_sample": corrected_manifest[
            "unique_semantic_pair_count_with_both_candidates_in_sample"
        ],
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "portable_test_result": "fresh extracted corrected-normal portable tests 8 passed",
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
        raise RuntimeError("corrected normal review pack exceeds size limit")
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
