from __future__ import annotations

from datetime import datetime, timezone
import hashlib
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


def planned_job_keys_signature(*, job_keys: Sequence[str]) -> str:
    normalized = [str(x) for x in job_keys]
    payload = json.dumps(
        normalized,
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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

    plan_job_keys_in_order = [str(job_key_fn(job)) for job in jobs]
    if len(plan_job_keys_in_order) != len(set(plan_job_keys_in_order)):
        raise ValueError("fixture-matrix plan contains duplicate job keys")
    planned_job_count = int(len(plan_job_keys_in_order))
    planned_job_keys_sig = planned_job_keys_signature(job_keys=plan_job_keys_in_order)
    expected_experiment_run_id = str(
        base_state_fields.get("experiment_run_id", "")
    ).strip()

    if planned_job_count != int(plan_job_count):
        raise ValueError(
            "fixture-matrix plan_job_count does not match materialized job count"
        )

    run_state = load_run_state(path=run_state_path, load_json_fn=load_json_fn)

    existing_experiment_run_id = str(run_state.get("experiment_run_id", "")).strip()
    existing_planned_job_keys_sig = str(
        run_state.get("planned_job_keys_signature", "")
    ).strip()
    if run_state:
        if expected_experiment_run_id:
            if not existing_experiment_run_id:
                raise ValueError(
                    "run_state missing experiment_run_id; rotate stale control files"
                )
            if existing_experiment_run_id != expected_experiment_run_id:
                raise ValueError(
                    "run_state experiment_run_id mismatch: "
                    f"expected {expected_experiment_run_id} got {existing_experiment_run_id}"
                )
        if not existing_planned_job_keys_sig:
            raise ValueError(
                "run_state missing planned_job_keys_signature; rotate stale control files"
            )
        if existing_planned_job_keys_sig != planned_job_keys_sig:
            raise ValueError(
                "run_state planned_job_keys_signature mismatch; rotate stale control files"
            )

    completed_job_keys: set[str] = {
        str(x) for x in run_state.get("completed_job_keys", []) if str(x).strip()
    }
    plan_job_keys = set(plan_job_keys_in_order)
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
        planned_job_count=int(planned_job_count),
        planned_job_keys_signature=str(planned_job_keys_sig),
        remaining_jobs=int(len(selected_jobs)),
        skipped_precompleted=int(skipped_precompleted),
        completed_jobs=int(len(completed_job_keys)),
        completed_job_keys=sorted(completed_job_keys),
        stopped_early=0,
        run_state_version="v2",
    )
    write_json_fn(run_state_path, run_state_base)

    event_common = (
        {}
        if not expected_experiment_run_id
        else {"experiment_run_id": str(expected_experiment_run_id)}
    )

    wallclock_start = time.time()
    completed_this_session = 0
    stopped_early = False
    span_ab_pairs: dict[str, dict[str, float]] = {}

    def _span_ab_base_key(job: Any) -> str:
        instance_input_mode = str(
            getattr(job, "instance_input_mode", "generated")
        ).strip().lower()
        return "|".join(
            (
                str(instance_input_mode or "generated"),
                (
                    str(getattr(job, "instance_fixture_id", ""))
                    if instance_input_mode == "fixed_ciphertext"
                    else str(getattr(job, "fixture_id", ""))
                ),
                f"p{int(getattr(job, 'period', 0))}",
                f"c{int(getattr(job, 'columns', 0))}",
                f"l{int(getattr(job, 'length', 0))}",
                (
                    f"search{int(getattr(job, 'search_seed', 0))}"
                    if instance_input_mode == "fixed_ciphertext"
                    else f"seed{int(getattr(job, 'run_seed', 0))}"
                ),
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
        instance_input_mode = str(
            getattr(job, "instance_input_mode", "generated")
        ).strip().lower()
        identity_txt = (
            f"fixture={str(getattr(job, 'instance_fixture_id', ''))} "
            f"search_seed={int(getattr(job, 'search_seed', 0))}"
            if instance_input_mode == "fixed_ciphertext"
            else f"fixture={job.fixture_id} seed={job.run_seed}"
        )
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
            f"{identity_txt} p={job.period} c={job.columns} "
            f"exp={job.scoring_experiment_profile} "
            f"schedule=({job.schedule_early},{job.schedule_middle},{job.schedule_late})",
            flush=True,
        )
        append_event_row(
            path=run_events_path,
            row=dict(
                event_common,
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
                f"[no_wli_fixture_matrix] error {identity_txt} p={job.period} c={job.columns} "
                f"err={type(exc).__name__}:{exc}",
                flush=True,
            )
            append_event_row(
                path=run_events_path,
                row=dict(
                    event_common,
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
                event_common,
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
                        event_common,
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
