from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.benchmarks.community import aggregate_results as ar
from tools.benchmarks.community import combine_results as cr
from tools.benchmarks.community._campaign_common import (
    INTEGRITY_CHAIN_GENESIS,
    INTEGRITY_CHAIN_HASH,
    INTEGRITY_CHAIN_VERSION,
    build_results_integrity_rows,
    read_jsonl,
)

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


def _manifest_row(*, campaign_id: str, git_sha: str, job_id: str, period: int, columns: int, order: str, profile_id: str) -> dict:
    return {
        "campaign_id": campaign_id,
        "job_id": job_id,
        "git_sha": git_sha,
        "text_fixture_id": "fixture_001",
        "period": period,
        "columns": columns,
        "order": order,
        "profile_id": profile_id,
        "run_seed": 111,
        "replicate_idx": 0,
        "config_fingerprint": "abcdef12",
    }


def _result_row(
    manifest_row: dict,
    *,
    status: str,
    stop_reason: str,
    best_match_ratio: float,
    total_seconds: float,
    stage1_best_score: float,
) -> dict:
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
        "status": status,
        "stop_reason": stop_reason,
        "best_match_ratio": best_match_ratio,
        "best_stage": 3,
        "total_seconds": total_seconds,
        "total_evals": 1000,
        "stage1_best_score": stage1_best_score,
        "stage2_best_score": 0.2,
        "stage3_best_score": 0.3,
        "output_run_dir": "output/example",
        "device": "cpu",
        "scoring_backend": "numpy",
        "fastlm_present": True,
    }


def _make_bundle(
    root: Path,
    *,
    name: str,
    campaign_id: str,
    git_sha: str,
    runner_id: str,
    finished_at_utc: str,
    manifest_rows: list[dict],
    result_rows: list[dict],
) -> Path:
    bundle = root / name
    bundle.mkdir(parents=True, exist_ok=True)
    integrity_rows, final_chain_hash = build_results_integrity_rows(result_rows)
    _write_json(
        bundle / "run_meta.json",
        {
            "runner_id": runner_id,
            "campaign_id": campaign_id,
            "git_sha": git_sha,
            "campaign_mode": True,
            "autoskip_proven_disabled": True,
            "results_integrity": {
                "integrity_version": INTEGRITY_CHAIN_VERSION,
                "hash_algorithm": INTEGRITY_CHAIN_HASH,
                "genesis_hash": INTEGRITY_CHAIN_GENESIS,
                "row_count": len(result_rows),
                "final_chain_hash": final_chain_hash,
            },
            "finished_at_utc": finished_at_utc,
        },
    )
    _write_json(
        bundle / "campaign_config_v1_1.json",
        {"campaign_spec_version": "v1.1", "campaign_id": campaign_id, "git_sha": git_sha, "caps": {"max_seconds_per_job": 10}},
    )
    _write_json(bundle / "profile_catalog_v1_1.json", {"catalog_version": "v1.1", "profiles": [{"profile_id": "baseline_resume_v1_1"}]})
    _write_jsonl(bundle / "shard_manifest.jsonl", manifest_rows)
    _write_jsonl(bundle / "results.jsonl", result_rows)
    _write_jsonl(bundle / "results_integrity.jsonl", integrity_rows)
    _write_json(bundle / "setup_report.json", {"ok": True})
    _write_json(bundle / "preflight_report.json", {"ok": True})
    (bundle / "setup.log").write_text("ok\n", encoding="utf-8")
    (bundle / "preflight.log").write_text("ok\n", encoding="utf-8")
    (bundle / "run.log").write_text("ok\n", encoding="utf-8")
    return bundle


def test_combine_and_aggregate_outputs(tmp_path: Path):
    campaign_id = "community-test"
    git_sha = "7c346c2"
    job_1 = _manifest_row(
        campaign_id=campaign_id,
        git_sha=git_sha,
        job_id="job_valid_0001",
        period=10,
        columns=3,
        order="col_then_sub",
        profile_id="baseline_resume_v1_1",
    )
    job_2 = _manifest_row(
        campaign_id=campaign_id,
        git_sha=git_sha,
        job_id="job_valid_0002",
        period=13,
        columns=7,
        order="sub_then_col",
        profile_id="stage3_fullband_basin_v1_1",
    )
    manifest_rows = [job_1, job_2]

    bundle_b = _make_bundle(
        tmp_path,
        name="run_bundle_b",
        campaign_id=campaign_id,
        git_sha=git_sha,
        runner_id="runner_b",
        finished_at_utc="2026-02-19T00:10:00+00:00",
        manifest_rows=manifest_rows,
        result_rows=[
            _result_row(
                job_1,
                status="unsolved",
                stop_reason="stage3_budget_exhausted",
                best_match_ratio=0.40,
                total_seconds=20.0,
                stage1_best_score=0.11,
            ),
            _result_row(
                job_2,
                status="solved",
                stop_reason="solved_threshold_met",
                best_match_ratio=0.95,
                total_seconds=5.0,
                stage1_best_score=0.11,
            ),
        ],
    )
    bundle_a = _make_bundle(
        tmp_path,
        name="run_bundle_a",
        campaign_id=campaign_id,
        git_sha=git_sha,
        runner_id="runner_a",
        finished_at_utc="2026-02-19T00:20:00+00:00",
        manifest_rows=manifest_rows,
        result_rows=[
            _result_row(
                job_1,
                status="solved",
                stop_reason="solved_threshold_met",
                best_match_ratio=0.91,
                total_seconds=60.0,
                stage1_best_score=0.77,
            ),
            _result_row(
                job_2,
                status="solved",
                stop_reason="solved_threshold_met",
                best_match_ratio=0.95,
                total_seconds=5.0,
                stage1_best_score=0.77,
            ),
        ],
    )

    combine_out = tmp_path / "combine_out"
    combine_report = cr.combine_run_bundles(
        run_bundle_paths=[bundle_b, bundle_a],
        output_dir=combine_out,
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        result_schema_path=Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        expected_campaign_id=campaign_id,
        expected_git_sha=git_sha,
    )
    assert combine_report["combined_rows"] == 2
    assert combine_report["collision_rows"] == 2

    combined_rows = read_jsonl(combine_out / "combined_results.jsonl")
    assert len(combined_rows) == 2
    by_job = {row["job_id"]: row for row in combined_rows}
    assert by_job["job_valid_0001"]["status"] == "solved"  # solved beats unsolved
    assert by_job["job_valid_0002"]["stage1_best_score"] == pytest.approx(0.77)  # tie -> runner_id runner_a

    agg_out = tmp_path / "agg_out"
    agg_report = ar.aggregate_results(
        combined_results_path=combine_out / "combined_results.jsonl",
        output_dir=agg_out,
    )
    assert agg_report["input_rows"] == 2
    for expected in (
        "summary_by_cell.csv",
        "summary_by_profile.csv",
        "solve_rate_heatmap_order_col_then_sub.csv",
        "solve_rate_heatmap_order_sub_then_col.csv",
        "stop_reason_counts_by_cell.csv",
        "stop_reason_counts_by_profile.csv",
    ):
        assert (agg_out / expected).exists()

    with (agg_out / "summary_by_profile.csv").open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert {row["profile_id"] for row in rows} == {"baseline_resume_v1_1", "stage3_fullband_basin_v1_1"}

    with (agg_out / "solve_rate_heatmap_order_col_then_sub.csv").open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    p10_row = next(row for row in rows if int(row["period"]) == 10)
    assert p10_row["c3"] == "1.0"
