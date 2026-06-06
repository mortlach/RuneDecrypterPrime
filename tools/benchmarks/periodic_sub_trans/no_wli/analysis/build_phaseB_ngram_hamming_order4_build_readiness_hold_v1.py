from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
RUN_LABEL = "phaseB_ngram_hamming_order4_build_readiness_hold_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_order4_build_readiness_hold_v1"
)

RAW_ASSET_ID = "phaseB_ngram_hamming_order4_fwd_nose_full_raw_v1"
CANARY_ASSET_ID = "phaseB_ngram_hamming_order4_fwd_nose_compact_lookup_canary_v1"
RAW_ROW_COUNT = 1_037_043_475
RAW_COMPLETED_SHARDS = 1_999
RAW_PAYLOAD_FILES = 3_998
RAW_PAYLOAD_BYTES = 17_499_944_107
RAW_RETAINED_GB = 66.9
CANARY_ROW_COUNT = 75_941
TOTAL_PARTITIONS = 800
COMPLETED_PARTITIONS = 50
NORMAL_COMPLETED_PARTITIONS = 25
STRICT_COMPLETED_PARTITIONS = 25
RETAINED_COMPACT_WORK_GB = 72.12
LINEAR_TEMP_ESTIMATE_GB = RETAINED_COMPACT_WORK_GB * TOTAL_PARTITIONS / COMPLETED_PARTITIONS


