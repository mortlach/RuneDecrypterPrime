from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.benchmarks.community import run_shard as rs
from tools.benchmarks.community._campaign_common import read_jsonl

pytestmark = pytest.mark.tier_a


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _manifest_row(campaign_config: dict) -> dict:
    return {
        "campaign_id": campaign_config["campaign_id"],
        "job_id": "job_test_0001",
        "git_sha": campaign_config["git_sha"],
        "text_fixture_id": "fixture_001",
        "period": 10,
        "columns": 7,
        "order": "col_then_sub",
        "profile_id": "baseline_resume_v1_1",
        "run_seed": 111,
        "replicate_idx": 0,
        "config_fingerprint": "abcdef12",
    }


def _fake_result_row(job: dict) -> dict:
    return {
        "campaign_id": str(job["campaign_id"]),
        "job_id": str(job["job_id"]),
        "git_sha": str(job["git_sha"]),
        "text_fixture_id": str(job["text_fixture_id"]),
        "period": int(job["period"]),
        "columns": int(job["columns"]),
        "order": str(job["order"]),
        "profile_id": str(job["profile_id"]),
        "run_seed": int(job["run_seed"]),
        "replicate_idx": int(job["replicate_idx"]),
        "config_fingerprint": str(job["config_fingerprint"]),
        "status": "unsolved",
        "stop_reason": "stage3_budget_exhausted",
        "best_match_ratio": 0.2,
        "best_stage": 3,
        "total_seconds": 1.2,
        "total_evals": 123,
        "stage1_best_score": 0.1,
        "stage2_best_score": 0.2,
        "stage3_best_score": 0.3,
        "output_run_dir": "output/dummy",
        "device": "cpu",
        "scoring_backend": "numpy",
        "fastlm_present": True,
    }


def test_run_shard_writes_schema_valid_results(tmp_path: Path):
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"))
    profile_catalog = _load_json(Path("tools/benchmarks/community/profile_catalog_v1_1.json"))
    campaign_config_path = tmp_path / "campaign_config.json"
    profile_catalog_path = tmp_path / "profile_catalog.json"
    _write_json(campaign_config_path, campaign_config)
    _write_json(profile_catalog_path, profile_catalog)

    shard_path = tmp_path / "manifest_shard_00.jsonl"
    row = _manifest_row(campaign_config)
    shard_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    runner_config = {
        "runner_id": "tester",
        "shard_path": str(shard_path),
        "output_root": str(tmp_path / "output"),
        "resume": True,
        "max_jobs": None,
    }
    runner_config_path = tmp_path / "runner_config.json"
    _write_json(runner_config_path, runner_config)

    def fake_run_job_fn(**kwargs):
        return _fake_result_row(kwargs["job"])

    meta = rs.run_shard_bundle(
        runner_config_path=runner_config_path,
        campaign_config_path=campaign_config_path,
        profile_catalog_path=profile_catalog_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        repo_root=Path.cwd(),
        run_job_fn=fake_run_job_fn,
    )
    assert meta["campaign_mode"] is True
    assert meta["autoskip_proven_disabled"] is True
    assert meta["processed_jobs"] == 1
    assert meta["result_rows_written"] == 1

    run_bundle = Path(meta["run_bundle_path"])
    rows = read_jsonl(run_bundle / "results.jsonl")
    assert len(rows) == 1
    schema = _load_json(Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"))
    validator = Draft202012Validator(schema)
    validator.validate(rows[0])


def test_run_shard_resume_skip_only(tmp_path: Path):
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"))
    profile_catalog = _load_json(Path("tools/benchmarks/community/profile_catalog_v1_1.json"))
    campaign_config_path = tmp_path / "campaign_config.json"
    profile_catalog_path = tmp_path / "profile_catalog.json"
    _write_json(campaign_config_path, campaign_config)
    _write_json(profile_catalog_path, profile_catalog)

    shard_path = tmp_path / "manifest_shard_00.jsonl"
    row = _manifest_row(campaign_config)
    shard_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    runner_config = {
        "runner_id": "tester",
        "shard_path": str(shard_path),
        "output_root": str(tmp_path / "output"),
        "resume": True,
        "max_jobs": None,
    }
    runner_config_path = tmp_path / "runner_config.json"
    _write_json(runner_config_path, runner_config)

    calls = {"n": 0}

    def fake_run_job_fn(**kwargs):
        calls["n"] += 1
        return _fake_result_row(kwargs["job"])

    meta_1 = rs.run_shard_bundle(
        runner_config_path=runner_config_path,
        campaign_config_path=campaign_config_path,
        profile_catalog_path=profile_catalog_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        repo_root=Path.cwd(),
        run_job_fn=fake_run_job_fn,
    )
    meta_2 = rs.run_shard_bundle(
        runner_config_path=runner_config_path,
        campaign_config_path=campaign_config_path,
        profile_catalog_path=profile_catalog_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        repo_root=Path.cwd(),
        run_job_fn=fake_run_job_fn,
    )

    assert calls["n"] == 1
    assert meta_1["result_rows_written"] == 1
    assert meta_2["resume_skips"] == 1
    run_bundle = Path(meta_2["run_bundle_path"])
    run_log = (run_bundle / "run.log").read_text(encoding="utf-8")
    assert "RESUME_SKIP_ALREADY_RECORDED" in run_log
