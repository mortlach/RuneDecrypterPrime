from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.community import generate_manifest as gm
from tools.benchmarks.community import shard_manifest as sm
from tools.benchmarks.community._campaign_common import read_jsonl

pytestmark = pytest.mark.tier_a


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_for_tests(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "manifest.jsonl"
    gm.generate_manifest(
        campaign_config_path=Path("tools/benchmarks/community/examples/canary_campaign_config_v1_1.json"),
        profile_catalog_path=Path("tools/benchmarks/community/profile_catalog_v1_1.json"),
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        output_path=manifest_path,
        summary_output_path=tmp_path / "manifest.summary.json",
    )
    return manifest_path


def test_shard_manifest_has_no_missing_or_duplicate_jobs(tmp_path: Path):
    manifest_path = _manifest_for_tests(tmp_path)
    output_dir = tmp_path / "shards"
    summary = sm.shard_manifest_file(
        manifest_path=manifest_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        output_dir=output_dir,
        shard_count=3,
    )
    assert summary["manifest_rows"] > 0
    assert summary["missing_jobs_count"] == 0
    assert summary["duplicate_jobs_count"] == 0
    assert len(summary["shards"]) == 3

    manifest_rows = read_jsonl(manifest_path)
    manifest_job_ids = {row["job_id"] for row in manifest_rows}
    shard_job_ids: set[str] = set()
    for record in summary["shards"]:
        rows = read_jsonl(Path(record["path"]))
        for row in rows:
            assert row["job_id"] not in shard_job_ids
            shard_job_ids.add(row["job_id"])
    assert shard_job_ids == manifest_job_ids


def test_shard_manifest_is_deterministic(tmp_path: Path):
    manifest_path = _manifest_for_tests(tmp_path)
    output_dir_1 = tmp_path / "shards_1"
    output_dir_2 = tmp_path / "shards_2"

    summary_1 = sm.shard_manifest_file(
        manifest_path=manifest_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        output_dir=output_dir_1,
        shard_count=4,
    )
    summary_2 = sm.shard_manifest_file(
        manifest_path=manifest_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        output_dir=output_dir_2,
        shard_count=4,
    )

    for index in range(4):
        rows_1 = read_jsonl(Path(summary_1["shards"][index]["path"]))
        rows_2 = read_jsonl(Path(summary_2["shards"][index]["path"]))
        assert [row["job_id"] for row in rows_1] == [row["job_id"] for row in rows_2]


def test_shard_manifest_rejects_duplicate_job_ids(tmp_path: Path):
    manifest_path = tmp_path / "bad_manifest.jsonl"
    duplicate_row = {
        "campaign_id": "x",
        "job_id": "dupjob01",
        "git_sha": "abc1234",
        "text_fixture_id": "fixture_001",
        "period": 10,
        "columns": 3,
        "order": "col_then_sub",
        "profile_id": "baseline_resume_v1_1",
        "run_seed": 1,
        "replicate_idx": 0,
        "config_fingerprint": "abcdef12",
    }
    manifest_path.write_text(
        json.dumps(duplicate_row) + "\n" + json.dumps(duplicate_row) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate job_id"):
        sm.shard_manifest_file(
            manifest_path=manifest_path,
            manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
            output_dir=tmp_path / "shards",
            shard_count=2,
        )
