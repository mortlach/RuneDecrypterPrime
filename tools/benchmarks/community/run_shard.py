from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import load_json, read_jsonl, write_json
from tools.benchmarks.community.config import load_profile_catalog_from_dict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN_CONFIG = REPO_ROOT / "tools" / "benchmarks" / "community" / "examples" / "campaign_config_v1_1.json"
DEFAULT_PROFILE_CATALOG = REPO_ROOT / "tools" / "benchmarks" / "community" / "profile_catalog_v1_1.json"
DEFAULT_MANIFEST_SCHEMA = REPO_ROOT / "tools" / "benchmarks" / "community" / "schemas" / "manifest_schema_v1_1.json"
DEFAULT_RESULT_SCHEMA = REPO_ROOT / "tools" / "benchmarks" / "community" / "schemas" / "result_schema_v1_1.json"
HELPER_SCRIPT = REPO_ROOT / "tools" / "benchmarks" / "community" / "_run_single_job.py"

STOP_REASON_VALUES = {
    "solved_threshold_met",
    "time_cap_reached",
    "eval_cap_reached",
    "stage1_budget_exhausted",
    "stage2_budget_exhausted",
    "stage3_budget_exhausted",
    "plateau_detected",
    "no_candidates_to_promote",
    "invalid_config",
    "missing_assets",
    "fastlm_unavailable",
    "exception_raised",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_schema_validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _write_result_row(results_path: Path, row: dict[str, Any]) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False))
        f.write("\n")


def _load_existing_results(results_path: Path) -> list[dict[str, Any]]:
    if not results_path.exists():
        return []
    return read_jsonl(results_path)


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _build_run_bundle_dir(*, output_root: Path, campaign_id: str, runner_id: str, shard_path: Path) -> Path:
    safe_campaign = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in campaign_id)
    safe_runner = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in runner_id)
    safe_shard = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in shard_path.stem)
    return output_root / f"run_bundle__{safe_campaign}__{safe_runner}__{safe_shard}"


def _default_error_row(job: dict[str, Any], *, status: str, stop_reason: str, total_seconds: float = 0.0) -> dict[str, Any]:
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
        "status": str(status),
        "stop_reason": str(stop_reason),
        "best_match_ratio": 0.0,
        "best_stage": 0,
        "total_seconds": float(max(total_seconds, 0.0)),
        "total_evals": 0,
        "stage1_best_score": None,
        "stage2_best_score": None,
        "stage3_best_score": None,
        "output_run_dir": None,
        "device": "cpu",
        "scoring_backend": "numpy",
        "fastlm_present": False,
    }


def _run_job_with_helper(
    *,
    job: dict[str, Any],
    repo_root: Path,
    campaign_config_path: Path,
    profile_catalog_path: Path,
    max_seconds_per_job: float,
    max_total_evals_per_job: int | None,
    run_log_path: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="community_job_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        job_path = tmp_dir / "job.json"
        output_path = tmp_dir / "job_output.json"
        job_path.write_text(json.dumps(job, ensure_ascii=True), encoding="utf-8")

        cmd = [
            sys.executable,
            str(HELPER_SCRIPT),
            "--job-json",
            str(job_path),
            "--campaign-config",
            str(campaign_config_path),
            "--profile-catalog",
            str(profile_catalog_path),
            "--output-json",
            str(output_path),
            "--repo-root",
            str(repo_root),
        ]

        with run_log_path.open("a", encoding="utf-8", newline="\n") as run_log:
            run_log.write(f"{_utc_now()} JOB_START job_id={job['job_id']}\n")
            run_log.write(f"{_utc_now()} JOB_CMD {' '.join(cmd)}\n")
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=float(max_seconds_per_job),
                )
            except subprocess.TimeoutExpired:
                run_log.write(f"{_utc_now()} JOB_TIMEOUT job_id={job['job_id']} cap_s={float(max_seconds_per_job):.3f}\n")
                return _default_error_row(
                    job,
                    status="unsolved",
                    stop_reason="time_cap_reached",
                    total_seconds=float(max_seconds_per_job),
                )

            if proc.stdout:
                run_log.write(proc.stdout)
                if not proc.stdout.endswith("\n"):
                    run_log.write("\n")
            if proc.stderr:
                run_log.write(proc.stderr)
                if not proc.stderr.endswith("\n"):
                    run_log.write("\n")
            run_log.write(f"{_utc_now()} JOB_EXIT job_id={job['job_id']} code={proc.returncode}\n")

        if not output_path.exists():
            return _default_error_row(job, status="error", stop_reason="exception_raised")
        payload = load_json(output_path)
        if not isinstance(payload, dict) or not payload.get("ok"):
            err_type = str(payload.get("error_type", ""))
            stop = "missing_assets" if err_type == "FileNotFoundError" else "exception_raised"
            return _default_error_row(job, status="error", stop_reason=stop)
        row = payload.get("row")
        if not isinstance(row, dict):
            return _default_error_row(job, status="error", stop_reason="exception_raised")

    if max_total_evals_per_job is not None:
        try:
            evals = int(row.get("total_evals", 0))
        except Exception:
            evals = 0
        if evals >= int(max_total_evals_per_job) and str(row.get("status")) != "solved":
            row["stop_reason"] = "eval_cap_reached"
    return row