def _ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _ensure_under_repo(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: tuple[str, ...]) -> None:
    _ensure_under_repo(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_readiness_hold_evidence() -> dict[str, Any]:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    output_dir.mkdir(parents=True, exist_ok=True)

    partition_rows = (
        {
            "dictionary_cut": "normal",
            "completed_partitions": NORMAL_COMPLETED_PARTITIONS,
            "total_partitions": TOTAL_PARTITIONS // 2,
            "completion_fraction": NORMAL_COMPLETED_PARTITIONS / (TOTAL_PARTITIONS // 2),
            "status": "partial_held",
        },
        {
            "dictionary_cut": "strict",
            "completed_partitions": STRICT_COMPLETED_PARTITIONS,
            "total_partitions": TOTAL_PARTITIONS // 2,
            "completion_fraction": STRICT_COMPLETED_PARTITIONS / (TOTAL_PARTITIONS // 2),
            "status": "partial_held",
        },
    )
    estimate_rows = (
        {
            "measure": "raw_retained_gb",
            "value_gb": RAW_RETAINED_GB,
            "evidence_class": "measured_remote_summary",
            "launch_authority": "none",
        },
        {
            "measure": "partial_compact_work_retained_gb",
            "value_gb": RETAINED_COMPACT_WORK_GB,
            "evidence_class": "measured_remote_summary",
            "launch_authority": "none",
        },
        {
            "measure": "naive_linear_temp_projection_gb",
            "value_gb": round(LINEAR_TEMP_ESTIMATE_GB, 3),
            "evidence_class": "planning_estimate_only",
            "launch_authority": "none",
        },
        {
            "measure": "estimated_final_compact_min_gb",
            "value_gb": 80,
            "evidence_class": "planning_estimate_only",
            "launch_authority": "none",
        },
        {
            "measure": "estimated_final_compact_max_gb",
            "value_gb": 110,
            "evidence_class": "planning_estimate_only",
            "launch_authority": "none",
        },
        {
            "measure": "estimated_final_runtime_min_gb",
            "value_gb": 70,
            "evidence_class": "planning_estimate_only",
            "launch_authority": "none",
        },
        {
            "measure": "estimated_final_runtime_max_gb",
            "value_gb": 100,
            "evidence_class": "planning_estimate_only",
            "launch_authority": "none",
        },
    )
    resume_contract = {
        "status": "hold_not_approved",
        "resume_allowed": False,
        "abort_required_when": [
            "available_space_falls_below_declared_margin",
            "microbatch_bytes_per_partition_exceeds_approved_projection",
            "microbatch_runtime_exceeds_declared_wallclock_budget",
            "normal_and_strict_outputs_are_not_separate",
            "resume_state_or_completed_partition_evidence_is_ambiguous",
        ],
        "requirements_before_resume": [
            "approve_incremental_compaction_or_retained_work_strategy",
            "declare temporary_space_requirement_and margin",
            "declare bounded_microbatch_partition_count",
            "declare microbatch_wallclock_budget_and stop_condition",
            "validate resume state before and after microbatch",
        ],
        "asset_isolation": {
            "preserve_order4_asset_ids": True,
            "mix_with_closed_order2_order3_assets": False,
            "keep_normal_and_strict_separate": True,
        },
    }
    manifest = {
        "run_label": RUN_LABEL,
        "status": "hold_not_approved",
        "full_build_approved": False,
        "production_scoring_change_approved": False,
        "production_ranking_change_approved": False,
        "evidence_scope": "machine_readable_order4_build_readiness_only",
        "source_evidence_location": "DJ-MINI remote summary normalized into this portable local artifact",
        "raw_asset": {
            "asset_id": RAW_ASSET_ID,
            "scope": {"direction": "fwd", "ngram_order": 4, "dictionary_cuts": ["normal", "strict"]},
            "asset_status": "review_ready_candidate",
            "payload_validation_status": "pass",
            "completed_shards": RAW_COMPLETED_SHARDS,
            "payload_files": RAW_PAYLOAD_FILES,
            "aggregate_rows": RAW_ROW_COUNT,
            "manifest_reported_payload_bytes": RAW_PAYLOAD_BYTES,
            "retained_shard_directory_gb": RAW_RETAINED_GB,
        },
        "compact_canary": {
            "asset_id": CANARY_ASSET_ID,
            "validation_status": "pass",
            "rows_before_dedup": CANARY_ROW_COUNT,
            "rows_after_dedup": CANARY_ROW_COUNT,
            "duplicate_identities": 0,
            "compact_files_checked": 2,
        },
        "partial_full_compact_preparation": {
            "status": "partial_held",
            "completed_partitions": COMPLETED_PARTITIONS,
            "total_partitions": TOTAL_PARTITIONS,
            "completion_fraction": COMPLETED_PARTITIONS / TOTAL_PARTITIONS,
            "retained_work_gb": RETAINED_COMPACT_WORK_GB,
        },
        "estimate_interpretation": "planning estimates are not measurements and provide no launch authority",
        "resume_contract_file": f"{OUTPUT_DIR_REL}/abort_and_resume_contract.json",
    }
    _write_json(output_dir / "readiness_manifest.json", manifest)
    _write_json(output_dir / "abort_and_resume_contract.json", resume_contract)
    _write_csv(
        output_dir / "partition_summary_rows.csv",
        partition_rows,
        ("dictionary_cut", "completed_partitions", "total_partitions", "completion_fraction", "status"),
    )
    _write_csv(
        output_dir / "temporary_space_estimate_rows.csv",
        estimate_rows,
        ("measure", "value_gb", "evidence_class", "launch_authority"),
    )
    readout = "\n".join(
        (
            "# Order-4 Build Readiness Hold",
            "",
            "- status: `hold_not_approved`",
            "- full build approved: `false`",
            f"- validated raw rows: `{RAW_ROW_COUNT}`",
            f"- compact canary rows: `{CANARY_ROW_COUNT}`",
            f"- partial compact preparation: `{COMPLETED_PARTITIONS}/{TOTAL_PARTITIONS}` partitions",
            f"- retained partial work: `{RETAINED_COMPACT_WORK_GB} GB`",
            f"- naive linear temporary-space projection: `{LINEAR_TEMP_ESTIMATE_GB / 1000:.2f} TB`",
            "",
            "The projection is planning evidence only. Resume requires a separately approved",
            "bounded microbatch, space margin, stop condition, and retained-work strategy.",
        )
    )
    (output_dir / "readout.md").write_text(readout + "\n", encoding="utf-8")
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] completed_partitions={COMPLETED_PARTITIONS}/{TOTAL_PARTITIONS}")
    print(f"[{RUN_LABEL}] full_build_approved={manifest['full_build_approved']}")
    return manifest


def main() -> None:
    build_readiness_hold_evidence()


if __name__ == "__main__":
    main()
