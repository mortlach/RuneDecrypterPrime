#!/usr/bin/env python3
"""
Shard a benchmark manifest into smaller pieces.

The manifest generator produces a single JSON lines file containing every
campaign job.  For distributed execution or parallel processing, it is often
helpful to divide the manifest into shards of roughly equal size.  This
script accepts a manifest file and writes a series of shard files to an
output directory.  Jobs are preserved in the order provided by the input
manifest.

Usage::

    python shard_manifest.py \
        --input manifest.jsonl \
        --shards 4 \
        --output-dir shards

If the manifest contains ``N`` jobs and the number of shards is ``S``, each
shard will contain up to ``ceil(N/S)`` jobs.  Empty shards are not
created.  The output files are named ``manifest_shard_000.jsonl``,
``manifest_shard_001.jsonl`` and so on.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import List, Iterable


def load_manifest(path: str) -> List[dict]:
    """Load a JSON lines manifest into a list of dictionaries."""
    jobs: List[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            jobs.append(json.loads(line))
    return jobs


def write_shards(jobs: List[dict], shard_count: int, out_dir: str) -> None:
    """Write the provided jobs into ``shard_count`` shards in ``out_dir``."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    total = len(jobs)
    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    if total == 0:
        return
    # Determine the maximum number of jobs per shard.  This is the ceiling
    # division of total jobs by shard count.
    per_shard = math.ceil(total / shard_count)
    for idx in range(shard_count):
        start = idx * per_shard
        end = min(start + per_shard, total)
        shard_jobs = jobs[start:end]
        if not shard_jobs:
            continue
        filename = f"manifest_shard_{idx:03d}.jsonl"
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "w", encoding="utf-8") as fh:
            for job in shard_jobs:
                fh.write(json.dumps(job, separators=(",", ":")))
                fh.write("\n")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shard a benchmark manifest into N shards of roughly equal size."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to the input manifest (JSON lines).",
    )
    parser.add_argument(
        "--shards",
        "-n",
        type=int,
        required=True,
        help="Number of shards to produce.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        required=True,
        help="Directory into which shard files will be written.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or [])
    jobs = load_manifest(args.input)
    write_shards(jobs, args.shards, args.output_dir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))