def run_shard_bundle(
    *,
    runner_config_path: Path,
    campaign_config_path: Path,
    profile_catalog_path: Path,
    manifest_schema_path: Path,
    result_schema_path: Path,
    repo_root: Path,
    run_job_fn: Callable[..., dict[str, Any]] = _run_job_with_helper,
) -> dict[str, Any]:
    runner_config = load_json(runner_config_path)
    campaign_config = load_json(campaign_config_path)
    profile_catalog_data = load_json(profile_catalog_path)
    _ = load_profile_catalog_from_dict(profile_catalog_data)  # eager parse + config validation

    runner_id = str(runner_config.get("runner_id", "")).strip()
    if not runner_id:
        raise ValueError("runner config missing runner_id")
    shard_path = Path(str(runner_config.get("shard_path", "")))
    if not shard_path.is_absolute():
        shard_path = (repo_root / shard_path).resolve()
    if not shard_path.exists():
        raise FileNotFoundError(f"shard_path does not exist: {shard_path}")
    output_root = Path(str(runner_config.get("output_root", "")))
    if not output_root.is_absolute():
        output_root = (repo_root / output_root).resolve()
    resume = bool(runner_config.get("resume", True))
    max_jobs = runner_config.get("max_jobs", None)
    if max_jobs is not None:
        max_jobs = int(max_jobs)
        if max_jobs <= 0:
            raise ValueError("max_jobs must be > 0 when provided")

    if str(campaign_config.get("campaign_spec_version")) != "v1.1":
        raise ValueError("campaign_spec_version must be v1.1")
    campaign_id = str(campaign_config.get("campaign_id", "")).strip()
    if not campaign_id:
        raise ValueError("campaign config missing campaign_id")

    caps = campaign_config.get("caps")
    if not isinstance(caps, dict):
        raise ValueError("campaign config missing caps")
    max_seconds_per_job = float(caps.get("max_seconds_per_job", 0))
    if max_seconds_per_job <= 0:
        raise ValueError("caps.max_seconds_per_job must be > 0")
    max_total_evals = caps.get("max_total_evals_per_job", None)
    max_total_evals_per_job = None if max_total_evals is None else int(max_total_evals)

    manifest_validator = _load_schema_validator(manifest_schema_path)
    result_validator = _load_schema_validator(result_schema_path)

    jobs = read_jsonl(shard_path)
    for idx, job in enumerate(jobs):
        errors = sorted(manifest_validator.iter_errors(job), key=lambda item: item.path)
        if errors:
            raise ValueError(f"manifest row {idx} invalid: {errors[0].message}")
        if str(job.get("campaign_id")) != campaign_id:
            raise ValueError(f"manifest row {idx} campaign_id mismatch")

    run_bundle = _build_run_bundle_dir(
        output_root=output_root,
        campaign_id=campaign_id,
        runner_id=runner_id,
        shard_path=shard_path,
    )
    run_bundle.mkdir(parents=True, exist_ok=True)
    run_log_path = run_bundle / "run.log"
    results_path = run_bundle / "results.jsonl"

    existing_rows = _load_existing_results(results_path) if resume else []
    completed_job_ids = {str(row.get("job_id")) for row in existing_rows}
    if existing_rows:
        for idx, row in enumerate(existing_rows):
            errors = sorted(result_validator.iter_errors(row), key=lambda item: item.path)
            if errors:
                raise ValueError(f"existing results row {idx} invalid: {errors[0].message}")

    _copy_if_exists(campaign_config_path, run_bundle / "campaign_config_v1_1.json")
    _copy_if_exists(profile_catalog_path, run_bundle / "profile_catalog_v1_1.json")
    _copy_if_exists(shard_path, run_bundle / "shard_manifest.jsonl")
    _copy_if_exists(repo_root / "setup.log", run_bundle / "setup.log")
    _copy_if_exists(repo_root / "setup_report.json", run_bundle / "setup_report.json")
    _copy_if_exists(repo_root / "preflight.log", run_bundle / "preflight.log")
    _copy_if_exists(repo_root / "preflight_report.json", run_bundle / "preflight_report.json")

    run_meta = {
        "runner_id": runner_id,
        "campaign_id": campaign_id,
        "git_sha": str(campaign_config.get("git_sha")),
        "campaign_mode": True,
        "autoskip_proven_disabled": True,
        "resume": resume,
        "max_jobs": max_jobs,
        "caps": {
            "max_seconds_per_job": max_seconds_per_job,
            "max_total_evals_per_job": max_total_evals_per_job,
        },
        "shard_path": str(shard_path),
        "run_bundle_path": str(run_bundle),
        "started_at_utc": _utc_now(),
        "processed_jobs": 0,
        "resume_skips": 0,
        "result_rows_written": 0,
    }
    write_json(run_bundle / "run_meta.json", run_meta)

    processed = 0
    skips = 0
    rows_written = 0
    for job in jobs:
        if max_jobs is not None and processed >= int(max_jobs):
            break
        job_id = str(job["job_id"])
        if resume and job_id in completed_job_ids:
            skips += 1
            with run_log_path.open("a", encoding="utf-8", newline="\n") as run_log:
                run_log.write(f"{_utc_now()} RESUME_SKIP_ALREADY_RECORDED job_id={job_id}\n")
            continue

        row = run_job_fn(
            job=job,
            repo_root=repo_root,
            campaign_config_path=campaign_config_path,
            profile_catalog_path=profile_catalog_path,
            max_seconds_per_job=max_seconds_per_job,
            max_total_evals_per_job=max_total_evals_per_job,
            run_log_path=run_log_path,
        )
        if str(row.get("stop_reason")) not in STOP_REASON_VALUES:
            row = _default_error_row(job, status="error", stop_reason="invalid_config")
        errors = sorted(result_validator.iter_errors(row), key=lambda item: item.path)
        if errors:
            row = _default_error_row(job, status="error", stop_reason="invalid_config")
            errors2 = sorted(result_validator.iter_errors(row), key=lambda item: item.path)
            if errors2:
                raise ValueError(f"unable to produce valid result row for job_id={job_id}: {errors2[0].message}")
        _write_result_row(results_path, row)
        rows_written += 1
        processed += 1

    run_meta["processed_jobs"] = int(processed)
    run_meta["resume_skips"] = int(skips)
    run_meta["result_rows_written"] = int(rows_written)
    run_meta["finished_at_utc"] = _utc_now()
    write_json(run_bundle / "run_meta.json", run_meta)
    return run_meta


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one community benchmark shard (campaign mode, v1.1).")
    parser.add_argument(
        "--runner-config",
        type=Path,
        required=True,
        help="path to local runner config json (runner_id, shard_path, output_root, resume, max_jobs)",
    )
    parser.add_argument(
        "--campaign-config",
        type=Path,
        default=DEFAULT_CAMPAIGN_CONFIG,
        help=f"path to campaign config json (default: {DEFAULT_CAMPAIGN_CONFIG})",
    )
    parser.add_argument(
        "--profile-catalog",
        type=Path,
        default=DEFAULT_PROFILE_CATALOG,
        help=f"path to profile catalog json (default: {DEFAULT_PROFILE_CATALOG})",
    )
    parser.add_argument(
        "--manifest-schema",
        type=Path,
        default=DEFAULT_MANIFEST_SCHEMA,
        help=f"path to manifest schema json (default: {DEFAULT_MANIFEST_SCHEMA})",
    )
    parser.add_argument(
        "--result-schema",
        type=Path,
        default=DEFAULT_RESULT_SCHEMA,
        help=f"path to result schema json (default: {DEFAULT_RESULT_SCHEMA})",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help=f"repo root path (default: {REPO_ROOT})",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    meta = run_shard_bundle(
        runner_config_path=args.runner_config,
        campaign_config_path=args.campaign_config,
        profile_catalog_path=args.profile_catalog,
        manifest_schema_path=args.manifest_schema,
        result_schema_path=args.result_schema,
        repo_root=args.repo_root.resolve(),
    )
    print(
        "[community] shard run complete "
        f"processed={meta['processed_jobs']} resume_skips={meta['resume_skips']} "
        f"rows={meta['result_rows_written']} bundle={meta['run_bundle_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
