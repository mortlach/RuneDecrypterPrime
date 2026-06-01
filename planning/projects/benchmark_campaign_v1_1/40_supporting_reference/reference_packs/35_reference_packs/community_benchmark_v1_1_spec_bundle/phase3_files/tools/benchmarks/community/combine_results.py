#!/usr/bin/env python3
"""
Combine multiple results JSONL files into a single deduplicated file.

In large community campaigns, shards may be run independently and yield
overlapping results files.  This script merges a set of result files by
job_id.  When duplicate entries exist for the same job, the record with the
highest status precedence, highest best_match_ratio and lowest total_seconds
is selected.  Status precedence follows the order ``solved`` > ``unsolved`` >
``stalled`` > ``error``.  If all compared fields are equal, the job_id
comparison provides a deterministic tie break.

The script writes a combined results file (JSON lines) and prints a summary
of how many unique jobs were produced and how many duplicates were merged.

Usage::

    python combine_results.py \
        --results shard1_results.jsonl \
        --results shard2_results.jsonl \
        --output combined_results.jsonl
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, Iterable, List, Tuple

STATUS_PRECEDENCE = {
    "solved": 3,
    "unsolved": 2,
    "stalled": 1,
    "error": 0,
}


def load_results(path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def choose_better(a: Dict, b: Dict) -> Dict:
    """Return the better of two result rows according to tie‑break rules."""
    # Compare status precedence
    ap = STATUS_PRECEDENCE.get(a.get("status", "error"), 0)
    bp = STATUS_PRECEDENCE.get(b.get("status", "error"), 0)
    if ap != bp:
        return a if ap > bp else b
    # Compare best_match_ratio (higher is better)
    abr = a.get("best_match_ratio", 0.0)
    bbr = b.get("best_match_ratio", 0.0)
    if abr != bbr:
        return a if abr > bbr else b
    # Compare total_seconds (lower is better)
    ats = a.get("total_seconds", float("inf"))
    bts = b.get("total_seconds", float("inf"))
    if ats != bts:
        return a if ats < bts else b
    # Fallback deterministic tie break: lexicographic job_id
    return a if (a.get("job_id", "") < b.get("job_id", "")) else b


def combine(result_paths: List[str]) -> Tuple[Dict[str, Dict], Dict[str, int]]:
    best: Dict[str, Dict] = {}
    source_counts: Dict[str, int] = {}
    for path in result_paths:
        rows = load_results(path)
        source_counts[path] = len(rows)
        for row in rows:
            job_id = row.get("job_id")
            if not job_id:
                continue
            if job_id not in best:
                best[job_id] = row
            else:
                best[job_id] = choose_better(best[job_id], row)
    return best, source_counts


def write_results(rows: Dict[str, Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for job_id in sorted(rows.keys()):
            fh.write(json.dumps(rows[job_id], separators=(",", ":")))
            fh.write("\n")


def parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine multiple results files into one, deduplicating by job_id."
    )
    parser.add_argument(
        "--results",
        "-r",
        action="append",
        required=True,
        help="Path to a results file (JSON lines).  May be specified multiple times.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to write the combined results file.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    import sys

    args = parse_args(sys.argv[1:] if argv is None else argv)
    best, source_counts = combine(args.results)
    write_results(best, args.output)
    total_sources = sum(source_counts.values())
    duplicates = total_sources - len(best)
    print(
        f"Combined {len(args.results)} files containing {total_sources} rows into {len(best)} unique jobs."
    )
    print(f"Merged and discarded {duplicates} duplicate rows.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())