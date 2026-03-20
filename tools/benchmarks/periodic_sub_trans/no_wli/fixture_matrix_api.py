from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from tools.benchmarks.community._campaign_common import load_json
from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCORER_SCHEDULE_ID_CATALOG,
    SCHEDULE_EARLY_A_CHAR1,
    SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
    SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT,
    SCHEDULE_EARLY_DEFAULT,
    SCHEDULE_LATE_B_CHAR34,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_LATE_DEFAULT,
    SCHEDULE_MIDDLE_M_CHAR12,
    SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_DEFAULT,
    validate_scorer_schedule_ids,
)
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule_apply import (
    apply_no_wli_schedule,
)
from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_config import (
    DISABLE_STAGE3_SPAN_BASIN_K_SWEEP,
    ENABLE_STAGE3_TUNING_PRESET_MATRIX,
    FORCE_STAGE3_PHASEA_CFG,
    FORCE_STAGE3_PHASEB_CFG,
    FORCE_STAGE3_PHASEB_GATE_DELTA_FLOOR,
    FORCE_STAGE3_PHASEB_GATE_END_GAIN_FLOOR,
    FORCE_STAGE3_PHASEB_TOP_N,
    FORCE_STAGE3_TWO_PHASE,
    REQUIRE_FULL_TEXT_EFFECTIVE,
    REQUIRE_NO_WIN10_OBJECTIVES,
    STAGE3_TUNING_PRESET_IDS,
    STAGE3_TUNING_PRESETS,
    STAGE3_SPAN_BASIN_K_SWEEP_VALUES,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_inputs import (
    fixture_length_from_metadata as _fixture_length_from_metadata_impl,
    load_fixture_specs as _load_fixture_specs_impl,
    resolve_period_columns as _resolve_period_columns_impl,
    unique_sorted_ints as _unique_sorted_ints_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_jobs import (
    apply_job as _apply_job_impl,
    build_fixture_jobs as _build_fixture_jobs_impl,
    job_key as _job_key_impl,
    run_job as _run_job_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_models import (
    FixtureSpec,
    NoWliFixtureJob,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_plan import (
    resolve_path as _resolve_path_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_runtime import (
    load_run_state as _load_run_state_runtime,
    utc_now_iso as _utc_now_iso_runtime,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_schedule import (
    build_schedule_matrix as _build_schedule_matrix_impl,
    resolve_stage_objectives_for_schedule as _resolve_stage_objectives_for_schedule_impl,
    validate_schedule_contract as _validate_schedule_contract_impl,
)


def _utc_now_iso() -> str:
    return _utc_now_iso_runtime()


def _job_key(job: NoWliFixtureJob) -> str:
    return _job_key_impl(job)


def _load_run_state(path: Path) -> dict[str, Any]:
    return _load_run_state_runtime(path=path, load_json_fn=load_json)


def _unique_sorted_ints(values: Iterable[int]) -> tuple[int, ...]:
    return _unique_sorted_ints_impl(values)


def _fixture_length_from_metadata(
    *,
    fixture_row: Mapping[str, Any],
    repo_root: Path,
) -> int:
    return _fixture_length_from_metadata_impl(
        fixture_row=fixture_row,
        repo_root=repo_root,
        load_json_fn=load_json,
    )


def load_fixture_specs(
    *,
    campaign_config: Mapping[str, Any],
    repo_root: Path,
    fixture_ids: Sequence[str] | None = None,
    fixture_length_override: int | None = None,
) -> list[FixtureSpec]:
    return _load_fixture_specs_impl(
        campaign_config=campaign_config,
        repo_root=repo_root,
        fixture_ids=fixture_ids,
        fixture_length_override=fixture_length_override,
        fixture_spec_cls=FixtureSpec,
        fixture_length_from_metadata_fn=_fixture_length_from_metadata,
    )


def resolve_period_columns(
    *,
    campaign_config: Mapping[str, Any],
    use_campaign_grid: bool,
    periods_override: Sequence[int] | None,
    columns_override_by_period: Mapping[int, Sequence[int]] | None,
) -> dict[int, tuple[int, ...]]:
    return _resolve_period_columns_impl(
        campaign_config=campaign_config,
        use_campaign_grid=use_campaign_grid,
        periods_override=periods_override,
        columns_override_by_period=columns_override_by_period,
        unique_sorted_ints_fn=_unique_sorted_ints,
    )


def build_schedule_matrix(
    *,
    mode: str,
    explicit_schedules: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, str]]:
    return _build_schedule_matrix_impl(
        mode=mode,
        explicit_schedules=explicit_schedules,
        scorer_schedule_id_catalog=SCORER_SCHEDULE_ID_CATALOG,
        schedule_early_a_char1=str(SCHEDULE_EARLY_A_CHAR1),
        schedule_middle_m_char12=str(SCHEDULE_MIDDLE_M_CHAR12),
        schedule_late_b_char34=str(SCHEDULE_LATE_B_CHAR34),
        schedule_early_default=str(SCHEDULE_EARLY_DEFAULT),
        schedule_early_a_char1_avg_fulltext=str(SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT),
        schedule_early_a_char2_avg_fulltext=str(SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT),
        schedule_middle_default=str(SCHEDULE_MIDDLE_DEFAULT),
        schedule_middle_m_char12_avg_fulltext=str(SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT),
        schedule_middle_m_char4_avg_fulltext=str(SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT),
        schedule_late_default=str(SCHEDULE_LATE_DEFAULT),
        schedule_late_b_char4_avg_fulltext=str(SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT),
        validate_scorer_schedule_ids_fn=validate_scorer_schedule_ids,
    )


def resolve_stage_objectives_for_schedule(
    *,
    profile_id: str,
    schedule: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    return _resolve_stage_objectives_for_schedule_impl(
        profile_id=profile_id,
        schedule=schedule,
        get_profile_fn=get_no_wli_pipeline_profile,
        apply_no_wli_schedule_fn=apply_no_wli_schedule,
    )


def validate_schedule_contract(
    *,
    profile_id: str,
    schedule: Mapping[str, str],
) -> None:
    _validate_schedule_contract_impl(
        profile_id=profile_id,
        schedule=schedule,
        resolve_stage_objectives_for_schedule_fn=resolve_stage_objectives_for_schedule,
        require_no_win10_objectives=bool(REQUIRE_NO_WIN10_OBJECTIVES),
        require_full_text_effective=bool(REQUIRE_FULL_TEXT_EFFECTIVE),
    )


def build_fixture_jobs(
    *,
    fixtures: Sequence[FixtureSpec],
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
    enable_span_ab_pair: bool = False,
    span_ab_decision_role: str = "prune",
) -> list[NoWliFixtureJob]:
    return _build_fixture_jobs_impl(
        fixtures=fixtures,
        period_columns=period_columns,
        run_seeds=run_seeds,
        run_mode=run_mode,
        profile_id=profile_id,
        heartbeat_seconds=heartbeat_seconds,
        text_offsets=text_offsets,
        scorer_impl=scorer_impl,
        scorer_stage3_impl_avg_fulltext=scorer_stage3_impl_avg_fulltext,
        scoring_experiment_profiles=scoring_experiment_profiles,
        stage3_tuning_preset_ids=stage3_tuning_preset_ids,
        schedules=schedules,
        enable_span_ab_pair=bool(enable_span_ab_pair),
        span_ab_decision_role=str(span_ab_decision_role),
        unique_sorted_ints_fn=lambda xs: _unique_sorted_ints(tuple(int(x) for x in xs)),
        validate_scorer_schedule_ids_fn=validate_scorer_schedule_ids,
        validate_schedule_contract_fn=validate_schedule_contract,
        job_cls=NoWliFixtureJob,
    )


def resolve_stage3_tuning_preset_ids() -> tuple[str, ...]:
    if not bool(ENABLE_STAGE3_TUNING_PRESET_MATRIX):
        return ("base",)
    out: list[str] = []
    seen: set[str] = set()
    for raw in STAGE3_TUNING_PRESET_IDS:
        preset_id = str(raw).strip().lower()
        if not preset_id or preset_id in seen:
            continue
        seen.add(preset_id)
        out.append(preset_id)
    if not out:
        return ("base",)
    return tuple(out)


def _resolve_stage3_tuning_overrides_for_job(
    job: NoWliFixtureJob,
) -> dict[str, Any]:
    preset_id = str(getattr(job, "stage3_tuning_preset_id", "base")).strip().lower()
    raw_presets = (
        STAGE3_TUNING_PRESETS if isinstance(STAGE3_TUNING_PRESETS, Mapping) else {}
    )
    raw_preset = raw_presets.get(preset_id, {})
    preset = raw_preset if isinstance(raw_preset, Mapping) else {}

    span_basin_values = tuple(int(x) for x in STAGE3_SPAN_BASIN_K_SWEEP_VALUES)
    if "stage3_span_basin_k_sweep_values" in preset:
        try:
            parsed = tuple(int(x) for x in list(preset["stage3_span_basin_k_sweep_values"]))
            if parsed:
                span_basin_values = parsed
        except Exception:
            pass

    phasea_cfg = dict(FORCE_STAGE3_PHASEA_CFG)
    raw_phasea_cfg = preset.get("force_stage3_phasea_cfg")
    if isinstance(raw_phasea_cfg, Mapping):
        phasea_cfg.update({str(k): int(v) for k, v in raw_phasea_cfg.items()})

    phaseb_cfg = dict(FORCE_STAGE3_PHASEB_CFG)
    raw_phaseb_cfg = preset.get("force_stage3_phaseb_cfg")
    if isinstance(raw_phaseb_cfg, Mapping):
        phaseb_cfg.update({str(k): int(v) for k, v in raw_phaseb_cfg.items()})

    force_word_ngram_decision_influence = preset.get(
        "force_word_ngram_decision_influence", None
    )
    if force_word_ngram_decision_influence is not None:
        force_word_ngram_decision_influence = bool(force_word_ngram_decision_influence)
    force_word_ngram_report_min_positions = preset.get(
        "force_word_ngram_report_min_positions", None
    )
    if force_word_ngram_report_min_positions is not None:
        force_word_ngram_report_min_positions = int(
            force_word_ngram_report_min_positions
        )

    force_stage3_initial_keys = preset.get("force_stage3_initial_keys", None)
    if force_stage3_initial_keys is not None:
        force_stage3_initial_keys = int(force_stage3_initial_keys)

    force_stage3_initial_keys_by_columns: dict[int, int] | None = None
    raw_init_by_columns = preset.get("force_stage3_initial_keys_by_columns", None)
    if isinstance(raw_init_by_columns, Mapping):
        force_stage3_initial_keys_by_columns = {
            int(k): int(v) for k, v in raw_init_by_columns.items()
        }

    force_stage12_promote_top = preset.get("force_stage12_promote_top", None)
    if force_stage12_promote_top is not None:
        force_stage12_promote_top = int(force_stage12_promote_top)

    force_stage3_span_basin_judge_tie_max_seeds = preset.get(
        "force_stage3_span_basin_judge_tie_max_seeds", None
    )
    if force_stage3_span_basin_judge_tie_max_seeds is not None:
        force_stage3_span_basin_judge_tie_max_seeds = int(
            force_stage3_span_basin_judge_tie_max_seeds
        )
    force_stage1_seed_restarts = preset.get("force_stage1_seed_restarts", None)
    if force_stage1_seed_restarts is not None:
        force_stage1_seed_restarts = int(force_stage1_seed_restarts)
    force_stage1_seed_total = preset.get("force_stage1_seed_total", None)
    if force_stage1_seed_total is not None:
        force_stage1_seed_total = int(force_stage1_seed_total)
    force_stage1_scout_min_steps = preset.get("force_stage1_scout_min_steps", None)
    if force_stage1_scout_min_steps is not None:
        force_stage1_scout_min_steps = int(force_stage1_scout_min_steps)
    force_stage12_archive_keep = preset.get("force_stage12_archive_keep", None)
    if force_stage12_archive_keep is not None:
        force_stage12_archive_keep = int(force_stage12_archive_keep)
    force_stage3_phasec_enabled = preset.get("force_stage3_phasec_enabled", None)
    if force_stage3_phasec_enabled is not None:
        force_stage3_phasec_enabled = bool(force_stage3_phasec_enabled)
    force_stage3_phasec_start_keys = preset.get("force_stage3_phasec_start_keys", None)
    if force_stage3_phasec_start_keys is not None:
        force_stage3_phasec_start_keys = int(force_stage3_phasec_start_keys)
    force_stage3_phasec_seed_offset = preset.get("force_stage3_phasec_seed_offset", None)
    if force_stage3_phasec_seed_offset is not None:
        force_stage3_phasec_seed_offset = int(force_stage3_phasec_seed_offset)
    force_stage3_phasec_word_ngram_tiebreak = preset.get(
        "force_stage3_phasec_word_ngram_tiebreak",
        None,
    )
    if force_stage3_phasec_word_ngram_tiebreak is not None:
        force_stage3_phasec_word_ngram_tiebreak = bool(
            force_stage3_phasec_word_ngram_tiebreak
        )
    force_stage3_phasec_cfg: dict[str, Any] | None = None
    raw_phasec_cfg = preset.get("force_stage3_phasec_cfg", None)
    if isinstance(raw_phasec_cfg, Mapping):
        force_stage3_phasec_cfg = dict(raw_phasec_cfg)

    return dict(
        disable_stage3_span_basin_k_sweep=bool(DISABLE_STAGE3_SPAN_BASIN_K_SWEEP),
        stage3_span_basin_k_sweep_values=span_basin_values,
        force_stage3_two_phase=bool(
            preset.get("force_stage3_two_phase", FORCE_STAGE3_TWO_PHASE)
        ),
        force_stage3_phasea_cfg=phasea_cfg,
        force_stage3_phaseb_cfg=phaseb_cfg,
        force_stage3_phaseb_top_n=int(
            preset.get("force_stage3_phaseb_top_n", FORCE_STAGE3_PHASEB_TOP_N)
        ),
        force_stage3_phaseb_gate_delta_floor=float(
            preset.get(
                "force_stage3_phaseb_gate_delta_floor",
                FORCE_STAGE3_PHASEB_GATE_DELTA_FLOOR,
            )
        ),
        force_stage3_phaseb_gate_end_gain_floor=float(
            preset.get(
                "force_stage3_phaseb_gate_end_gain_floor",
                FORCE_STAGE3_PHASEB_GATE_END_GAIN_FLOOR,
            )
        ),
        force_word_ngram_decision_influence=force_word_ngram_decision_influence,
        force_word_ngram_report_min_positions=force_word_ngram_report_min_positions,
        force_stage3_initial_keys=force_stage3_initial_keys,
        force_stage3_initial_keys_by_columns=force_stage3_initial_keys_by_columns,
        force_stage12_promote_top=force_stage12_promote_top,
        force_stage3_span_basin_judge_tie_max_seeds=(
            force_stage3_span_basin_judge_tie_max_seeds
        ),
        force_stage3_phasec_enabled=force_stage3_phasec_enabled,
        force_stage3_phasec_cfg=force_stage3_phasec_cfg,
        force_stage3_phasec_start_keys=force_stage3_phasec_start_keys,
        force_stage3_phasec_seed_offset=force_stage3_phasec_seed_offset,
        force_stage3_phasec_word_ngram_tiebreak=force_stage3_phasec_word_ngram_tiebreak,
        force_stage1_seed_restarts=force_stage1_seed_restarts,
        force_stage1_seed_total=force_stage1_seed_total,
        force_stage1_scout_min_steps=force_stage1_scout_min_steps,
        force_stage12_archive_keep=force_stage12_archive_keep,
    )


def apply_job(job: NoWliFixtureJob) -> None:
    stage3_tuning_overrides = _resolve_stage3_tuning_overrides_for_job(job)
    _apply_job_impl(
        job=job,
        no_wli=no_wli,
        disable_stage3_span_basin_k_sweep=bool(
            stage3_tuning_overrides["disable_stage3_span_basin_k_sweep"]
        ),
        stage3_span_basin_k_sweep_values=tuple(
            int(x) for x in stage3_tuning_overrides["stage3_span_basin_k_sweep_values"]
        ),
        force_stage3_two_phase=bool(stage3_tuning_overrides["force_stage3_two_phase"]),
        force_stage3_phasea_cfg=dict(stage3_tuning_overrides["force_stage3_phasea_cfg"]),
        force_stage3_phaseb_cfg=dict(stage3_tuning_overrides["force_stage3_phaseb_cfg"]),
        force_stage3_phaseb_top_n=int(stage3_tuning_overrides["force_stage3_phaseb_top_n"]),
        force_stage3_phaseb_gate_delta_floor=float(
            stage3_tuning_overrides["force_stage3_phaseb_gate_delta_floor"]
        ),
        force_stage3_phaseb_gate_end_gain_floor=float(
            stage3_tuning_overrides["force_stage3_phaseb_gate_end_gain_floor"]
        ),
        force_word_ngram_decision_influence=stage3_tuning_overrides[
            "force_word_ngram_decision_influence"
        ],
        force_word_ngram_report_min_positions=stage3_tuning_overrides[
            "force_word_ngram_report_min_positions"
        ],
        force_stage3_initial_keys=stage3_tuning_overrides["force_stage3_initial_keys"],
        force_stage3_initial_keys_by_columns=stage3_tuning_overrides[
            "force_stage3_initial_keys_by_columns"
        ],
        force_stage12_promote_top=stage3_tuning_overrides["force_stage12_promote_top"],
        force_stage3_span_basin_judge_tie_max_seeds=stage3_tuning_overrides[
            "force_stage3_span_basin_judge_tie_max_seeds"
        ],
        force_stage3_phasec_enabled=stage3_tuning_overrides[
            "force_stage3_phasec_enabled"
        ],
        force_stage3_phasec_cfg=stage3_tuning_overrides["force_stage3_phasec_cfg"],
        force_stage3_phasec_start_keys=stage3_tuning_overrides[
            "force_stage3_phasec_start_keys"
        ],
        force_stage3_phasec_seed_offset=stage3_tuning_overrides[
            "force_stage3_phasec_seed_offset"
        ],
        force_stage3_phasec_word_ngram_tiebreak=stage3_tuning_overrides[
            "force_stage3_phasec_word_ngram_tiebreak"
        ],
        force_stage1_seed_restarts=stage3_tuning_overrides[
            "force_stage1_seed_restarts"
        ],
        force_stage1_seed_total=stage3_tuning_overrides["force_stage1_seed_total"],
        force_stage1_scout_min_steps=stage3_tuning_overrides[
            "force_stage1_scout_min_steps"
        ],
        force_stage12_archive_keep=stage3_tuning_overrides[
            "force_stage12_archive_keep"
        ],
    )


def run_job(job: NoWliFixtureJob) -> None:
    _run_job_impl(
        job=job,
        apply_job_fn=apply_job,
        main_fn=no_wli.main,
    )


def _resolve_path(*, path_like: Path, repo_root: Path) -> Path:
    return _resolve_path_impl(path_like=Path(path_like), repo_root=repo_root)
