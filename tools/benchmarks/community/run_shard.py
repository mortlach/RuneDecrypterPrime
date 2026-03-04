from __future__ import annotations

import argparse
import importlib
import json
import re
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

from tools.benchmarks.community._campaign_common import (
    INTEGRITY_CHAIN_GENESIS,
    INTEGRITY_CHAIN_HASH,
    INTEGRITY_CHAIN_VERSION,
    build_result_integrity_row,
    load_json,
    read_jsonl,
    verify_results_integrity,
    write_json,
)
from tools.benchmarks.community.config import load_profile_catalog_from_dict
from tools.benchmarks.community.setup_and_preflight import latest_setup_bundle_dir

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

# Console output controls (hardcoded by repo convention; no CLI flags).
CONSOLE_MODE = "compact"  # "compact" | "quiet"
CONSOLE_PRINT_START = True
CONSOLE_PRINT_PER_JOB = True
CONSOLE_PRINT_EVERY_N = 1
CONSOLE_PRINT_FINAL = True
CONSOLE_PRINT_PATHS = True
CONSOLE_PRINT_INTEGRITY_SUMMARY = True

_ROW_IDENTITY_FIELDS = (
    "campaign_id",
    "job_id",
    "git_sha",
    "text_fixture_id",
    "period",
    "columns",
    "order",
    "profile_id",
    "run_seed",
    "replicate_idx",
    "config_fingerprint",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_path_for_log(path_text: str, *, repo_root: Path) -> str:
    text = str(path_text).strip()
    if not text:
        return text
    try:
        path_obj = Path(text)
    except Exception:
        return "<redacted_path>"
    if path_obj.is_absolute():
        try:
            return str(path_obj.resolve().relative_to(repo_root.resolve()))
        except Exception:
            return "<abs_path>"
    return text


def _format_job_cmd_for_log(*, cmd: list[str], repo_root: Path, helper_script: Path) -> str:
    if not cmd:
        return ""
    out: list[str] = []
    out.append(Path(str(cmd[0])).name)
    if len(cmd) > 1:
        try:
            helper_rel = helper_script.resolve().relative_to(repo_root.resolve())
            helper_rel_text = str(helper_rel)
        except Exception:
            helper_rel_text = helper_script.name
        script_token = _sanitize_path_for_log(str(cmd[1]), repo_root=repo_root)
        if script_token == "<abs_path>":
            script_token = helper_rel_text
        out.append(script_token)

    i = 2
    while i < len(cmd):
        token = str(cmd[i])
        if token.startswith("--"):
            out.append(token)
            if i + 1 < len(cmd) and not str(cmd[i + 1]).startswith("--"):
                raw_val = str(cmd[i + 1])
                if token in {"--job-json", "--output-json"}:
                    out.append("<tmp_path>")
                elif token in {"--campaign-config", "--profile-catalog", "--repo-root"}:
                    out.append(_sanitize_path_for_log(raw_val, repo_root=repo_root))
                else:
                    out.append("<arg>")
                i += 2
                continue
            i += 1
            continue
        out.append("<arg>")
        i += 1
    return " ".join(out)


def _sanitize_log_text(text: str, *, repo_root: Path) -> str:
    value = str(text)
    # First preserve useful repo-local traces by mapping to relative paths.
    repo_abs = str(repo_root.resolve())
    value = value.replace(repo_abs, ".")
    # Then redact any remaining absolute Windows paths (machine/user specific).
    value = re.sub(r"[A-Za-z]:\\[^\s\"']+", "<abs_path>", value)
    # Redact Unix-like absolute paths too, except current-dir relative forms.
    value = re.sub(r"(?<![A-Za-z0-9_./-])/(?:[^ \n\r\t\"']+)", "<abs_path>", value)
    return value


def _console_enabled() -> bool:
    return str(CONSOLE_MODE).strip().lower() != "quiet"


def _fmt_short_float(value: Any, *, default: float = 0.0, places: int = 3) -> str:
    try:
        out = float(value)
    except Exception:
        out = float(default)
    return f"{out:.{int(places)}f}"


def _fmt_short_int(value: Any, *, default: int = 0) -> str:
    try:
        out = int(value)
    except Exception:
        out = int(default)
    return str(out)


def _should_print_job_line(job_index: int) -> bool:
    if not CONSOLE_PRINT_PER_JOB:
        return False
    every_n = max(1, int(CONSOLE_PRINT_EVERY_N))
    return int(job_index) % every_n == 0


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


def _load_existing_integrity_rows(integrity_path: Path) -> list[dict[str, Any]]:
    if not integrity_path.exists():
        return []
    return read_jsonl(integrity_path)


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_setup_preflight_artifacts(*, repo_root: Path, run_bundle: Path) -> Path:
    source_dir = latest_setup_bundle_dir(repo_root)
    if source_dir is None:
        # Back-compat fallback for partially configured environments.
        source_dir = repo_root
    _copy_if_exists(source_dir / "setup.log", run_bundle / "setup.log")
    _copy_if_exists(source_dir / "setup_report.json", run_bundle / "setup_report.json")
    _copy_if_exists(source_dir / "preflight.log", run_bundle / "preflight.log")
    _copy_if_exists(source_dir / "preflight_report.json", run_bundle / "preflight_report.json")
    return source_dir


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


def _row_identity_error(*, row: dict[str, Any], expected_job: dict[str, Any]) -> str | None:
    for field in _ROW_IDENTITY_FIELDS:
        if str(row.get(field)) != str(expected_job.get(field)):
            return (
                f"row identity mismatch for field={field}: "
                f"expected={expected_job.get(field)!r} got={row.get(field)!r}"
            )
    return None


def _detect_fastlm_available(*, repo_root: Path) -> bool:
    repo_root = repo_root.resolve()
    src_root = repo_root / "src"
    for path in (repo_root, src_root):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    try:
        importlib.import_module("rune_decrypter_prime.scoring.language_model._fastlm")
        return True
    except Exception:
        return False


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
    fastlm_available = _detect_fastlm_available(repo_root=repo_root)
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
            run_log.write(
                f"{_utc_now()} JOB_CMD "
                f"{_format_job_cmd_for_log(cmd=cmd, repo_root=repo_root, helper_script=HELPER_SCRIPT)}\n"
            )
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
                row = _default_error_row(
                    job,
                    status="unsolved",
                    stop_reason="time_cap_reached",
                    total_seconds=float(max_seconds_per_job),
                )
                row["fastlm_present"] = bool(fastlm_available)
                return row

            if proc.stdout:
                safe_stdout = _sanitize_log_text(proc.stdout, repo_root=repo_root)
                run_log.write(safe_stdout)
                if not safe_stdout.endswith("\n"):
                    run_log.write("\n")
            if proc.stderr:
                safe_stderr = _sanitize_log_text(proc.stderr, repo_root=repo_root)
                run_log.write(safe_stderr)
                if not safe_stderr.endswith("\n"):
                    run_log.write("\n")
            run_log.write(f"{_utc_now()} JOB_EXIT job_id={job['job_id']} code={proc.returncode}\n")

        if not output_path.exists():
            row = _default_error_row(job, status="error", stop_reason="exception_raised")
            row["fastlm_present"] = bool(fastlm_available)
            return row
        payload = load_json(output_path)
        if not isinstance(payload, dict) or not payload.get("ok"):
            err_type = str(payload.get("error_type", ""))
            stop = "missing_assets" if err_type == "FileNotFoundError" else "exception_raised"
            row = _default_error_row(job, status="error", stop_reason=stop)
            row["fastlm_present"] = bool(fastlm_available)
            return row
        row = payload.get("row")
        if not isinstance(row, dict):
            out = _default_error_row(job, status="error", stop_reason="exception_raised")
            out["fastlm_present"] = bool(fastlm_available)
            return out

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
    jobs_by_id: dict[str, dict[str, Any]] = {}
    for idx, job in enumerate(jobs):
        job_id = str(job.get("job_id"))
        if job_id in jobs_by_id:
            raise ValueError(f"manifest duplicate job_id at row {idx}: {job_id}")
        jobs_by_id[job_id] = job
    total_jobs = len(jobs)

    run_bundle = _build_run_bundle_dir(
        output_root=output_root,
        campaign_id=campaign_id,
        runner_id=runner_id,
        shard_path=shard_path,
    )
    run_bundle.mkdir(parents=True, exist_ok=True)
    run_log_path = run_bundle / "run.log"
    results_path = run_bundle / "results.jsonl"
    results_integrity_path = run_bundle / "results_integrity.jsonl"

    if not resume:
        if results_path.exists():
            results_path.unlink()
        if results_integrity_path.exists():
            results_integrity_path.unlink()
        run_meta_path = run_bundle / "run_meta.json"
        if run_log_path.exists():
            run_log_path.unlink()
        if run_meta_path.exists():
            run_meta_path.unlink()

    existing_rows = _load_existing_results(results_path) if resume else []
    existing_integrity_rows = _load_existing_integrity_rows(results_integrity_path) if resume else []
    completed_job_ids: set[str] = set()
    if existing_rows:
        for idx, row in enumerate(existing_rows):
            errors = sorted(result_validator.iter_errors(row), key=lambda item: item.path)
            if errors:
                raise ValueError(f"existing results row {idx} invalid: {errors[0].message}")
            job_id = str(row.get("job_id"))
            if job_id in completed_job_ids:
                raise ValueError(f"duplicate existing results job_id: {job_id}")
            completed_job_ids.add(job_id)
            if job_id not in jobs_by_id:
                raise ValueError(f"existing results row {idx} job_id not in current shard: {job_id}")
            identity_error = _row_identity_error(row=row, expected_job=jobs_by_id[job_id])
            if identity_error is not None:
                raise ValueError(f"existing results row {idx} {identity_error}")
    if resume:
        integrity_errors, chain_tail = verify_results_integrity(
            result_rows=existing_rows,
            integrity_rows=existing_integrity_rows,
        )
        if integrity_errors:
            raise ValueError(
                "existing results integrity invalid: " + "; ".join(integrity_errors[:3])
            )
    else:
        chain_tail = INTEGRITY_CHAIN_GENESIS

    _copy_if_exists(campaign_config_path, run_bundle / "campaign_config_v1_1.json")
    _copy_if_exists(profile_catalog_path, run_bundle / "profile_catalog_v1_1.json")
    _copy_if_exists(shard_path, run_bundle / "shard_manifest.jsonl")
    setup_source_dir = _copy_setup_preflight_artifacts(repo_root=repo_root, run_bundle=run_bundle)

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
        "setup_preflight_source_dir": str(setup_source_dir),
        "started_at_utc": _utc_now(),
        "jobs_in_manifest": int(total_jobs),
        "processed_jobs": 0,
        "resume_skips": 0,
        "result_rows_written": 0,
        "status_counts": {
            "solved": 0,
            "unsolved": 0,
            "stalled": 0,
            "error": 0,
        },
        "results_integrity": {
            "integrity_version": INTEGRITY_CHAIN_VERSION,
            "hash_algorithm": INTEGRITY_CHAIN_HASH,
            "genesis_hash": INTEGRITY_CHAIN_GENESIS,
            "row_count": int(len(existing_rows)),
            "final_chain_hash": str(chain_tail),
        },
    }
    write_json(run_bundle / "run_meta.json", run_meta)

    if _console_enabled() and CONSOLE_PRINT_START:
        jobs_target = int(total_jobs)
        caps_eval_text = "none" if max_total_evals_per_job is None else str(max_total_evals_per_job)
        print(
            "[community] shard start "
            f"campaign={campaign_id} runner={runner_id} "
            f"jobs={jobs_target} resume={int(bool(resume))} "
            f"caps=(seconds={_fmt_short_float(max_seconds_per_job, places=1)},evals={caps_eval_text}) "
            f"shard={shard_path}",
            flush=True,
        )
        if CONSOLE_PRINT_PATHS:
            print(
                "[community] shard paths "
                f"bundle={run_bundle} run_log={run_log_path} "
                f"results={results_path} integrity={results_integrity_path}",
                flush=True,
            )

    processed = 0
    skips = 0
    rows_written = 0
    status_counts = {
        "solved": 0,
        "unsolved": 0,
        "stalled": 0,
        "error": 0,
    }
    next_row_index = int(len(existing_rows))
    current_chain_hash = str(chain_tail)
    for job_index, job in enumerate(jobs, start=1):
        if max_jobs is not None and processed >= int(max_jobs):
            break
        job_id = str(job["job_id"])
        if resume and job_id in completed_job_ids:
            skips += 1
            with run_log_path.open("a", encoding="utf-8", newline="\n") as run_log:
                run_log.write(f"{_utc_now()} RESUME_SKIP_ALREADY_RECORDED job_id={job_id}\n")
            if _console_enabled() and _should_print_job_line(job_index):
                print(
                    "[community] job "
                    f"{job_index}/{total_jobs} job_id={job_id} status=skip stop=resume_already_recorded",
                    flush=True,
                )
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
        if not isinstance(row, dict):
            row = _default_error_row(job, status="error", stop_reason="invalid_config")
        # Enforce that helper output is tagged to exactly this scheduled job.
        identity_error = _row_identity_error(row=row, expected_job=job)
        if identity_error is not None:
            with run_log_path.open("a", encoding="utf-8", newline="\n") as run_log:
                run_log.write(f"{_utc_now()} ROW_IDENTITY_MISMATCH job_id={job_id} detail={identity_error}\n")
            bad_fastlm = bool(row.get("fastlm_present", False)) if isinstance(row, dict) else False
            row = _default_error_row(job, status="error", stop_reason="invalid_config")
            row["fastlm_present"] = bad_fastlm
        if str(row.get("stop_reason")) not in STOP_REASON_VALUES:
            bad_fastlm = bool(row.get("fastlm_present", False)) if isinstance(row, dict) else False
            row = _default_error_row(job, status="error", stop_reason="invalid_config")
            row["fastlm_present"] = bad_fastlm
        errors = sorted(result_validator.iter_errors(row), key=lambda item: item.path)
        if errors:
            bad_fastlm = bool(row.get("fastlm_present", False)) if isinstance(row, dict) else False
            row = _default_error_row(job, status="error", stop_reason="invalid_config")
            row["fastlm_present"] = bad_fastlm
            errors2 = sorted(result_validator.iter_errors(row), key=lambda item: item.path)
            if errors2:
                raise ValueError(f"unable to produce valid result row for job_id={job_id}: {errors2[0].message}")
        integrity_row = build_result_integrity_row(
            result_row=row,
            row_index=next_row_index,
            prev_chain_hash=current_chain_hash,
        )
        _write_result_row(results_path, row)
        _write_result_row(results_integrity_path, integrity_row)
        rows_written += 1
        status = str(row.get("status", "error")).strip().lower()
        if status not in status_counts:
            status = "error"
        status_counts[status] += 1
        if _console_enabled() and _should_print_job_line(job_index):
            print(
                "[community] job "
                f"{job_index}/{total_jobs} job_id={job_id} "
                f"status={status} stop={str(row.get('stop_reason', ''))} "
                f"match={_fmt_short_float(row.get('best_match_ratio'), places=3)} "
                f"secs={_fmt_short_float(row.get('total_seconds'), places=1)} "
                f"evals={_fmt_short_int(row.get('total_evals'))}",
                flush=True,
            )
        next_row_index += 1
        current_chain_hash = str(integrity_row["chain_hash"])
        completed_job_ids.add(job_id)
        processed += 1

    jobs_seen = int(processed + skips)
    run_meta["processed_jobs"] = int(processed)
    run_meta["resume_skips"] = int(skips)
    run_meta["jobs_seen"] = int(jobs_seen)
    run_meta["result_rows_written"] = int(rows_written)
    run_meta["status_counts"] = dict(status_counts)
    run_meta["results_integrity"] = {
        "integrity_version": INTEGRITY_CHAIN_VERSION,
        "hash_algorithm": INTEGRITY_CHAIN_HASH,
        "genesis_hash": INTEGRITY_CHAIN_GENESIS,
        "row_count": int(len(existing_rows) + rows_written),
        "final_chain_hash": str(current_chain_hash),
    }
    run_meta["finished_at_utc"] = _utc_now()
    write_json(run_bundle / "run_meta.json", run_meta)

    if _console_enabled() and CONSOLE_PRINT_FINAL:
        final_msg = (
            "[community] shard done "
            f"processed={processed} skips={skips} seen={jobs_seen}/{total_jobs} "
            f"solved={status_counts['solved']} unsolved={status_counts['unsolved']} "
            f"stalled={status_counts['stalled']} error={status_counts['error']} "
            f"rows_written={rows_written}"
        )
        if CONSOLE_PRINT_INTEGRITY_SUMMARY:
            final_msg += (
                " "
                f"integrity_rows={run_meta['results_integrity']['row_count']} "
                f"integrity_tail={run_meta['results_integrity']['final_chain_hash'][:12]}"
            )
        print(final_msg, flush=True)
        if CONSOLE_PRINT_PATHS:
            print(
                "[community] shard outputs "
                f"bundle={run_bundle} run_log={run_log_path} "
                f"results={results_path} integrity={results_integrity_path}",
                flush=True,
            )
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
    if not _console_enabled():
        print(
            "[community] shard run complete "
            f"processed={meta['processed_jobs']} resume_skips={meta['resume_skips']} "
            f"rows={meta['result_rows_written']} bundle={meta['run_bundle_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
