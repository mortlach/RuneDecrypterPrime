from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping, MutableMapping, Sequence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_run_state(*, path: Path, load_json_fn: Callable[[Path], Any]) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json_fn(path)
    if not isinstance(payload, Mapping):
        return {}
    return {str(k): v for k, v in payload.items()}


def append_event_row(*, path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        )
        handle.write("\n")


def run_jobs_with_checkpoints(
    *,
    jobs: Sequence[Any],
    run_mode: str,
    profile_id: str,
    dry_run_only: bool,
    stop_on_error: bool,
    max_wallclock_seconds: float | None,
    resume_skip_completed: bool,
    run_state_path: Path,
    run_events_path: Path,
    plan_job_count: int,
    base_state_fields: Mapping[str, Any],
    write_json_fn: Callable[[Path, Mapping[str, Any]], None],
    job_key_fn: Callable[[Any], str],
    run_job_fn: Callable[[Any], None],
    print_fn: Callable[..., None],
    load_json_fn: Callable[[Path], Any],
) -> None:
    print_fn(
        f"[no_wli_fixture_matrix] jobs={len(jobs)} dry_run={int(bool(dry_run_only))}",
        flush=True,
    )
    if not jobs:
        print_fn("[no_wli_fixture_matrix] no jobs to run", flush=True)
        return
    if dry_run_only:
        print_fn("[no_wli_fixture_matrix] dry-run complete (no runner executions)", flush=True)
        return

    run_state = load_run_state(path=run_state_path, load_json_fn=load_json_fn)
    completed_job_keys: set[str] = {
        str(x) for x in run_state.get("completed_job_keys", []) if str(x).strip()
    }
    plan_job_keys = {job_key_fn(job) for job in jobs}
    completed_job_keys.intersection_update(plan_job_keys)
    selected_jobs = (
        [job for job in jobs if job_key_fn(job) not in completed_job_keys]
        if bool(resume_skip_completed)
        else list(jobs)
    )
    skipped_precompleted = int(plan_job_count) - len(selected_jobs)
    if skipped_precompleted > 0:
        print_fn(
            f"[no_wli_fixture_matrix] resume: skipping {skipped_precompleted} pre-completed jobs",
            flush=True,
        )

    run_state_base: dict[str, Any] = dict(base_state_fields)
    run_state_base.update(
        started_utc=str(run_state.get("started_utc") or utc_now_iso()),
        updated_utc=utc_now_iso(),
        run_mode=str(run_mode),
        profile_id=str(profile_id),
        total_jobs=int(plan_job_count),
        remaining_jobs=int(len(selected_jobs)),
        skipped_precompleted=int(skipped_precompleted),
        completed_jobs=int(len(completed_job_keys)),
        completed_job_keys=sorted(completed_job_keys),
        stopped_early=0,
        run_state_version="v1",
    )
    write_json_fn(run_state_path, run_state_base)

    wallclock_start = time.time()
    completed_this_session = 0
    stopped_early = False
    span_ab_pairs: dict[str, dict[str, float]] = {}

    def _span_ab_base_key(job: Any) -> str:
        return "|".join(
            (
                str(getattr(job, "fixture_id", "")),
                f"p{int(getattr(job, 'period', 0))}",
                f"c{int(getattr(job, 'columns', 0))}",
                f"l{int(getattr(job, 'length', 0))}",
                f"seed{int(getattr(job, 'run_seed', 0))}",
                str(getattr(job, "run_mode", "")),
                str(getattr(job, "profile_id", "")),
                str(getattr(job, "scoring_experiment_profile", "")),
                str(getattr(job, "schedule_early", "")),
                str(getattr(job, "schedule_middle", "")),
                str(getattr(job, "schedule_late", "")),
            )
        )
    for idx, job in enumerate(selected_jobs, start=1):
        job_key = job_key_fn(job)
        if max_wallclock_seconds is not None:
            elapsed = float(time.time() - wallclock_start)
            if elapsed >= float(max_wallclock_seconds):
                print_fn(
                    f"[no_wli_fixture_matrix] wallclock cap reached; "
                    f"elapsed={elapsed:.1f}s cap={float(max_wallclock_seconds):.1f}s "
                    f"completed_jobs={idx-1}",
                    flush=True,
                )
                stopped_early = True
                break
        print_fn(
            f"[no_wli_fixture_matrix] run {idx}/{len(selected_jobs)} "
            f"fixture={job.fixture_id} p={job.period} c={job.columns} seed={job.run_seed} "
            f"exp={job.scoring_experiment_profile} "
            f"schedule=({job.schedule_early},{job.schedule_middle},{job.schedule_late})",
            flush=True,
        )
        append_event_row(
            path=run_events_path,
            row=dict(
                timestamp_utc=utc_now_iso(),
                event="job_started",
                run_mode=str(run_mode),
                profile_id=str(profile_id),
                index=int(idx),
                total=int(len(selected_jobs)),
                job_key=str(job_key),
                job=job.as_dict(),
                span_ab_case_id=str(getattr(job, "span_ab_case_id", "none")),
                span_decision_role_enabled=bool(
                    getattr(job, "span_decision_role_enabled", False)
                ),
            ),
        )
        t0_job = time.time()
        try:
            run_job_fn(job)
        except Exception as exc:
            print_fn(
                f"[no_wli_fixture_matrix] error fixture={job.fixture_id} p={job.period} c={job.columns} "
                f"seed={job.run_seed} err={type(exc).__name__}:{exc}",
                flush=True,
            )
            append_event_row(
                path=run_events_path,
                row=dict(
                    timestamp_utc=utc_now_iso(),
                    event="job_error",
                    run_mode=str(run_mode),
                    profile_id=str(profile_id),
                    index=int(idx),
                    total=int(len(selected_jobs)),
                    job_key=str(job_key),
                    elapsed_seconds=float(time.time() - t0_job),
                    error_type=str(type(exc).__name__),
                    error=str(exc),
                ),
            )
            run_state_base.update(
                updated_utc=utc_now_iso(),
                last_error=dict(
                    index=int(idx),
                    job_key=str(job_key),
                    error_type=str(type(exc).__name__),
                    error=str(exc),
                ),
                stopped_early=1,
                completed_jobs=int(len(completed_job_keys)),
                completed_job_keys=sorted(completed_job_keys),
                remaining_jobs=int(max(0, len(selected_jobs) - idx + 1)),
            )
            write_json_fn(run_state_path, run_state_base)
            if bool(stop_on_error):
                raise
            continue

        completed_job_keys.add(str(job_key))
        completed_this_session += 1
        job_elapsed = float(time.time() - t0_job)
        append_event_row(
            path=run_events_path,
            row=dict(
                timestamp_utc=utc_now_iso(),
                event="job_completed",
                run_mode=str(run_mode),
                profile_id=str(profile_id),
                index=int(idx),
                total=int(len(selected_jobs)),
                job_key=str(job_key),
                elapsed_seconds=float(job_elapsed),
                span_ab_case_id=str(getattr(job, "span_ab_case_id", "none")),
                span_decision_role_enabled=bool(
                    getattr(job, "span_decision_role_enabled", False)
                ),
            ),
        )
        span_case_id = str(getattr(job, "span_ab_case_id", "none")).strip().lower()
        if span_case_id in {"span_shadow", "span_prune", "span_gate", "span_combined", "span_judge"}:
            base_key = _span_ab_base_key(job)
            pair = span_ab_pairs.setdefault(base_key, {})
            pair[span_case_id] = float(job_elapsed)
            if "span_shadow" in pair and len(pair) >= 2:
                decision_case_id = sorted(k for k in pair.keys() if k != "span_shadow")[0]
                shadow_elapsed = float(pair["span_shadow"])
                decision_elapsed = float(pair[decision_case_id])
                append_event_row(
                    path=run_events_path,
                    row=dict(
                        timestamp_utc=utc_now_iso(),
                        event="span_ab_pair_delta",
                        run_mode=str(run_mode),
                        profile_id=str(profile_id),
                        pair_key=str(base_key),
                        shadow_case_id="span_shadow",
                        decision_case_id=str(decision_case_id),
                        shadow_elapsed_seconds=float(shadow_elapsed),
                        decision_elapsed_seconds=float(decision_elapsed),
                        delta_elapsed_seconds=float(decision_elapsed - shadow_elapsed),
                    ),
                )
        run_state_base.update(
            updated_utc=utc_now_iso(),
            completed_jobs=int(len(completed_job_keys)),
            completed_job_keys=sorted(completed_job_keys),
            last_completed=dict(
                index=int(idx),
                job_key=str(job_key),
                elapsed_seconds=float(job_elapsed),
            ),
            remaining_jobs=int(max(0, len(selected_jobs) - idx)),
        )
        write_json_fn(run_state_path, run_state_base)

    run_state_base.update(
        updated_utc=utc_now_iso(),
        completed_utc=utc_now_iso(),
        stopped_early=int(bool(stopped_early)),
        completed_jobs=int(len(completed_job_keys)),
        completed_job_keys=sorted(completed_job_keys),
        remaining_jobs=int(0 if not stopped_early else run_state_base.get("remaining_jobs", 0)),
    )
    write_json_fn(run_state_path, run_state_base)
    print_fn(
        f"[no_wli_fixture_matrix] completed session_completed_jobs={completed_this_session} "
        f"total_completed_jobs={len(completed_job_keys)}",
        flush=True,
    )
