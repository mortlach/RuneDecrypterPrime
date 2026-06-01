#!/usr/bin/env python3
"""
Execute a shard of community benchmark jobs.

Given a manifest shard (JSON lines), this script iterates over each job and
attempts to solve the corresponding periodic columnar cipher using the
RuneDecrypterPrime API.  Results are written to a JSON lines file.  Each
result row adheres to the v1.1 result schema, including mandatory keys for
status and stop_reason.  A minimal logging facility writes progress and
errors to stderr.

This implementation includes a stub solver that does not perform any real
decryption.  Instead, it returns an ``unsolved`` status with a
``missing_assets`` stop_reason.  The stub is provided as a safe default and
demonstrates the shape of the interface.  Integrators should replace the
``run_job`` function with a call into ``rune_decrypter_prime.api`` or another
appropriate entry point once the environment and assets are available.

Usage::

    python run_shard.py \
        --input manifest_shard_000.jsonl \
        --profile-catalog profile_catalog_v1_1.json \
        --output-results results.jsonl \
        [--resume-file resume.txt] \
        [--max-seconds-per-job 600] \
        [--max-evaluations-per-job 100000]

The runner maintains determinism by avoiding environment variables and
ensuring that jobs are executed and recorded in the order specified by the
input manifest.  If a resume file is provided, jobs whose job_id appears
within it will be skipped, and the skip will be logged.  This allows
interrupted runs to be resumed without repeating work.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set

# Status and stop reason enumerations aligned with the v1.1 spec
STATUS_SOLVED = "solved"
STATUS_UNSOLVED = "unsolved"
STATUS_STALLED = "stalled"
STATUS_ERROR = "error"

STOP_REASONS = {
    # Success termination conditions
    "solved_threshold_met",
    # Hard caps
    "time_cap_reached",
    "eval_cap_reached",
    # Stage budgets
    "stage1_budget_exhausted",
    "stage2_budget_exhausted",
    "stage3_budget_exhausted",
    # Plateau and candidate conditions
    "plateau_detected",
    "no_candidates_to_promote",
    # Infrastructure and configuration issues
    "invalid_config",
    "missing_assets",
    "fastlm_unavailable",
    # Generic exception catch‑all
    "exception_raised",
}


def load_manifest(path: str) -> List[Dict]:
    """Load a JSON lines manifest into a list of job dictionaries."""
    jobs: List[Dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            jobs.append(json.loads(line))
    return jobs


def load_profile_catalog(path: str) -> Dict[str, Dict]:
    """Load the profile catalogue into a dict keyed by profile name.

    The v1.1 specification defines a fixed set of scoring profiles for the
    periodic substitution + columnar cipher problem.  The catalogue is
    represented as a JSON object mapping profile names to configuration
    dictionaries.  This runner looks up the appropriate profile for each job
    based on the job parameters.  Should the spec mandate per‑job profile
    selection logic, that logic can be implemented here.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Profile catalogue at {path} must be a JSON object")
    return data


def read_resume_file(path: str) -> Set[str]:
    """Read a newline‑separated file of job_ids to skip."""
    job_ids: Set[str] = set()
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                job_ids.add(line)
    return job_ids


def run_job_stub(job: Dict, profile_catalog: Dict[str, Dict], max_seconds: int, max_evals: int) -> Dict:
    """Fallback solver implementation used when the real solver is unavailable.

    This stub returns a result row marked as unsolved with a stop_reason of
    ``missing_assets``.  It serves as a placeholder and makes the runner
    deterministic under CPU‑only assumptions.  Once the assets and solver are
    integrated, this function should be replaced with one that calls
    ``rune_decrypter_prime.api.run`` or similar and interprets its output to
    populate the fields below.
    """
    start_time = time.perf_counter()
    # In a real implementation, here we would construct the cipher and call
    # into the solving API, enforcing the time and evaluation caps.  For the
    # prototype we simply simulate negligible work and return default values.
    time.sleep(0.0)  # explicit no‑op to emphasise time measurement
    elapsed = time.perf_counter() - start_time
    return {
        "job_id": job["job_id"],
        "campaign_id": job["campaign_id"],
        "campaign_seed": job["campaign_seed"],
        "commit": job["commit"],
        "period": job["period"],
        "columns": job["columns"],
        "order": job["order"],
        "status": STATUS_UNSOLVED,
        "stop_reason": "missing_assets",
        "best_match_ratio": 0.0,
        "total_seconds": elapsed,
        "num_evaluations": 0,
    }


