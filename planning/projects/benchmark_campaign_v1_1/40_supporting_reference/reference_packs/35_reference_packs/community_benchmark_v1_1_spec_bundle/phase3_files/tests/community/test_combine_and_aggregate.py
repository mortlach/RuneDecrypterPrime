"""
Tests for combining and aggregating results.

The combine script deduplicates rows by job_id, prioritising according to
status, best_match_ratio and total_seconds.  The aggregate script then
summarises the combined results by (period, columns, order).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


def _import_combine_module():
    module_path = Path(__file__).parents[2] / "tools" / "benchmarks" / "community"
    sys.path.insert(0, str(module_path))
    try:
        return importlib.import_module("combine_results")
    finally:
        sys.path.pop(0)


def _import_aggregate_module():
    module_path = Path(__file__).parents[2] / "tools" / "benchmarks" / "community"
    sys.path.insert(0, str(module_path))
    try:
        return importlib.import_module("aggregate_results")
    finally:
        sys.path.pop(0)


def test_combine_deduplicates_and_prefers_better():
    combine_module = _import_combine_module()
    # Create two rows for the same job: one solved with lower ratio, one unsolved with higher ratio
    job_id = "j123"
    row_a = {
        "job_id": job_id,
        "campaign_id": "camp",
        "campaign_seed": "seed",
        "commit": "abc",
        "period": 7,
        "columns": 3,
        "order": "col_then_sub",
        "status": "unsolved",
        "stop_reason": "missing_assets",
        "best_match_ratio": 0.3,
        "total_seconds": 10.0,
        "num_evaluations": 0,
    }
    row_b = {
        **row_a,
        "status": "solved",
        "stop_reason": "solved_threshold_met",
        "best_match_ratio": 0.2,
        "total_seconds": 5.0,
    }
    # solved should win despite lower ratio
    best, _ = combine_module.combine([])
    # Without any input there should be no rows
    assert best == {}
    best, _ = combine_module.combine([])
    # Combine with duplicates from two files
    path1 = "dummy1.jsonl"
    path2 = "dummy2.jsonl"
    # Write temporary files
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / path1
        p2 = Path(td) / path2
        p1.write_text(json.dumps(row_a) + "\n", encoding="utf-8")
        p2.write_text(json.dumps(row_b) + "\n", encoding="utf-8")
        merged, counts = combine_module.combine([str(p1), str(p2)])
        assert list(merged.keys()) == [job_id]
        # row_b should be chosen as it has higher status precedence
        assert merged[job_id]["status"] == "solved"
        assert merged[job_id]["total_seconds"] == 5.0


def test_aggregate_groups_and_computes_means(tmp_path):
    aggregate_module = _import_aggregate_module()
    # Create a results file with multiple jobs in two groups
    rows = [
        {
            "job_id": f"j{i}",
            "campaign_id": "camp",
            "campaign_seed": "seed",
            "commit": "abc",
            "period": 7,
            "columns": 2,
            "order": "col_then_sub",
            "status": "solved" if i % 2 == 0 else "unsolved",
            "stop_reason": "solved_threshold_met" if i % 2 == 0 else "missing_assets",
            "best_match_ratio": 0.5 + 0.1 * i,
            "total_seconds": i,
            "num_evaluations": 10,
        }
        for i in range(4)
    ] + [
        {
            "job_id": "k1",
            "campaign_id": "camp",
            "campaign_seed": "seed",
            "commit": "abc",
            "period": 8,
            "columns": 3,
            "order": "sub_then_col",
            "status": "error",
            "stop_reason": "exception_raised",
            "best_match_ratio": 0.0,
            "total_seconds": 1.0,
            "num_evaluations": 0,
        }
    ]
    results_path = tmp_path / "results.jsonl"
    with open(results_path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row))
            fh.write("\n")
    # Aggregate and write to csv
    summary = aggregate_module.aggregate(rows)
    # There should be two groups
    assert len(summary) == 2
    # Find group for period=7, columns=2, order=col_then_sub
    group = next(g for g in summary if g["period"] == 7 and g["columns"] == 2)
    assert group["total_jobs"] == 4
    assert group["solved"] == 2
    assert group["unsolved"] == 2
    # Mean calculations
    expected_mean_ratio = sum(0.5 + 0.1 * i for i in range(4)) / 4
    assert abs(group["mean_best_match_ratio"] - round(expected_mean_ratio, 6)) < 1e-9