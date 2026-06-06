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


PHASE = "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_03_tail_serial_v1"
OUTPUT_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    / "phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_serial_v1"
)
INTENDED_WALLCLOCK_BUDGET_SECONDS = 7_200.0
BATCH_ID = "remaining_batch_03"
CANDIDATE_SCOPE = "strict_full80_remaining_batch_03_80_candidates_v1"
CANDIDATE_REMAINING_OFFSET = 160
BUCKETS = (
    {"length_bucket": "15-17", "suffix": "15_17", "budget_seconds": 7_200.0},
    {"length_bucket": "18+", "suffix": "18_plus", "budget_seconds": 5_400.0},
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(status: str, completed_jobs: list[dict[str, object]], started: float) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tail_progress_manifest.json").write_text(json.dumps({
        "status": status,
        "phase": PHASE,
        "updated_utc": utc_now(),
        "intended_wallclock_budget_seconds": INTENDED_WALLCLOCK_BUDGET_SECONDS,
        "planned_job_count": len(BUCKETS),
        "completed_job_count": len(completed_jobs),
        "elapsed_seconds": time.monotonic() - started,
        "completed_jobs": completed_jobs,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
    }, indent=2) + "\n", encoding="utf-8")


def run_tail() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed_jobs: list[dict[str, object]] = []
    print(f"[{PHASE}] started_utc={utc_now()}", flush=True)
    print(
        f"[{PHASE}] planned_batch={BATCH_ID} planned_jobs={len(BUCKETS)} "
        f"budget_seconds={INTENDED_WALLCLOCK_BUDGET_SECONDS:.1f}",
        flush=True,
    )
    write_status("running", completed_jobs, started)
    for bucket in BUCKETS:
        elapsed = time.monotonic() - started
        if elapsed >= INTENDED_WALLCLOCK_BUDGET_SECONDS:
            write_status("stopped_wallclock_budget_reached", completed_jobs, started)
            return {"status": "stopped_wallclock_budget_reached", "completed_jobs": completed_jobs}
        phase = (
            "phaseB_failed_decryption_n3c_strict_full80_"
            f"{BATCH_ID}_bucket_{bucket['suffix']}_query_evidence_v1"
        )
        print(
            f"[{PHASE}] launching batch={BATCH_ID} bucket={bucket['length_bucket']} "
            f"phase={phase} elapsed_seconds={elapsed:.1f}",
            flush=True,
        )
        result = run_strict_bucket(
            str(bucket["length_bucket"]),
            phase,
            float(bucket["budget_seconds"]),
            candidate_scope=CANDIDATE_SCOPE,
            candidate_selection_mode="remaining_by_trial_score_batch",
            candidate_remaining_offset=CANDIDATE_REMAINING_OFFSET,
        )
        completed_jobs.append({
            "batch_id": BATCH_ID,
            "length_bucket": bucket["length_bucket"],
            "phase": phase,
            "status": result["status"],
            "runtime_chunk_count": result["runtime_chunk_count"],
            "runtime_phrase_rows": result["runtime_phrase_rows"],
            "verified_hit_count": result["verified_hit_count"],
            "runtime_seconds": result["total_runtime_seconds_this_invocation"],
            "runtime_budget_pass": result["runtime_budget_pass"],
            "memory_budget_pass": result["memory_budget_pass"],
        })
        write_status("running", completed_jobs, started)
        if result["status"] != "bucket_n3c_query_complete":
            write_status("stopped_failed_bucket", completed_jobs, started)
            return {"status": "stopped_failed_bucket", "completed_jobs": completed_jobs}
    write_status("complete", completed_jobs, started)
    print(f"[{PHASE}] complete elapsed_seconds={time.monotonic() - started:.1f}", flush=True)
    return {"status": "complete", "completed_jobs": completed_jobs}


if __name__ == "__main__":
    run_tail()
