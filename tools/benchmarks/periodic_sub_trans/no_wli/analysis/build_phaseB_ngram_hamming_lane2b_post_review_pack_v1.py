from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1 as base,
)


RUN_LABEL = "phaseB_ngram_hamming_lane2b_post_review_pack_v1"
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_ngram_hamming_lane2b_stratified_telemetry_order4_sizing_review_pack_2026-06-03"
)
ZIP_REL = f"{PACK_DIR_REL}.zip"
LANE2B_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1"
)
ADDITIONAL_CONTEXT_REL = (
    "planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_selection_fixed_external_review_decision_2026-06-03.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_order4_size_and_readiness_plan_2026-06-03.md",
)
ADDITIONAL_COMPONENTS_REL = tuple(
    f"{LANE2B_DIR_REL}/{name}"
    for name in (
        "run_manifest.json",
        "corpus_manifest.json",
        "selection_manifest.json",
        "selection_manifest_rows.csv",
        "selected_phrase_entries.jsonl",
        "diagnostic_cases.jsonl",
        "boundary_cases.jsonl",
        "positive_cases.jsonl",
        "null_passages.jsonl",
        "damaged_cases.jsonl",
        "full_hit_rows.csv",
        "sampled_hit_rows.csv",
        "scan_diagnostic_rows.csv",
        "candidate_profile_summary_rows.csv",
        "candidate_cluster_summary_rows.csv",
        "null_comparison_rows.csv",
        "concentration_rows.csv",
        "damage_tier_summary_rows.csv",
        "review_readout.md",
    )
)
ADDITIONAL_SOURCE_REL = (
    "src/rune_decrypter_prime/scoring/ngram_hamming/report_only_telemetry.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_lane2b_post_review_pack_v1.py",
)
ADDITIONAL_TESTS_REL = (
    "tests/scoring/ngram_hamming/test_report_only_telemetry.py",
    "tests/tools/test_phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1.py",
)


def write_next_review_summary(path: Path, manifest: dict[str, Any]) -> None:
    base.ensure_under_repo(path)
    lines = [
        "# Lane 2B Post-Review Summary",
        "",
        f"- status: `{manifest['status']}`",
        f"- Lane 2B evidence status: `{manifest['lane2b_evidence_status']}`",
        f"- Lane 2B selection contract: `{manifest['lane2b_selection_contract_status']}`",
        f"- Lane 2B opportunity contract: `{manifest['lane2b_opportunity_contract_status']}`",
        f"- Lane 2B cases: `{manifest['lane2b_case_count']}`",
        f"- Lane 2B selected entries: `{manifest['lane2b_phrase_entry_count']}`",
        f"- Lane 2B raw hits: `{manifest['lane2b_raw_hit_count']}`",
        f"- report-only telemetry rank effect: `{manifest['report_only_telemetry_rank_effect']}`",
        f"- order-4 full build approved: `{manifest['order4_full_build_approved']}`",
        f"- zip bytes: `{manifest.get('zip_size_bytes', 'pending')}`",
        "",
        "This pack requests review of the stratified diagnostic result, isolated",
        "N3C-normal report-only telemetry contract, and order-4 sizing/build hold.",
        "It does not request production scoring or ranking authority.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_lane2b_post_review_pack() -> dict[str, Any]:
    lane2b_manifest_path = base.REPO_ROOT / LANE2B_DIR_REL / "run_manifest.json"
    lane2b_manifest = json.loads(lane2b_manifest_path.read_text(encoding="utf-8"))
    if (
        lane2b_manifest.get("evidence_status") != "diagnostic_evidence_ready_for_review"
        or lane2b_manifest.get("selection_contract_status") != "pass"
        or lane2b_manifest.get("opportunity_contract_status") != "pass"
    ):
        raise RuntimeError("Lane 2B evidence contracts are not review-ready")

    original_context = base.CONTEXT_FILES_REL
    original_components = base.COMPONENT_FILES_REL
    original_source = base.SOURCE_FILES_REL
    original_tests = base.TEST_FILES_REL
    try:
        base.CONTEXT_FILES_REL = (*original_context, *ADDITIONAL_CONTEXT_REL)
        base.COMPONENT_FILES_REL = (*original_components, *ADDITIONAL_COMPONENTS_REL)
        base.SOURCE_FILES_REL = (*original_source, *ADDITIONAL_SOURCE_REL)
        base.TEST_FILES_REL = (*original_tests, *ADDITIONAL_TESTS_REL)
        manifest = base.build_lane2_gated_diagnostic_evidence_review_pack(
            pack_dir=base.REPO_ROOT / PACK_DIR_REL,
            zip_path=base.REPO_ROOT / ZIP_REL,
        )
    finally:
        base.CONTEXT_FILES_REL = original_context
        base.COMPONENT_FILES_REL = original_components
        base.SOURCE_FILES_REL = original_source
        base.TEST_FILES_REL = original_tests

    manifest.update(
        {
            "run_label": RUN_LABEL,
            "lane2b_evidence_status": lane2b_manifest["evidence_status"],
            "lane2b_selection_contract_status": lane2b_manifest["selection_contract_status"],
            "lane2b_opportunity_contract_status": lane2b_manifest["opportunity_contract_status"],
            "lane2b_case_count": lane2b_manifest["case_count"],
            "lane2b_phrase_entry_count": lane2b_manifest["phrase_entry_count"],
            "lane2b_raw_hit_count": lane2b_manifest["raw_hit_count"],
            "report_only_telemetry_rank_effect": "none",
            "order4_full_build_approved": False,
        }
    )
    pack_dir = base.REPO_ROOT / PACK_DIR_REL
    zip_path = base.REPO_ROOT / ZIP_REL
    write_next_review_summary(pack_dir / "10_context" / "lane2b_post_review_summary.md", manifest)
    base.write_json(pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = base.make_zip(pack_dir, zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    manifest["zip_size_bytes"] = zip_path.stat().st_size
    if manifest["zip_size_bytes"] > base.MAX_ZIP_BYTES:
        raise RuntimeError("Lane 2B post-review pack exceeds hard compressed-size limit")
    write_next_review_summary(pack_dir / "10_context" / "lane2b_post_review_summary.md", manifest)
    base.write_json(pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = base.make_zip(pack_dir, zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    manifest["zip_size_bytes"] = zip_path.stat().st_size
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] entry_count={manifest['entry_count']} zip_size_bytes={manifest['zip_size_bytes']}")
    return manifest


def main() -> None:
    build_lane2b_post_review_pack()


if __name__ == "__main__":
    main()
