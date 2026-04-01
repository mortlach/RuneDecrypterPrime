from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def _normalize_stage35_cfg(cfg: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in dict(cfg).items():
        key = str(k)
        if key in {"accept_score_min_gain", "accept_search_score_max_drop"}:
            out[key] = float(v)
        else:
            out[key] = int(v)
    return out


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
    if hasattr(no_wli, "_STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY_DEFAULT"):
        no_wli._STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY_DEFAULT = str(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY
        )
    if hasattr(no_wli, "_STAGE3_PHASEB_FAMILY_VIEW_ID_DEFAULT"):
        no_wli._STAGE3_PHASEB_FAMILY_VIEW_ID_DEFAULT = str(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEB_FAMILY_VIEW_ID
        )
    if hasattr(no_wli, "_STAGE3_PHASEB_FAMILY_RESERVED_SLOTS_DEFAULT"):
        no_wli._STAGE3_PHASEB_FAMILY_RESERVED_SLOTS_DEFAULT = int(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEB_FAMILY_RESERVED_SLOTS
        )
    if hasattr(no_wli, "_STAGE3_PHASEC_ENABLED_DEFAULT"):
        no_wli._STAGE3_PHASEC_ENABLED_DEFAULT = bool(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEC_ENABLED
        )
    if hasattr(no_wli, "_STAGE3_PHASEC_CFG_DEFAULT"):
        no_wli._STAGE3_PHASEC_CFG_DEFAULT = {  # type: ignore[attr-defined]
            str(k): v for k, v in dict(no_wli.STAGE3_PHASEC_CFG).items()
        }
    if hasattr(no_wli, "_STAGE3_PHASEC_START_KEYS_DEFAULT"):
        no_wli._STAGE3_PHASEC_START_KEYS_DEFAULT = int(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEC_START_KEYS
        )
    if hasattr(no_wli, "_STAGE3_PHASEC_SEED_OFFSET_DEFAULT"):
        no_wli._STAGE3_PHASEC_SEED_OFFSET_DEFAULT = int(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEC_SEED_OFFSET
        )
    if hasattr(no_wli, "_STAGE3_PHASEC_WORD_NGRAM_TIEBREAK_DEFAULT"):
        no_wli._STAGE3_PHASEC_WORD_NGRAM_TIEBREAK_DEFAULT = bool(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEC_WORD_NGRAM_TIEBREAK
        )
    if hasattr(no_wli, "_STAGE3_PHASEC_START_POLICY_DEFAULT"):
        no_wli._STAGE3_PHASEC_START_POLICY_DEFAULT = str(  # type: ignore[attr-defined]
            no_wli.STAGE3_PHASEC_START_POLICY
        )
    if hasattr(no_wli, "_STAGE35_ENABLED_DEFAULT"):
        no_wli._STAGE35_ENABLED_DEFAULT = bool(  # type: ignore[attr-defined]
            no_wli.STAGE35_ENABLED
        )
    if hasattr(no_wli, "_STAGE35_BASELINE_SELECTOR_DEFAULT"):
        no_wli._STAGE35_BASELINE_SELECTOR_DEFAULT = str(  # type: ignore[attr-defined]
            no_wli.STAGE35_BASELINE_SELECTOR
        )
    if hasattr(no_wli, "_STAGE35_CFG_DEFAULT"):
        no_wli._STAGE35_CFG_DEFAULT = {  # type: ignore[attr-defined]
            str(k): v for k, v in _normalize_stage35_cfg(dict(no_wli.STAGE35_CFG)).items()
        }
    if hasattr(no_wli, "_STAGE3_ENTRY_ALLOCATION_POLICY_DEFAULT"):
        no_wli._STAGE3_ENTRY_ALLOCATION_POLICY_DEFAULT = str(  # type: ignore[attr-defined]
            no_wli.STAGE3_ENTRY_ALLOCATION_POLICY
        )
    if hasattr(no_wli, "_STAGE3_ENTRY_MUTATIONS_PER_PROMOTED_DEFAULT"):
        no_wli._STAGE3_ENTRY_MUTATIONS_PER_PROMOTED_DEFAULT = int(  # type: ignore[attr-defined]
            no_wli.STAGE3_ENTRY_MUTATIONS_PER_PROMOTED
        )
    if hasattr(no_wli, "_STAGE3_SPAN_BASIN_JUDGE_TIE_EPS_DEFAULT"):
        no_wli._STAGE3_SPAN_BASIN_JUDGE_TIE_EPS_DEFAULT = float(  # type: ignore[attr-defined]
            no_wli.STAGE3_SPAN_BASIN_JUDGE_TIE_EPS
        )
    if hasattr(no_wli, "_STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS_DEFAULT"):
        no_wli._STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS_DEFAULT = int(  # type: ignore[attr-defined]
            no_wli.STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS
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
            str(getattr(job, "stage3_tuning_preset_id", "base")),
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
    stage3_tuning_preset_ids: Sequence[str] = ("base",),
    enable_span_ab_pair: bool,
    span_ab_decision_role: str,
    unique_sorted_ints_fn: Callable[[Sequence[int]], tuple[int, ...]],
    validate_scorer_schedule_ids_fn: Callable[..., Any],
    validate_schedule_contract_fn: Callable[..., None],
    job_cls: type,
) -> list[Any]:
    # Preserve caller-provided seed order so campaigns can prioritize known hot seeds.
    seeds: list[int] = []
    seen_seed: set[int] = set()
    for raw_seed in run_seeds:
        seed_i = int(raw_seed)
        if seed_i in seen_seed:
            continue
        seen_seed.add(seed_i)
        seeds.append(seed_i)
    if not seeds:
        raise ValueError("RUN_SEEDS resolved empty")

    exp_profiles = [
        str(x).strip().lower() for x in scoring_experiment_profiles if str(x).strip()
    ]
    if not exp_profiles:
        raise ValueError("SCORING_EXPERIMENT_PROFILES resolved empty")
    tuning_preset_ids: list[str] = []
    seen_tuning_preset_ids: set[str] = set()
    for raw_id in stage3_tuning_preset_ids:
        preset_id = str(raw_id).strip().lower()
        if not preset_id or preset_id in seen_tuning_preset_ids:
            continue
        seen_tuning_preset_ids.add(preset_id)
        tuning_preset_ids.append(preset_id)
    if not tuning_preset_ids:
        tuning_preset_ids = ["base"]

    offsets = tuple(int(x) for x in text_offsets)
    if not offsets:
        raise ValueError("TEXT_OFFSETS resolved empty")

    span_ab_role = str(span_ab_decision_role).strip().lower()
    if span_ab_role not in {"prune", "gate", "combined", "judge"}:
        span_ab_role = "prune"

    def _append_job(*, base_kwargs: dict[str, Any], stage3_tuning_preset_id: str) -> None:
        if not bool(enable_span_ab_pair):
            jobs.append(
                job_cls(
                    **base_kwargs,
                    stage3_tuning_preset_id=str(stage3_tuning_preset_id),
                    span_ab_case_id="none",
                    span_decision_role_enabled=False,
                )
            )
            return
        jobs.append(
            job_cls(
                **base_kwargs,
                stage3_tuning_preset_id=str(stage3_tuning_preset_id),
                span_ab_case_id="span_shadow",
                span_decision_role_enabled=False,
            )
        )
        jobs.append(
            job_cls(
                **base_kwargs,
                stage3_tuning_preset_id=str(stage3_tuning_preset_id),
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
                        for tuning_preset_id in tuning_preset_ids:
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
                                    ),
                                    stage3_tuning_preset_id=str(tuning_preset_id),
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
    force_stage3_phaseb_family_preservation_policy: str | None = None,
    force_stage3_phaseb_family_view_id: str | None = None,
    force_stage3_phaseb_family_reserved_slots: int | None = None,
    force_stage3_phasec_enabled: bool | None = None,
    force_stage3_phasec_cfg: Mapping[str, Any] | None = None,
    force_stage3_phasec_start_keys: int | None = None,
    force_stage3_phasec_seed_offset: int | None = None,
    force_stage3_phasec_word_ngram_tiebreak: bool | None = None,
    force_stage3_phasec_start_policy: str | None = None,
    force_stage35_enabled: bool | None = None,
    force_stage35_baseline_selector: str | None = None,
    force_stage35_cfg: Mapping[str, Any] | None = None,
    force_stage1_seed_restarts: int | None = None,
    force_stage1_seed_total: int | None = None,
    force_stage1_scout_min_steps: int | None = None,
    force_stage12_archive_keep: int | None = None,
    force_word_ngram_decision_influence: bool | None = None,
    force_stage3_initial_keys: int | None = None,
    force_stage3_initial_keys_by_columns: Mapping[str, Any] | None = None,
    force_stage3_init_keys_cap: int | None = None,
    force_stage3_entry_allocation_policy: str | None = None,
    force_stage3_entry_mutations_per_promoted: int | None = None,
    force_solver_stage3_overrides: Mapping[str, Any] | None = None,
    force_stage12_promote_top: int | None = None,
    force_stage3_span_basin_judge_tie_eps: float | None = None,
    force_stage3_span_basin_judge_tie_max_seeds: int | None = None,
    force_word_ngram_report_min_positions: int | None = None,
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
    if force_stage3_phasec_enabled is not None:
        no_wli.STAGE3_PHASEC_ENABLED = bool(force_stage3_phasec_enabled)
    if force_stage3_phaseb_family_preservation_policy is not None:
        no_wli.STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY = str(
            force_stage3_phaseb_family_preservation_policy
        ).strip().lower()
    if force_stage3_phaseb_family_view_id is not None:
        no_wli.STAGE3_PHASEB_FAMILY_VIEW_ID = str(
            force_stage3_phaseb_family_view_id
        ).strip().lower()
    if force_stage3_phaseb_family_reserved_slots is not None:
        no_wli.STAGE3_PHASEB_FAMILY_RESERVED_SLOTS = int(
            max(0, int(force_stage3_phaseb_family_reserved_slots))
        )
    if force_stage3_phasec_cfg is not None:
        no_wli.STAGE3_PHASEC_CFG = dict(force_stage3_phasec_cfg)
    if force_stage3_phasec_start_keys is not None:
        no_wli.STAGE3_PHASEC_START_KEYS = int(max(1, int(force_stage3_phasec_start_keys)))
    if force_stage3_phasec_seed_offset is not None:
        no_wli.STAGE3_PHASEC_SEED_OFFSET = int(force_stage3_phasec_seed_offset)
    if force_stage3_phasec_word_ngram_tiebreak is not None:
        no_wli.STAGE3_PHASEC_WORD_NGRAM_TIEBREAK = bool(
            force_stage3_phasec_word_ngram_tiebreak
        )
    if force_stage3_phasec_start_policy is not None:
        no_wli.STAGE3_PHASEC_START_POLICY = str(
            force_stage3_phasec_start_policy
        ).strip().lower()
    if force_stage35_enabled is not None:
        no_wli.STAGE35_ENABLED = bool(force_stage35_enabled)
    if force_stage35_baseline_selector is not None:
        no_wli.STAGE35_BASELINE_SELECTOR = str(
            force_stage35_baseline_selector
        ).strip().lower()
    if force_stage35_cfg is not None:
        no_wli.STAGE35_CFG = _normalize_stage35_cfg(dict(force_stage35_cfg))
    if force_stage1_seed_restarts is not None:
        no_wli.STAGE1_SEED_RESTARTS = int(max(1, int(force_stage1_seed_restarts)))
    if force_stage1_seed_total is not None:
        no_wli.STAGE1_SEED_TOTAL = int(max(1, int(force_stage1_seed_total)))
    if force_stage1_scout_min_steps is not None:
        no_wli.STAGE1_SCOUT_MIN_STEPS = int(max(1, int(force_stage1_scout_min_steps)))
    if force_stage12_archive_keep is not None:
        no_wli.STAGE12_ARCHIVE_KEEP = int(max(1, int(force_stage12_archive_keep)))
    if force_word_ngram_decision_influence is not None:
        no_wli.WORD_NGRAM_REPORT_DECISION_INFLUENCE = bool(
            force_word_ngram_decision_influence
        )
    if force_word_ngram_report_min_positions is not None:
        no_wli.WORD_NGRAM_REPORT_MIN_POSITIONS = int(
            max(1, int(force_word_ngram_report_min_positions))
        )
    if force_stage3_initial_keys is not None:
        no_wli.STAGE3_INITIAL_KEYS = int(max(1, int(force_stage3_initial_keys)))
    if force_stage3_initial_keys_by_columns is not None:
        merged_init_by_columns = {
            int(k): int(v)
            for k, v in dict(no_wli.STAGE3_INITIAL_KEYS_BY_COLUMNS).items()
        }
        for k, v in dict(force_stage3_initial_keys_by_columns).items():
            merged_init_by_columns[int(k)] = int(max(1, int(v)))
        no_wli.STAGE3_INITIAL_KEYS_BY_COLUMNS = merged_init_by_columns
    if force_stage3_init_keys_cap is not None:
        no_wli.STAGE3_INIT_KEYS_CAP = int(max(0, int(force_stage3_init_keys_cap)))
    if force_stage3_entry_allocation_policy is not None:
        no_wli.STAGE3_ENTRY_ALLOCATION_POLICY = str(
            force_stage3_entry_allocation_policy
        ).strip().lower()
    if force_stage3_entry_mutations_per_promoted is not None:
        no_wli.STAGE3_ENTRY_MUTATIONS_PER_PROMOTED = int(
            max(1, int(force_stage3_entry_mutations_per_promoted))
        )
    if force_solver_stage3_overrides is not None:
        merged_solver_stage3 = {
            str(k): v for k, v in dict(no_wli.SOLVER_STAGE3).items()
        }
        for k, v in dict(force_solver_stage3_overrides).items():
            key = str(k)
            if key == "entry_allocation_policy":
                no_wli.STAGE3_ENTRY_ALLOCATION_POLICY = str(v).strip().lower()
                continue
            if key == "entry_mutations_per_promoted":
                no_wli.STAGE3_ENTRY_MUTATIONS_PER_PROMOTED = int(max(1, int(v)))
                continue
            merged_solver_stage3[key] = v
        no_wli.SOLVER_STAGE3 = merged_solver_stage3
    if force_stage12_promote_top is not None:
        no_wli.STAGE12_PROMOTE_TOP = int(max(1, int(force_stage12_promote_top)))
    if force_stage3_span_basin_judge_tie_eps is not None:
        no_wli.STAGE3_SPAN_BASIN_JUDGE_TIE_EPS = float(
            max(0.0, float(force_stage3_span_basin_judge_tie_eps))
        )
    if force_stage3_span_basin_judge_tie_max_seeds is not None:
        no_wli.STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS = int(
            max(1, int(force_stage3_span_basin_judge_tie_max_seeds))
        )
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
