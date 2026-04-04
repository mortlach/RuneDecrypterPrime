from __future__ import annotations

"""Internal no-WLI fixture-matrix launcher.

Purpose:
- Reuse community fixture definitions/grid metadata.
- Keep no_wli outside public community manifest/order contracts.
- Sweep adaptive staged no-WLI runs with configurable scorer schedules
  and scoring experiment profiles (default: no span-hamming).

Usage:
- Edit hardcoded knobs below.
- Run: `python tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
"""

from pathlib import Path
import sys
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.benchmarks.community._campaign_common import load_json, write_json
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_plan import (
    build_plan_payload as _build_plan_payload_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_mainflow import (
    run_mainflow as _run_mainflow_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_runtime import (
    run_jobs_with_checkpoints,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_preflight import (
    run_runtime_preflight,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_api import (
    _job_key,
    _load_run_state,
    _resolve_path,
    _utc_now_iso,
    build_fixture_jobs,
    build_schedule_matrix,
    load_fixture_specs,
    resolve_stage3_tuning_preset_ids,
    resolve_stage3_tuning_presets,
    resolve_period_columns,
    resolve_stage_objectives_for_schedule,
    run_job,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_models import (
    FixtureSpec,
    FixtureMatrixMainflowConfig,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_config import (
    CAMPAIGN_CONFIG_PATH,
    FIXTURE_IDS,
    FIXTURE_LENGTH_OVERRIDE,
    USE_CAMPAIGN_GRID,
    PERIODS_OVERRIDE,
    COLUMNS_OVERRIDE_BY_PERIOD,
    RUN_MODE,
    NO_WLI_PROFILE_ID,
    RUN_SEEDS,
    TEXT_OFFSETS,
    HEARTBEAT_SECONDS,
    SCORER_IMPL,
    SCORER_STAGE3_IMPL_AVG_FULLTEXT,
    ENABLE_ACCEPTANCE_HARNESS_500X5,
    ACCEPTANCE_HARNESS_FIXTURE_COUNT,
    ACCEPTANCE_HARNESS_LENGTH,
    SCORING_EXPERIMENT_PROFILES,
    ENABLE_SPAN_AB_PAIR,
    SPAN_AB_DECISION_ROLE,
    SCHEDULE_COVERAGE_MODE,
    EXPLICIT_SCHEDULES,
    REQUIRE_NO_WIN10_OBJECTIVES,
    REQUIRE_FULL_TEXT_EFFECTIVE,
    DISABLE_STAGE3_SPAN_BASIN_K_SWEEP,
    STAGE3_SPAN_BASIN_K_SWEEP_VALUES,
    ENABLE_STAGE3_TUNING_PRESET_MATRIX,
    STAGE3_TUNING_PRESET_IDS as _STAGE3_TUNING_PRESET_IDS_RAW,
    DRY_RUN_ONLY,
    STOP_ON_ERROR,
    MAX_JOBS,
    MAX_WALLCLOCK_SECONDS,
    MATRIX_CONTROL_FILES,
    RUN_STATE_PATH,
    RUN_EVENTS_PATH,
    RESUME_SKIP_COMPLETED,
    PLAN_OUTPUT_PATH,
    WRITE_PLAN_JSON,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_schedule import (
    validate_schedule_contract as _validate_schedule_contract_impl,
)


def validate_schedule_contract(*, profile_id: str, schedule: dict[str, str]) -> None:
    _validate_schedule_contract_impl(
        profile_id=profile_id,
        schedule=schedule,
        resolve_stage_objectives_for_schedule_fn=resolve_stage_objectives_for_schedule,
        require_no_win10_objectives=bool(REQUIRE_NO_WIN10_OBJECTIVES),
        require_full_text_effective=bool(REQUIRE_FULL_TEXT_EFFECTIVE),
    )


# Keep the resolved preset IDs as a stable top-level constant for mainflow state.
STAGE3_TUNING_PRESET_IDS = resolve_stage3_tuning_preset_ids()
if not STAGE3_TUNING_PRESET_IDS:
    STAGE3_TUNING_PRESET_IDS = tuple(
        str(x).strip().lower() for x in _STAGE3_TUNING_PRESET_IDS_RAW if str(x).strip()
    )

def build_matrix_mainflow_config() -> FixtureMatrixMainflowConfig:
    return FixtureMatrixMainflowConfig(
        campaign_config_path=Path(CAMPAIGN_CONFIG_PATH),
        fixture_ids=(
            None
            if FIXTURE_IDS is None
            else tuple(str(x) for x in FIXTURE_IDS)
        ),
        fixture_length_override=(
            None
            if FIXTURE_LENGTH_OVERRIDE is None
            else int(FIXTURE_LENGTH_OVERRIDE)
        ),
        use_campaign_grid=bool(USE_CAMPAIGN_GRID),
        periods_override=(
            None
            if PERIODS_OVERRIDE is None
            else tuple(int(x) for x in PERIODS_OVERRIDE)
        ),
        columns_override_by_period={
            int(k): tuple(int(x) for x in v)
            for k, v in dict(COLUMNS_OVERRIDE_BY_PERIOD).items()
        },
        run_mode=str(RUN_MODE),
        no_wli_profile_id=str(NO_WLI_PROFILE_ID),
        run_seeds=tuple(int(x) for x in RUN_SEEDS),
        text_offsets=tuple(int(x) for x in TEXT_OFFSETS),
        heartbeat_seconds=int(HEARTBEAT_SECONDS),
        scorer_impl=str(SCORER_IMPL),
        scorer_stage3_impl_avg_fulltext=str(SCORER_STAGE3_IMPL_AVG_FULLTEXT),
        enable_acceptance_harness_500x5=bool(ENABLE_ACCEPTANCE_HARNESS_500X5),
        acceptance_harness_fixture_count=int(ACCEPTANCE_HARNESS_FIXTURE_COUNT),
        acceptance_harness_length=int(ACCEPTANCE_HARNESS_LENGTH),
        scoring_experiment_profiles=tuple(
            str(x) for x in SCORING_EXPERIMENT_PROFILES
        ),
        enable_span_ab_pair=bool(ENABLE_SPAN_AB_PAIR),
        span_ab_decision_role=str(SPAN_AB_DECISION_ROLE),
        schedule_coverage_mode=str(SCHEDULE_COVERAGE_MODE),
        explicit_schedules=tuple(
            {
                "early": str(schedule["early"]),
                "middle": str(schedule["middle"]),
                "late": str(schedule["late"]),
            }
            for schedule in EXPLICIT_SCHEDULES
        ),
        require_no_win10_objectives=bool(REQUIRE_NO_WIN10_OBJECTIVES),
        require_full_text_effective=bool(REQUIRE_FULL_TEXT_EFFECTIVE),
        disable_stage3_span_basin_k_sweep=bool(DISABLE_STAGE3_SPAN_BASIN_K_SWEEP),
        stage3_span_basin_k_sweep_values=tuple(
            int(x) for x in STAGE3_SPAN_BASIN_K_SWEEP_VALUES
        ),
        stage3_tuning_preset_ids=tuple(str(x) for x in STAGE3_TUNING_PRESET_IDS),
        stage3_tuning_presets=dict(resolve_stage3_tuning_presets()),
        dry_run_only=bool(DRY_RUN_ONLY),
        stop_on_error=bool(STOP_ON_ERROR),
        max_jobs=(None if MAX_JOBS is None else int(MAX_JOBS)),
        max_wallclock_seconds=(
            None
            if MAX_WALLCLOCK_SECONDS is None
            else float(MAX_WALLCLOCK_SECONDS)
        ),
        resume_skip_completed=bool(RESUME_SKIP_COMPLETED),
        control_files=MATRIX_CONTROL_FILES,
        write_plan_json=bool(WRITE_PLAN_JSON),
    )


def build_matrix_mainflow_state() -> dict[str, Any]:
    return build_matrix_mainflow_config().to_state(utc_now_iso_fn=_utc_now_iso)


def main() -> None:
    _run_mainflow_impl(
        state=build_matrix_mainflow_state(),
        repo_root=_ROOT,
        resolve_path_fn=lambda p: _resolve_path(path_like=p, repo_root=_ROOT),
        load_json_fn=load_json,
        write_json_fn=write_json,
        load_fixture_specs_fn=load_fixture_specs,
        resolve_period_columns_fn=resolve_period_columns,
        build_schedule_matrix_fn=build_schedule_matrix,
        build_fixture_jobs_fn=build_fixture_jobs,
        build_plan_payload_fn=_build_plan_payload_impl,
        run_jobs_with_checkpoints_fn=run_jobs_with_checkpoints,
        load_run_state_fn=_load_run_state,
        job_key_fn=_job_key,
        run_job_fn=run_job,
        runtime_preflight_fn=run_runtime_preflight,
        print_fn=print,
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
