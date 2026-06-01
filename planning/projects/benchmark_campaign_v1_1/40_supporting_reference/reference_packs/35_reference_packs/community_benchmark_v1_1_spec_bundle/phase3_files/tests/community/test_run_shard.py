"""
Tests for the shard runner prototype.

These tests exercise the stub runner to ensure that it reads a manifest shard,
loads a profile catalogue and produces a results file and meta summary.  The
stub always returns an ``unsolved`` status with ``missing_assets`` stop
reason, so the tests verify that these values appear in the output and that
the number of rows matches the number of jobs processed.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


def _import_run_module():
    module_path = Path(__file__).parents[2] / "tools" / "benchmarks" / "community"
    sys.path.insert(0, str(module_path))
    try:
        return importlib.import_module("run_shard")
    finally:
        sys.path.pop(0)


def test_run_shard_stub_creates_results(tmp_path):
    run_module = _import_run_module()
    # Create a small manifest with two jobs
    jobs = [
        {
            "job_id": f"id{i}",
            "campaign_id": "camp",
            "campaign_seed": "seed",
            "commit": "abc",
            "period": 7,
            "columns": i + 1,
            "order": "col_then_sub",
        }
        for i in range(2)
    ]
    manifest_path = tmp_path / "manifest_shard.jsonl"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        for job in jobs:
            fh.write(json.dumps(job))
            fh.write("\n")
    # Dummy profile catalogue
    profile_catalog_path = tmp_path / "profile_catalog.json"
    with open(profile_catalog_path, "w", encoding="utf-8") as fh:
        json.dump({}, fh)
    # Output file
    results_path = tmp_path / "results.jsonl"
    # Invoke runner main
    run_module.main([
        "--input",
        str(manifest_path),
        "--profile-catalog",
        str(profile_catalog_path),
        "--output-results",
        str(results_path),
        "--max-seconds-per-job",
        "1",
        "--max-evaluations-per-job",
        "10",
    ])
    # Check results file exists
    assert results_path.exists()
    rows = [json.loads(line) for line in open(results_path, "r", encoding="utf-8")]  # type: ignore
    assert len(rows) == len(jobs)
    for row in rows:
        assert row["status"] == "unsolved"
        assert row["stop_reason"] == "missing_assets"
    # Check meta file exists
    meta_path = results_path.with_name(results_path.stem + "_meta.json")
    assert meta_path.exists()
    meta = json.load(open(meta_path, "r", encoding="utf-8"))  # type: ignore
    assert meta["processed_jobs"] == len(jobs)