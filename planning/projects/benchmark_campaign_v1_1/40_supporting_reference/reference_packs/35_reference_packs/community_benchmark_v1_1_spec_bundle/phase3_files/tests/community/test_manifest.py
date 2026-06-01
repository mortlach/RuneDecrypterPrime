"""
Tests for manifest generation utilities.

These tests verify that the manifest generator produces the expected number
of jobs and that job identifiers are deterministic across invocations with
the same seed and commit.  The tests import the module directly from the
phase3 implementation directory.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _import_generate_manifest_module():
    # Dynamically import the generate_manifest module from the phase3 path.
    module_path = Path(__file__).parents[2] / "tools" / "benchmarks" / "community"
    sys.path.insert(0, str(module_path))
    try:
        return importlib.import_module("generate_manifest")
    finally:
        sys.path.pop(0)


def test_manifest_job_count_and_determinism():
    gm = _import_generate_manifest_module()
    seed = "testseed"
    commit = "abcdef123"
    jobs1 = list(gm.generate_jobs(seed, commit))
    jobs2 = list(gm.generate_jobs(seed, commit))
    # 7 periods (7–13 inclusive) * 13 columns (1–13 inclusive) * 2 orders = 182
    assert len(jobs1) == 7 * 13 * 2
    assert len(jobs2) == len(jobs1)
    ids1 = [j["job_id"] for j in jobs1]
    ids2 = [j["job_id"] for j in jobs2]
    assert ids1 == ids2