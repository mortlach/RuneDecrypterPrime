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
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_api import (
    _job_key,
    _load_run_state,
    _resolve_path,
    _utc_now_iso,
    build_fixture_jobs,
    build_schedule_matrix,
    load_fixture_specs,
    resolve_period_columns,
    resolve_stage_objectives_for_schedule,
    run_job,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_models import (
    FixtureSpec,
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
    DRY_RUN_ONLY,
    STOP_ON_ERROR,
    MAX_JOBS,
    MAX_WALLCLOCK_SECONDS,
    RUN_STATE_PATH,
    RUN_EVENTS_PATH,
    RESUME_SKIP_COMPLETED,
    PLAN_OUTPUT_PATH,
    WRITE_PLAN_JSON,
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


def main() -> None:
    _run_mainflow_impl(
        state=globals(),
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
        print_fn=print,
    )


if __name__ == "__main__":
    main()