def run_job(job: Dict, profile_catalog: Dict[str, Dict], max_seconds: int, max_evals: int) -> Dict:
    """Dispatch to either the real solver or the stub.

    This thin wrapper exists so that solver integration can be slotted in
    without affecting the runner structure.  Replace the call to
    ``run_job_stub`` with a call into the real solving API once available.
    """
    # In the absence of a real solver, always call the stub.
    return run_job_stub(job, profile_catalog, max_seconds, max_evals)


def write_results(results: List[Dict], path: str) -> None:
    """Write result rows to a JSON lines file."""
    with open(path, "w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row, separators=(",", ":")))
            fh.write("\n")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a shard of RDP community benchmark jobs."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to the manifest shard (JSON lines).",
    )
    parser.add_argument(
        "--profile-catalog",
        "-p",
        required=True,
        help="Path to the profile catalogue JSON file.",
    )
    parser.add_argument(
        "--output-results",
        "-o",
        required=True,
        help="Path to write the results JSON lines file.",
    )
    parser.add_argument(
        "--resume-file",
        "-r",
        help="Path to a file containing job_ids to skip.  One per line.",
    )
    parser.add_argument(
        "--max-seconds-per-job",
        type=int,
        default=600,
        help="Maximum wall‑clock seconds allowed per job (default: 600).",
    )
    parser.add_argument(
        "--max-evaluations-per-job",
        type=int,
        default=100000,
        help="Maximum number of cipher evaluations per job (default: 100000).",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or [])
    # Configure minimal logging to stderr
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Load manifest and profile catalogue
    jobs = load_manifest(args.input)
    profile_catalog = load_profile_catalog(args.profile_catalog)
    skipped: Set[str] = set()
    if args.resume_file:
        skipped = read_resume_file(args.resume_file)
        logging.info(f"Resuming: {len(skipped)} job_ids will be skipped")

    results: List[Dict] = []
    total_jobs = len(jobs)
    processed = 0
    start_ts = datetime.utcnow().isoformat() + "Z"
    for job in jobs:
        if job["job_id"] in skipped:
            logging.info(f"Skipping job {job['job_id']} due to resume")
            continue
        processed += 1
        logging.info(
            f"Running job {processed}/{total_jobs}: period={job['period']}, columns={job['columns']}, order={job['order']}"
        )
        try:
            result = run_job(job, profile_catalog, args.max_seconds_per_job, args.max_evaluations_per_job)
        except Exception as exc:  # catch all unexpected errors
            logging.exception(f"Exception raised while running job {job['job_id']}")
            # Build an error result row
            result = {
                "job_id": job["job_id"],
                "campaign_id": job["campaign_id"],
                "campaign_seed": job["campaign_seed"],
                "commit": job["commit"],
                "period": job["period"],
                "columns": job["columns"],
                "order": job["order"],
                "status": STATUS_ERROR,
                "stop_reason": "exception_raised",
                "best_match_ratio": 0.0,
                "total_seconds": 0.0,
                "num_evaluations": 0,
                "error_message": str(exc),
            }
        results.append(result)

    # Write results file
    write_results(results, args.output_results)
    end_ts = datetime.utcnow().isoformat() + "Z"
    # Write a meta file summarising run statistics next to the results file
    meta_path = os.path.splitext(args.output_results)[0] + "_meta.json"
    summary = {
        "input_manifest": args.input,
        "results_file": args.output_results,
        "start_utc": start_ts,
        "end_utc": end_ts,
        "total_jobs": total_jobs,
        "processed_jobs": processed,
        "skipped_jobs": len(skipped),
        "status_counts": {},
    }
    # compute status counts
    counts: Dict[str, int] = {}
    for row in results:
        status = row["status"]
        counts[status] = counts.get(status, 0) + 1
    summary["status_counts"] = counts
    with open(meta_path, "w", encoding="utf-8") as meta_fh:
        json.dump(summary, meta_fh, indent=2)
    logging.info(f"Completed run: processed {processed} jobs, wrote results to {args.output_results}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))