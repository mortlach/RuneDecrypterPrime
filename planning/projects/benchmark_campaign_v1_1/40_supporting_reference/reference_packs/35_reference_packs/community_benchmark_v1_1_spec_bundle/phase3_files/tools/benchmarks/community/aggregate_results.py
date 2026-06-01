#!/usr/bin/env python3
"""
Aggregate result rows into summary statistics and CSV reports.

This script reads a results JSONL file and produces a tabular summary grouped
by the cipher parameters (period, columns, order).  For each group it
computes the number of jobs, the count of each status, the mean
best_match_ratio and mean total_seconds.  The summary is written to a CSV
file which can be opened in a spreadsheet or further processed for
visualisation.

Usage::

    python aggregate_results.py \
        --results combined_results.jsonl \
        --output summary.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple


def load_results(path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def aggregate(rows: List[Dict]) -> List[Dict]:
    """Group results by (period, columns, order) and compute aggregates."""
    groups: Dict[Tuple[int, int, str], Dict] = defaultdict(lambda: {
        "total_jobs": 0,
        "solved": 0,
        "unsolved": 0,
        "stalled": 0,
        "error": 0,
        "sum_best_match_ratio": 0.0,
        "sum_total_seconds": 0.0,
    })
    for row in rows:
        key = (row["period"], row["columns"], row["order"])
        g = groups[key]
        g["total_jobs"] += 1
        status = row.get("status", "error")
        if status not in g:
            g[status] = 0
        g[status] += 1
        g["sum_best_match_ratio"] += float(row.get("best_match_ratio", 0.0))
        g["sum_total_seconds"] += float(row.get("total_seconds", 0.0))
    # Build summary list
    summaries: List[Dict] = []
    for (period, columns, order), g in sorted(groups.items()):
        total = g["total_jobs"]
        mean_ratio = g["sum_best_match_ratio"] / total if total else 0.0
        mean_seconds = g["sum_total_seconds"] / total if total else 0.0
        summaries.append({
            "period": period,
            "columns": columns,
            "order": order,
            "total_jobs": total,
            "solved": g.get("solved", 0),
            "unsolved": g.get("unsolved", 0),
            "stalled": g.get("stalled", 0),
            "error": g.get("error", 0),
            "mean_best_match_ratio": round(mean_ratio, 6),
            "mean_total_seconds": round(mean_seconds, 6),
        })
    return summaries


def write_csv(summaries: List[Dict], path: str) -> None:
    if not summaries:
        # Write an empty file with headers
        headers = [
            "period",
            "columns",
            "order",
            "total_jobs",
            "solved",
            "unsolved",
            "stalled",
            "error",
            "mean_best_match_ratio",
            "mean_total_seconds",
        ]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()
        return
    headers = list(summaries[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in summaries:
            writer.writerow(row)


def parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate result rows into a CSV summary grouped by cipher parameters."
    )
    parser.add_argument(
        "--results",
        "-r",
        required=True,
        help="Path to the results file (JSON lines).",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to write the summary CSV file.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    import sys

    args = parse_args(sys.argv[1:] if argv is None else argv)
    rows = load_results(args.results)
    summaries = aggregate(rows)
    write_csv(summaries, args.output)
    print(f"Wrote summary with {len(summaries)} groups to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())