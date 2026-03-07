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
    REQUIRE_FULL_TEXT_EFFECTIVE,
    REQUIRE_NO_WIN10_OBJECTIVES,
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
        schedules=schedules,
        unique_sorted_ints_fn=lambda xs: _unique_sorted_ints(tuple(int(x) for x in xs)),
        validate_scorer_schedule_ids_fn=validate_scorer_schedule_ids,
        validate_schedule_contract_fn=validate_schedule_contract,
        job_cls=NoWliFixtureJob,
    )


def apply_job(job: NoWliFixtureJob) -> None:
    _apply_job_impl(
        job=job,
        no_wli=no_wli,
        disable_stage3_span_basin_k_sweep=bool(DISABLE_STAGE3_SPAN_BASIN_K_SWEEP),
        stage3_span_basin_k_sweep_values=STAGE3_SPAN_BASIN_K_SWEEP_VALUES,
    )


def run_job(job: NoWliFixtureJob) -> None:
    _run_job_impl(
        job=job,
        apply_job_fn=apply_job,
        main_fn=no_wli.main,
    )


def _resolve_path(*, path_like: Path, repo_root: Path) -> Path:
    return _resolve_path_impl(path_like=Path(path_like), repo_root=repo_root)
