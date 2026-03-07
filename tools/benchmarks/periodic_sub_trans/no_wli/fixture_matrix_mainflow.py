from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping


def run_mainflow(
    *,
    state: MutableMapping[str, Any],
    repo_root: Path,
    resolve_path_fn: Callable[[Path], Path],
    load_json_fn: Callable[[Path], Any],
    write_json_fn: Callable[[Path, Mapping[str, Any]], None],
    load_fixture_specs_fn: Callable[..., list[Any]],
    resolve_period_columns_fn: Callable[..., dict[int, tuple[int, ...]]],
    build_schedule_matrix_fn: Callable[..., list[dict[str, str]]],
    build_fixture_jobs_fn: Callable[..., list[Any]],
    build_plan_payload_fn: Callable[..., dict[str, Any]],
    run_jobs_with_checkpoints_fn: Callable[..., None],
    load_run_state_fn: Callable[[Path], dict[str, Any]],
    job_key_fn: Callable[[Any], str],
    run_job_fn: Callable[[Any], None],
    print_fn: Callable[..., None],
) -> None:
    campaign_path = resolve_path_fn(Path(state["CAMPAIGN_CONFIG_PATH"]))
    campaign_config = load_json_fn(campaign_path)
    if not isinstance(campaign_config, Mapping):
        raise ValueError(f"campaign config must be an object: {campaign_path}")

    fixtures = load_fixture_specs_fn(
        campaign_config=campaign_config,
        repo_root=repo_root,
        fixture_ids=state["FIXTURE_IDS"],
        fixture_length_override=state["FIXTURE_LENGTH_OVERRIDE"],
    )
    period_columns = resolve_period_columns_fn(
        campaign_config=campaign_config,
        use_campaign_grid=bool(state["USE_CAMPAIGN_GRID"]),
        periods_override=state["PERIODS_OVERRIDE"],
        columns_override_by_period=state["COLUMNS_OVERRIDE_BY_PERIOD"],
    )
    schedules = build_schedule_matrix_fn(
        mode=str(state["SCHEDULE_COVERAGE_MODE"]),
        explicit_schedules=state["EXPLICIT_SCHEDULES"],
    )
    jobs = build_fixture_jobs_fn(
        fixtures=fixtures,
        period_columns=period_columns,
        run_seeds=state["RUN_SEEDS"],
        run_mode=state["RUN_MODE"],
        profile_id=state["NO_WLI_PROFILE_ID"],
        heartbeat_seconds=int(state["HEARTBEAT_SECONDS"]),
        text_offsets=state["TEXT_OFFSETS"],
        scorer_impl=state["SCORER_IMPL"],
        scorer_stage3_impl_avg_fulltext=state["SCORER_STAGE3_IMPL_AVG_FULLTEXT"],
        scoring_experiment_profiles=state["SCORING_EXPERIMENT_PROFILES"],
        schedules=schedules,
    )
    if state["MAX_JOBS"] is not None:
        jobs = jobs[: max(0, int(state["MAX_JOBS"]))]

    plan_payload = build_plan_payload_fn(
        repo_root=repo_root,
        campaign_path=campaign_path,
        run_mode=str(state["RUN_MODE"]),
        profile_id=str(state["NO_WLI_PROFILE_ID"]),
        schedule_coverage_mode=str(state["SCHEDULE_COVERAGE_MODE"]),
        schedules=schedules,
        fixtures=fixtures,
        jobs=jobs,
        scoring_experiment_profiles=state["SCORING_EXPERIMENT_PROFILES"],
        require_no_win10_objectives=bool(state["REQUIRE_NO_WIN10_OBJECTIVES"]),
        require_full_text_effective=bool(state["REQUIRE_FULL_TEXT_EFFECTIVE"]),
        disable_stage3_span_basin_k_sweep=bool(state["DISABLE_STAGE3_SPAN_BASIN_K_SWEEP"]),
        stage3_span_basin_k_sweep_values=state["STAGE3_SPAN_BASIN_K_SWEEP_VALUES"],
        dry_run_only=bool(state["DRY_RUN_ONLY"]),
        max_wallclock_seconds=(
            None
            if state["MAX_WALLCLOCK_SECONDS"] is None
            else float(state["MAX_WALLCLOCK_SECONDS"])
        ),
        resume_skip_completed=bool(state["RESUME_SKIP_COMPLETED"]),
        run_state_path=state["RUN_STATE_PATH"],
        run_events_path=state["RUN_EVENTS_PATH"],
        fixture_length_override=state["FIXTURE_LENGTH_OVERRIDE"],
        period_columns=period_columns,
        resolve_path_fn=resolve_path_fn,
    )
    if bool(state["WRITE_PLAN_JSON"]):
        write_json_fn(resolve_path_fn(Path(state["PLAN_OUTPUT_PATH"])), plan_payload)

    print_fn(
        f"[no_wli_fixture_matrix] fixtures={len(fixtures)} periods={len(period_columns)} "
        f"schedules={len(schedules)} jobs={len(jobs)} dry_run={int(bool(state['DRY_RUN_ONLY']))}",
        flush=True,
    )
    if not jobs:
        print_fn("[no_wli_fixture_matrix] no jobs to run", flush=True)
        return
    if bool(state["DRY_RUN_ONLY"]):
        print_fn("[no_wli_fixture_matrix] dry-run complete (no runner executions)", flush=True)
        return

    run_state_path = resolve_path_fn(Path(state["RUN_STATE_PATH"]))
    run_events_path = resolve_path_fn(Path(state["RUN_EVENTS_PATH"]))
    run_state = load_run_state_fn(run_state_path)
    run_state_base: dict[str, Any] = dict(
        started_utc=str(run_state.get("started_utc") or state["_utc_now_iso"]()),
        campaign_config_path=str(campaign_path),
        run_mode=str(state["RUN_MODE"]),
        profile_id=str(state["NO_WLI_PROFILE_ID"]),
        schedule_coverage_mode=str(state["SCHEDULE_COVERAGE_MODE"]),
        scoring_experiment_profiles=[str(x) for x in state["SCORING_EXPERIMENT_PROFILES"]],
    )
    run_jobs_with_checkpoints_fn(
        jobs=jobs,
        run_mode=str(state["RUN_MODE"]),
        profile_id=str(state["NO_WLI_PROFILE_ID"]),
        dry_run_only=bool(state["DRY_RUN_ONLY"]),
        stop_on_error=bool(state["STOP_ON_ERROR"]),
        max_wallclock_seconds=(
            None
            if state["MAX_WALLCLOCK_SECONDS"] is None
            else float(state["MAX_WALLCLOCK_SECONDS"])
        ),
        resume_skip_completed=bool(state["RESUME_SKIP_COMPLETED"]),
        run_state_path=run_state_path,
        run_events_path=run_events_path,
        plan_job_count=int(plan_payload["job_count"]),
        base_state_fields=run_state_base,
        write_json_fn=write_json_fn,
        job_key_fn=job_key_fn,
        run_job_fn=run_job_fn,
        print_fn=print_fn,
        load_json_fn=load_json_fn,
    )
