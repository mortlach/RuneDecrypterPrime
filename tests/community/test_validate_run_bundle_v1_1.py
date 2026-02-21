from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.community import validate_run_bundle as vrb

pytestmark = pytest.mark.tier_a


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True))
            f.write("\n")


def _manifest_row(*, campaign_id: str, git_sha: str) -> dict:
    return {
        "campaign_id": campaign_id,
        "job_id": "job_valid_0001",
        "git_sha": git_sha,
        "text_fixture_id": "fixture_001",
        "period": 10,
        "columns": 3,
        "order": "col_then_sub",
        "profile_id": "baseline_resume_v1_1",
        "run_seed": 111,
        "replicate_idx": 0,
        "config_fingerprint": "abcdef12",
    }


def _result_row_from_manifest(manifest_row: dict, *, fastlm_present: bool) -> dict:
    return {
        "campaign_id": manifest_row["campaign_id"],
        "job_id": manifest_row["job_id"],
        "git_sha": manifest_row["git_sha"],
        "text_fixture_id": manifest_row["text_fixture_id"],
        "period": manifest_row["period"],
        "columns": manifest_row["columns"],
        "order": manifest_row["order"],
        "profile_id": manifest_row["profile_id"],
        "run_seed": manifest_row["run_seed"],
        "replicate_idx": manifest_row["replicate_idx"],
        "config_fingerprint": manifest_row["config_fingerprint"],
        "status": "unsolved",
        "stop_reason": "stage3_budget_exhausted",
        "best_match_ratio": 0.33,
        "best_stage": 3,
        "total_seconds": 12.3,
        "total_evals": 1234,
        "stage1_best_score": 0.1,
        "stage2_best_score": 0.2,
        "stage3_best_score": 0.3,
        "output_run_dir": "output/tools/benchmarks/example",
        "device": "cpu",
        "scoring_backend": "numpy",
        "fastlm_present": bool(fastlm_present),
    }


def _make_bundle(tmp_path: Path, *, fastlm_present: bool) -> Path:
    campaign_id = "community-test"
    git_sha = "7c346c2"
    bundle = tmp_path / "run_bundle"
    bundle.mkdir(parents=True, exist_ok=True)

    manifest_row = _manifest_row(campaign_id=campaign_id, git_sha=git_sha)
    result_row = _result_row_from_manifest(manifest_row, fastlm_present=fastlm_present)

    _write_json(
        bundle / "run_meta.json",
        {
            "runner_id": "tester",
            "campaign_id": campaign_id,
            "git_sha": git_sha,
            "campaign_mode": True,
            "autoskip_proven_disabled": True,
            "finished_at_utc": "2026-02-19T00:00:00+00:00",
        },
    )
    _write_json(
        bundle / "campaign_config_v1_1.json",
        {"campaign_spec_version": "v1.1", "campaign_id": campaign_id, "git_sha": git_sha, "caps": {"max_seconds_per_job": 10}},
    )
    _write_json(bundle / "profile_catalog_v1_1.json", {"catalog_version": "v1.1", "profiles": [{"profile_id": "baseline_resume_v1_1"}]})
    _write_jsonl(bundle / "shard_manifest.jsonl", [manifest_row])
    _write_jsonl(bundle / "results.jsonl", [result_row])
    _write_json(bundle / "setup_report.json", {"ok": True})
    _write_json(bundle / "preflight_report.json", {"ok": True})
    (bundle / "setup.log").write_text("ok\n", encoding="utf-8")
    (bundle / "preflight.log").write_text("ok\n", encoding="utf-8")
    (bundle / "run.log").write_text("ok\n", encoding="utf-8")
    return bundle


def test_validate_run_bundle_accepts_valid_bundle(tmp_path: Path):
    bundle = _make_bundle(tmp_path, fastlm_present=True)
    report = vrb.validate_run_bundle(
        run_bundle_path=bundle,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        expected_campaign_id="community-test",
        expected_git_sha="7c346c2",
    )
    assert report["ok"] is True
    assert report["errors"] == []


def test_validate_run_bundle_rejects_fastlm_false(tmp_path: Path):
    bundle = _make_bundle(tmp_path, fastlm_present=False)
    report = vrb.validate_run_bundle(
        run_bundle_path=bundle,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        expected_campaign_id="community-test",
        expected_git_sha="7c346c2",
    )
    assert report["ok"] is False
    assert any("fastlm_present must be true" in msg for msg in report["errors"])
