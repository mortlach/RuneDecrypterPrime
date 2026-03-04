from __future__ import annotations

import json
import subprocess
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
    integrity_rows = read_jsonl(run_bundle / "results_integrity.jsonl")
    assert len(rows) == 1
    assert len(integrity_rows) == 1
    schema = _load_json(Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"))
    validator = Draft202012Validator(schema)
    validator.validate(rows[0])
    run_meta = _load_json(run_bundle / "run_meta.json")
    assert run_meta["results_integrity"]["row_count"] == 1


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


def test_format_job_cmd_for_log_redacts_absolute_paths(tmp_path: Path):
    repo_root = tmp_path
    helper_script = repo_root / "tools" / "benchmarks" / "community" / "_run_single_job.py"
    win_drive = "C" + ":"
    py_exe_abs = win_drive + "\\Python\\Python311\\python.exe"
    tmp_root_abs = win_drive + "\\Users\\alice\\AppData\\Local\\Temp\\community_job_abc"
    job_json_abs = tmp_root_abs + "\\job.json"
    job_out_abs = tmp_root_abs + "\\job_output.json"
    cmd = [
        py_exe_abs,
        str(helper_script),
        "--job-json",
        job_json_abs,
        "--campaign-config",
        str(repo_root / "tools" / "benchmarks" / "community" / "examples" / "campaign_config_v1_1.json"),
        "--profile-catalog",
        str(repo_root / "tools" / "benchmarks" / "community" / "profile_catalog_v1_1.json"),
        "--output-json",
        job_out_abs,
        "--repo-root",
        str(repo_root),
    ]
    rendered = rs._format_job_cmd_for_log(cmd=cmd, repo_root=repo_root, helper_script=helper_script)
    rendered_norm = rendered.replace("\\", "/")
    assert job_json_abs.replace("\\", "/") not in rendered_norm
    assert job_out_abs.replace("\\", "/") not in rendered_norm
    assert "<tmp_path>" in rendered_norm
    assert "tools/benchmarks/community/_run_single_job.py" in rendered_norm


def test_sanitize_log_text_redacts_absolute_paths(tmp_path: Path):
    repo_root = tmp_path
    win_drive = "C" + ":"
    win_abs_file = (
        "File "
        + win_drive
        + "\\Users\\alice\\OneDrive\\repo\\tools\\benchmarks\\community\\_run_single_job.py, line 10\n"
    )
    unix_abs_tmp = "/" + "Users/alice/tmp/community_job_abc/job.json\n"
    unix_user_prefix = "/" + "Users" + "/alice/"
    win_user_prefix = win_drive + "/" + "Users" + "/alice/"
    raw = (
        "Traceback:\n"
        + win_abs_file
        + "repo path "
        + str(repo_root / "tools" / "benchmarks" / "community" / "run_shard.py")
        + "\n"
        + "tmp "
        + unix_abs_tmp
    )
    safe = rs._sanitize_log_text(raw, repo_root=repo_root).replace("\\", "/")
    assert win_user_prefix not in safe
    assert unix_user_prefix not in safe
    assert "<abs_path>" in safe
    assert "./tools/benchmarks/community/run_shard.py" in safe


def test_run_job_with_helper_timeout_preserves_fastlm_detection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"))
    job = _manifest_row(campaign_config)
    campaign_config_path = tmp_path / "campaign_config.json"
    profile_catalog_path = tmp_path / "profile_catalog.json"
    _write_json(campaign_config_path, campaign_config)
    _write_json(profile_catalog_path, {})
    run_log_path = tmp_path / "run.log"

    monkeypatch.setattr(rs, "_detect_fastlm_available", lambda **kwargs: True)

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="helper", timeout=1.0)

    monkeypatch.setattr(rs.subprocess, "run", _timeout)

    row = rs._run_job_with_helper(
        job=job,
        repo_root=Path.cwd(),
        campaign_config_path=campaign_config_path,
        profile_catalog_path=profile_catalog_path,
        max_seconds_per_job=1.0,
        max_total_evals_per_job=None,
        run_log_path=run_log_path,
    )

    assert row["status"] == "unsolved"
    assert row["stop_reason"] == "time_cap_reached"
    assert row["fastlm_present"] is True


def test_run_shard_marks_identity_mismatch_as_invalid_config(tmp_path: Path):
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
        bad = _fake_result_row(kwargs["job"])
        bad["job_id"] = "job_other_9999"
        return bad

    meta = rs.run_shard_bundle(
        runner_config_path=runner_config_path,
        campaign_config_path=campaign_config_path,
        profile_catalog_path=profile_catalog_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        repo_root=Path.cwd(),
        run_job_fn=fake_run_job_fn,
    )
    run_bundle = Path(meta["run_bundle_path"])
    rows = read_jsonl(run_bundle / "results.jsonl")
    assert len(rows) == 1
    assert rows[0]["job_id"] == row["job_id"]
    assert rows[0]["status"] == "error"
    assert rows[0]["stop_reason"] == "invalid_config"
    run_log = (run_bundle / "run.log").read_text(encoding="utf-8")
    assert "ROW_IDENTITY_MISMATCH" in run_log


