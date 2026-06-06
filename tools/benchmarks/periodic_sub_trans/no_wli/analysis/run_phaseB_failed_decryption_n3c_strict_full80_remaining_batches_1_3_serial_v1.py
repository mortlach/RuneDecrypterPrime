from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_strict_full80_bucket_common_v1 import (
    run_strict_bucket,
)


PHASE = "phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_serial_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
INTENDED_WALLCLOCK_BUDGET_SECONDS = 36_000.0
STOP_ON_FIRST_FAILURE = True
BATCHES = (
    {"batch_id": "remaining_batch_01", "remaining_offset": 0},
    {"batch_id": "remaining_batch_02", "remaining_offset": 80},
    {"batch_id": "remaining_batch_03", "remaining_offset": 160},
)
BUCKETS = (
    {"length_bucket": "8-9", "suffix": "8_9", "budget_seconds": 3_600.0, "reference_seconds": 2_263.453},
    {"length_bucket": "10-11", "suffix": "10_11", "budget_seconds": 7_200.0, "reference_seconds": 2_780.656},
    {"length_bucket": "12-14", "suffix": "12_14", "budget_seconds": 7_200.0, "reference_seconds": 2_160.546},
    {"length_bucket": "15-17", "suffix": "15_17", "budget_seconds": 7_200.0, "reference_seconds": 918.328},
    {"length_bucket": "18+", "suffix": "18_plus", "budget_seconds": 5_400.0, "reference_seconds": 779.703},
)
ESTIMATED_TOTAL_SECONDS = sum(bucket["reference_seconds"] for bucket in BUCKETS) * len(BATCHES)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(status: str, completed_jobs: list[dict[str, object]], started: float) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "status": status,
        "phase": PHASE,
        "updated_utc": utc_now(),
        "intended_wallclock_budget_seconds": INTENDED_WALLCLOCK_BUDGET_SECONDS,
        "estimated_total_seconds_from_strict_selected80_reference": ESTIMATED_TOTAL_SECONDS,
        "batch_count": len(BATCHES),
        "bucket_count_per_batch": len(BUCKETS),
        "planned_job_count": len(BATCHES) * len(BUCKETS),
        "completed_job_count": len(completed_jobs),
        "elapsed_seconds": time.monotonic() - started,
        "stop_on_first_failure": STOP_ON_FIRST_FAILURE,
        "completed_jobs": completed_jobs,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
    }
    (OUTPUT_DIR / "progress_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def run_serial() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed_jobs: list[dict[str, object]] = []
    print(f"[{PHASE}] started_utc={utc_now()}", flush=True)
    print(
        f"[{PHASE}] planned_batches={len(BATCHES)} planned_jobs={len(BATCHES) * len(BUCKETS)} "
        f"estimated_seconds={ESTIMATED_TOTAL_SECONDS:.1f} budget_seconds={INTENDED_WALLCLOCK_BUDGET_SECONDS:.1f}",
        flush=True,
    )
    write_status("running", completed_jobs, started)
    for batch in BATCHES:
        candidate_scope = f"strict_full80_{batch['batch_id']}_80_candidates_v1"
        for bucket in BUCKETS:
            elapsed = time.monotonic() - started
            if elapsed >= INTENDED_WALLCLOCK_BUDGET_SECONDS:
                print(f"[{PHASE}] wallclock_budget_reached elapsed_seconds={elapsed:.1f}", flush=True)
                write_status("stopped_wallclock_budget_reached", completed_jobs, started)
                return {"status": "stopped_wallclock_budget_reached", "completed_jobs": completed_jobs}
            phase = (
                "phaseB_failed_decryption_n3c_strict_full80_"
                f"{batch['batch_id']}_bucket_{bucket['suffix']}_query_evidence_v1"
            )
            print(
                f"[{PHASE}] launching batch={batch['batch_id']} bucket={bucket['length_bucket']} "
                f"phase={phase} elapsed_seconds={elapsed:.1f}",
                flush=True,
            )
            result = run_strict_bucket(
                str(bucket["length_bucket"]),
                phase,
                float(bucket["budget_seconds"]),
                candidate_scope=candidate_scope,
                candidate_selection_mode="remaining_by_trial_score_batch",
                candidate_remaining_offset=int(batch["remaining_offset"]),
            )
            completed = {
                "batch_id": batch["batch_id"],
                "length_bucket": bucket["length_bucket"],
                "phase": phase,
                "status": result["status"],
                "runtime_chunk_count": result["runtime_chunk_count"],
                "runtime_phrase_rows": result["runtime_phrase_rows"],
                "verified_hit_count": result["verified_hit_count"],
                "runtime_seconds": result["total_runtime_seconds_this_invocation"],
                "runtime_budget_pass": result["runtime_budget_pass"],
                "memory_budget_pass": result["memory_budget_pass"],
            }
            completed_jobs.append(completed)
            write_status("running", completed_jobs, started)
            if result["status"] != "bucket_n3c_query_complete" and STOP_ON_FIRST_FAILURE:
                write_status("stopped_failed_bucket", completed_jobs, started)
                return {"status": "stopped_failed_bucket", "completed_jobs": completed_jobs}
    write_status("complete", completed_jobs, started)
    print(f"[{PHASE}] complete elapsed_seconds={time.monotonic() - started:.1f}", flush=True)
    return {"status": "complete", "completed_jobs": completed_jobs}


if __name__ == "__main__":
    run_serial()
