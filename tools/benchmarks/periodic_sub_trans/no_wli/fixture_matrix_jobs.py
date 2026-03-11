from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def _sync_stage3_two_phase_defaults_from_live_state(*, no_wli: Any) -> None:
    """Keep profile-reset defaults aligned with current live Stage-3 two-phase config.

    The stage3-span-basin-k sweep wrapper reapplies profile defaults before each
    sweep run. Without syncing these shadow defaults, fixture-matrix forced
    two-phase settings are reverted back to runner hardcoded defaults.
    """
    if hasattr(no_wli, "_STAGE3_TWO_PHASE_ENABLED_DEFAULT"):
        no_wli._STAGE3_TWO_PHASE_ENABLED_DEFAULT = bool(  # type: ignore[attr-defined]
            no_wli.STAGE3_TWO_PHASE_ENABLED
        )
    if hasattr(no_wli, "_STAGE3_PHASEA_CFG_DEFAULT"):
        no_wli._STAGE3_PHASEA_CFG_DEFAULT = {  # type: ignore[attr-defined]
            str(k): int(v) for k, v in dict(no_wli.STAGE3_PHASEA_CFG).items()
        }
    if hasattr(no_wli, "_STAGE3_PHASEB_CFG_DEFAULT"):
        no_wli._STAGE3_PHASEB_CFG_DEFAULT = {  # type: ignore[attr-defined]
            str(k): int(v) for k, v in dict(no_wli.STAGE3_PHASEB_CFG).items()
        }
    if hasattr(no_wli, "_STAGE3_PHASEB_TOP_N_DEFAULT"):
        no_wli._STAGE3_PHASEB_TOP_N_DEFAULT = int(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEB_TOP_N
        )
    if hasattr(no_wli, "_STAGE3_PHASEB_GATE_DELTA_FLOOR_DEFAULT"):
        no_wli._STAGE3_PHASEB_GATE_DELTA_FLOOR_DEFAULT = float(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEB_GATE_DELTA_FLOOR
        )
    if hasattr(no_wli, "_STAGE3_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT"):
        no_wli._STAGE3_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT = float(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEB_GATE_END_GAIN_FLOOR
        )


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
            str(getattr(job, "span_ab_case_id", "none")),
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
    enable_span_ab_pair: bool,
    span_ab_decision_role: str,
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

    span_ab_role = str(span_ab_decision_role).strip().lower()
    if span_ab_role not in {"prune", "gate", "combined", "judge"}:
        span_ab_role = "prune"

    def _append_job(*, base_kwargs: dict[str, Any]) -> None:
        if not bool(enable_span_ab_pair):
            jobs.append(
                job_cls(
                    **base_kwargs,
                    span_ab_case_id="none",
                    span_decision_role_enabled=False,
                )
            )
            return
        jobs.append(
            job_cls(
                **base_kwargs,
                span_ab_case_id="span_shadow",
                span_decision_role_enabled=False,
            )
        )
        jobs.append(
            job_cls(
                **base_kwargs,
                span_ab_case_id=f"span_{span_ab_role}",
                span_decision_role_enabled=True,
            )
        )

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
        # Preserve caller-specified period order (for example p13-first campaigns).
        for period in tuple(int(k) for k in period_columns.keys()):
            columns = unique_sorted_ints_fn(tuple(int(x) for x in period_columns[period]))
            for column in columns:
                for run_seed in seeds:
                    for exp_profile in exp_profiles:
                        for schedule in validated_schedules:
                            _append_job(
                                base_kwargs=dict(
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
    force_stage3_two_phase: bool = False,
    force_stage3_phasea_cfg: Mapping[str, Any] | None = None,
    force_stage3_phaseb_cfg: Mapping[str, Any] | None = None,
    force_stage3_phaseb_top_n: int | None = None,
    force_stage3_phaseb_gate_delta_floor: float | None = None,
    force_stage3_phaseb_gate_end_gain_floor: float | None = None,
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
    if bool(force_stage3_two_phase):
        no_wli.STAGE3_TWO_PHASE_ENABLED = True
        if force_stage3_phasea_cfg is not None:
            no_wli.STAGE3_PHASEA_CFG = {
                str(k): int(v) for k, v in dict(force_stage3_phasea_cfg).items()
            }
        if force_stage3_phaseb_cfg is not None:
            no_wli.STAGE3_PHASEB_CFG = {
                str(k): int(v) for k, v in dict(force_stage3_phaseb_cfg).items()
            }
        if force_stage3_phaseb_top_n is not None:
            no_wli.STAGE3_PHASEB_TOP_N = int(force_stage3_phaseb_top_n)
        if force_stage3_phaseb_gate_delta_floor is not None:
            no_wli.STAGE3_PHASEB_GATE_DELTA_FLOOR = float(
                force_stage3_phaseb_gate_delta_floor
            )
        if force_stage3_phaseb_gate_end_gain_floor is not None:
            no_wli.STAGE3_PHASEB_GATE_END_GAIN_FLOOR = float(
                force_stage3_phaseb_gate_end_gain_floor
            )
    _sync_stage3_two_phase_defaults_from_live_state(no_wli=no_wli)
    no_wli.SPAN_DECISION_ROLE_ENABLED = bool(
        getattr(job, "span_decision_role_enabled", False)
    )
    span_case_id = str(getattr(job, "span_ab_case_id", "none")).strip().lower()
    if span_case_id in {"span_shadow", "shadow"}:
        no_wli.STAGE3_SPAN_AUX_ROLE = "shadow"
    elif span_case_id.startswith("span_"):
        no_wli.STAGE3_SPAN_AUX_ROLE = span_case_id.split("span_", 1)[1] or "off"
    else:
        no_wli.STAGE3_SPAN_AUX_ROLE = "off"


def run_job(
    *,
    job: Any,
    apply_job_fn: Callable[..., None],
    main_fn: Callable[[], None],
) -> None:
    apply_job_fn(job=job)
    main_fn()
