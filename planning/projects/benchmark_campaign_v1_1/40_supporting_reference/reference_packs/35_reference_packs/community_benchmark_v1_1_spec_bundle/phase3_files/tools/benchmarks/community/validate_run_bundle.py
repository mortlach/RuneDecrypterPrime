#!/usr/bin/env python3
"""
Validate a run bundle consisting of a manifest and corresponding results.

This script loads a manifest (JSON lines) and a results file (JSON lines) and
performs consistency checks:

* Every result row must contain a job_id present in the manifest.
* No job_id appears more than once in the results.
* All mandatory fields defined by the v1.1 result schema are present.
* ``status`` values belong to the allowed set {solved, unsolved, stalled, error}.
* ``stop_reason`` values belong to the enumerated set defined by the spec.

The validator prints a summary to standard output indicating whether the run
bundle is valid and lists any errors encountered.  It returns a non‑zero
exit code on validation failure.

Usage::

    python validate_run_bundle.py \
        --manifest manifest_shard_000.jsonl \
        --results results_000.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Set, Tuple

# Status and stop reason enumerations must mirror those used in the runner
STATUS_VALUES = {"solved", "unsolved", "stalled", "error"}
STOP_REASONS = {
    "solved_threshold_met",
    "time_cap_reached",
    "eval_cap_reached",
    "stage1_budget_exhausted",
    "stage2_budget_exhausted",
    "stage3_budget_exhausted",
    "plateau_detected",
    "no_candidates_to_promote",
    "invalid_config",
    "missing_assets",
    "fastlm_unavailable",
    "exception_raised",
}

MANDATORY_RESULT_KEYS = {
    "job_id",
    "campaign_id",
    "campaign_seed",
    "commit",
    "period",
    "columns",
    "order",
    "status",
    "stop_reason",
    "best_match_ratio",
    "total_seconds",
    "num_evaluations",
}


def load_jsonl(path: str) -> List[Dict]:
    items: List[Dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def validate_run(manifest_jobs: List[Dict], results: List[Dict]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    manifest_ids: Set[str] = {job["job_id"] for job in manifest_jobs}
    seen_ids: Set[str] = set()
    for idx, row in enumerate(results):
        context = f"result line {idx + 1}"
        # Check mandatory keys
        missing_keys = MANDATORY_RESULT_KEYS - row.keys()
        if missing_keys:
            errors.append(f"{context}: missing keys {sorted(missing_keys)}")
        # Validate job_id presence in manifest
        job_id = row.get("job_id")
        if job_id and job_id not in manifest_ids:
            errors.append(f"{context}: job_id {job_id!r} not found in manifest")
        if job_id in seen_ids:
            errors.append(f"{context}: duplicate job_id {job_id!r} in results")
        seen_ids.add(job_id)
        # Validate status
        status = row.get("status")
        if status and status not in STATUS_VALUES:
            errors.append(f"{context}: invalid status {status!r}")
        # Validate stop_reason
        stop_reason = row.get("stop_reason")
        if stop_reason and stop_reason not in STOP_REASONS:
            errors.append(f"{context}: invalid stop_reason {stop_reason!r}")
    # Check for missing job_ids in results
    missing_in_results = manifest_ids - seen_ids
    if missing_in_results:
        errors.append(f"Missing {len(missing_in_results)} job_ids in results: {sorted(list(missing_in_results))[:10]}...")
    return (not errors, errors)


def parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a manifest/results bundle for the RDP community benchmark."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to the manifest shard (JSON lines).",
    )
    parser.add_argument(
        "--results",
        required=True,
        help="Path to the results file (JSON lines).",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    manifest_jobs = load_jsonl(args.manifest)
    results = load_jsonl(args.results)
    ok, errors = validate_run(manifest_jobs, results)
    if ok:
        print("VALID run bundle:", args.results)
        return 0
    print("INVALID run bundle:", args.results)
    for err in errors:
        print(" -", err)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())