def test_run_shard_resume_rejects_duplicate_existing_job_ids(tmp_path: Path):
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"))
    profile_catalog = _load_json(Path("tools/benchmarks/community/profile_catalog_v1_1.json"))
    campaign_config_path = tmp_path / "campaign_config.json"
    profile_catalog_path = tmp_path / "profile_catalog.json"
    _write_json(campaign_config_path, campaign_config)
    _write_json(profile_catalog_path, profile_catalog)

    shard_path = tmp_path / "manifest_shard_00.jsonl"
    job = _manifest_row(campaign_config)
    shard_path.write_text(json.dumps(job) + "\n", encoding="utf-8")

    runner_config = {
        "runner_id": "tester",
        "shard_path": str(shard_path),
        "output_root": str(tmp_path / "output"),
        "resume": True,
        "max_jobs": None,
    }
    runner_config_path = tmp_path / "runner_config.json"
    _write_json(runner_config_path, runner_config)

    run_bundle = rs._build_run_bundle_dir(
        output_root=(tmp_path / "output").resolve(),
        campaign_id=str(campaign_config["campaign_id"]),
        runner_id="tester",
        shard_path=shard_path.resolve(),
    )
    run_bundle.mkdir(parents=True, exist_ok=True)
    row = _fake_result_row(job)
    (run_bundle / "results.jsonl").write_text(
        json.dumps(row, sort_keys=True) + "\n" + json.dumps(row, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate existing results job_id"):
        rs.run_shard_bundle(
            runner_config_path=runner_config_path,
            campaign_config_path=campaign_config_path,
            profile_catalog_path=profile_catalog_path,
            manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
            result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
            repo_root=Path.cwd(),
            run_job_fn=lambda **kwargs: _fake_result_row(kwargs["job"]),
        )


def test_run_shard_resume_rejects_existing_job_not_in_shard(tmp_path: Path):
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"))
    profile_catalog = _load_json(Path("tools/benchmarks/community/profile_catalog_v1_1.json"))
    campaign_config_path = tmp_path / "campaign_config.json"
    profile_catalog_path = tmp_path / "profile_catalog.json"
    _write_json(campaign_config_path, campaign_config)
    _write_json(profile_catalog_path, profile_catalog)

    shard_path = tmp_path / "manifest_shard_00.jsonl"
    job = _manifest_row(campaign_config)
    shard_path.write_text(json.dumps(job) + "\n", encoding="utf-8")

    runner_config = {
        "runner_id": "tester",
        "shard_path": str(shard_path),
        "output_root": str(tmp_path / "output"),
        "resume": True,
        "max_jobs": None,
    }
    runner_config_path = tmp_path / "runner_config.json"
    _write_json(runner_config_path, runner_config)

    run_bundle = rs._build_run_bundle_dir(
        output_root=(tmp_path / "output").resolve(),
        campaign_id=str(campaign_config["campaign_id"]),
        runner_id="tester",
        shard_path=shard_path.resolve(),
    )
    run_bundle.mkdir(parents=True, exist_ok=True)
    bad = _fake_result_row(job)
    bad["job_id"] = "job_not_in_manifest"
    (run_bundle / "results.jsonl").write_text(
        json.dumps(bad, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="job_id not in current shard"):
        rs.run_shard_bundle(
            runner_config_path=runner_config_path,
            campaign_config_path=campaign_config_path,
            profile_catalog_path=profile_catalog_path,
            manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
            result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
            repo_root=Path.cwd(),
            run_job_fn=lambda **kwargs: _fake_result_row(kwargs["job"]),
        )


def test_run_shard_resume_false_resets_run_log_and_rows(tmp_path: Path):
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
    run_bundle = Path(meta_1["run_bundle_path"])
    with (run_bundle / "run.log").open("a", encoding="utf-8", newline="\n") as f:
        f.write("OLD_LOG_MARKER\n")

    runner_config["resume"] = False
    _write_json(runner_config_path, runner_config)
    rs.run_shard_bundle(
        runner_config_path=runner_config_path,
        campaign_config_path=campaign_config_path,
        profile_catalog_path=profile_catalog_path,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        repo_root=Path.cwd(),
        run_job_fn=fake_run_job_fn,
    )

    rows = read_jsonl(run_bundle / "results.jsonl")
    assert len(rows) == 1
    run_log_path = run_bundle / "run.log"
    if run_log_path.exists():
        run_log = run_log_path.read_text(encoding="utf-8")
        assert "OLD_LOG_MARKER" not in run_log
    assert calls["n"] == 2
