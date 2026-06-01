"""
Tests for the manifest sharding utility.

These tests verify that sharding divides the input manifest into the requested
number of shards and preserves job order.  Since the manifest generator is
deterministic, we create a small synthetic manifest and use the sharder to
split it.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


def _import_shard_module():
    module_path = Path(__file__).parents[2] / "tools" / "benchmarks" / "community"
    sys.path.insert(0, str(module_path))
    try:
        return importlib.import_module("shard_manifest")
    finally:
        sys.path.pop(0)


def test_shard_splits(tmp_path):
    shard_module = _import_shard_module()
    # Build a synthetic manifest with 10 jobs
    jobs = [
        {
            "job_id": f"id{i}",
            "campaign_id": "camp",
            "campaign_seed": "seed",
            "commit": "abc",
            "period": 7,
            "columns": i,
            "order": "col_then_sub",
        }
        for i in range(10)
    ]
    manifest_path = tmp_path / "manifest.jsonl"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        for job in jobs:
            fh.write(json.dumps(job))
            fh.write("\n")
    out_dir = tmp_path / "shards"
    shard_module.write_shards(jobs, shard_count=3, out_dir=str(out_dir))
    # The sharder should create at most 3 files
    files = sorted(os.listdir(out_dir))
    assert len(files) <= 3
    # Reassemble jobs from shards and ensure they match the original order
    reassembled: list = []
    for fname in files:
        with open(out_dir / fname, "r", encoding="utf-8") as fh:
            for line in fh:
                reassembled.append(json.loads(line))
    assert [job["job_id"] for job in reassembled] == [job["job_id"] for job in jobs]