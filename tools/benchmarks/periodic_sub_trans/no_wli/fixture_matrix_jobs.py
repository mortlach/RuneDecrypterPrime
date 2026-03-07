from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def job_key(job: Any) -> str:
    return "|".join(
        (
            str(job.fixture_id),
            f"p{int(job.period)}",
            f"c{int(job.columns)}",
            f"l{int(job.length)}",
            f"seed{int(job.run_seed)}",
            str(job.run_mode),
            str(job.profile_id),
            str(job.scoring_experiment_profile),
            str(job.schedule_early),
            str(job.schedule_middle),
            str(job.schedule_late),
        )
    )


def build_fixture_jobs(
    *,
    fixtures: Sequence[Any],
    period_columns: Mapping[int, Sequence[int]],
    run_seeds: Sequence[int],
    run_mode: str,
    profile_id: str,
    heartbeat_seconds: int,
    text_offsets: Sequence[int],
    scorer_impl: str,
    scorer_stage3_impl_avg_fulltext: str,
    scoring_experiment_profiles: Sequence[str],
    schedules: Sequence[Mapping[str, str]],
    unique_sorted_ints_fn: Callable[[Sequence[int]], tuple[int, ...]],
    validate_scorer_schedule_ids_fn: Callable[..., Any],
    validate_schedule_contract_fn: Callable[..., None],
    job_cls: type,
) -> list[Any]:
    seeds = unique_sorted_ints_fn(tuple(int(x) for x in run_seeds))
    if not seeds:
        raise ValueError("RUN_SEEDS resolved empty")

    exp_profiles = [
        str(x).strip().lower() for x in scoring_experiment_profiles if str(x).strip()
    ]
    if not exp_profiles:
        raise ValueError("SCORING_EXPERIMENT_PROFILES resolved empty")

    offsets = tuple(int(x) for x in text_offsets)
    if not offsets:
        raise ValueError("TEXT_OFFSETS resolved empty")

    jobs: list[Any] = []
    validated_schedules: list[dict[str, str]] = []
    for schedule in schedules:
        norm = validate_scorer_schedule_ids_fn(schedule, require_all_keys=True)
        resolved = dict(early=str(norm.early), middle=str(norm.middle), late=str(norm.late))
        validate_schedule_contract_fn(
            profile_id=str(profile_id),
            schedule=resolved,
        )
        validated_schedules.append(resolved)

    for fixture in fixtures:
        for period in sorted(int(k) for k in period_columns.keys()):
            columns = unique_sorted_ints_fn(tuple(int(x) for x in period_columns[period]))
            for column in columns:
                for run_seed in seeds:
                    for exp_profile in exp_profiles:
                        for schedule in validated_schedules:
                            jobs.append(
                                job_cls(
                                    fixture_id=str(fixture.fixture_id),
                                    period=int(period),
                                    columns=int(column),
                                    length=int(fixture.length),
                                    run_seed=int(run_seed),
                                    run_mode=str(run_mode),
                                    profile_id=str(profile_id),
                                    heartbeat_seconds=int(heartbeat_seconds),
                                    text_offsets=offsets,
                                    scorer_impl=str(scorer_impl),
                                    scorer_stage3_impl_avg_fulltext=str(
                                        scorer_stage3_impl_avg_fulltext
                                    ),
                                    scoring_experiment_profile=str(exp_profile),
                                    schedule_early=str(schedule["early"]),
                                    schedule_middle=str(schedule["middle"]),
                                    schedule_late=str(schedule["late"]),
                                )
                            )
    return jobs


def apply_job(
    *,
    job: Any,
    no_wli: Any,
    disable_stage3_span_basin_k_sweep: bool,
    stage3_span_basin_k_sweep_values: Sequence[int],
) -> None:
    if bool(disable_stage3_span_basin_k_sweep):
        no_wli.RUN_STAGE3_SPAN_BASIN_K_SWEEP = False
    else:
        no_wli.RUN_STAGE3_SPAN_BASIN_K_SWEEP = True
        no_wli.STAGE3_SPAN_BASIN_K_SWEEP_VALUES = [int(x) for x in stage3_span_basin_k_sweep_values]
        if no_wli.STAGE3_SPAN_BASIN_K_SWEEP_VALUES:
            no_wli.STAGE3_SPAN_BASIN_JUDGE_K = int(no_wli.STAGE3_SPAN_BASIN_K_SWEEP_VALUES[0])

    no_wli.configure_campaign_run(
        run_seed=int(job.run_seed),
        period=int(job.period),
        columns=int(job.columns),
        length=int(job.length),
        tier_name=str(job.tier_name()),
        run_mode=str(job.run_mode),
        profile_name=str(job.profile_id),
        heartbeat_seconds=int(job.heartbeat_seconds),
        autoskip_proven=False,
        force_rerun_proven=True,
        avoid_repeat_fail=False,
        text_offsets=[int(x) for x in job.text_offsets],
        tiers_regex_override=None,
        scorer_impl=str(job.scorer_impl),
        scorer_stage3_impl_avg_fulltext=str(job.scorer_stage3_impl_avg_fulltext),
        scorer_schedule=job.scorer_schedule(),
    )
    no_wli.SCORING_EXPERIMENT_PROFILE = str(job.scoring_experiment_profile)


def run_job(
    *,
    job: Any,
    apply_job_fn: Callable[..., None],
    main_fn: Callable[[], None],
) -> None:
    apply_job_fn(job=job)
    main_fn()
