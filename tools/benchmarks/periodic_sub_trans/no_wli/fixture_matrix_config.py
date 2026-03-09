from __future__ import annotations

from pathlib import Path

from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT,
)


CAMPAIGN_CONFIG_PATH = Path("tools/benchmarks/community/examples/campaign_config_v1_1.json")
FIXTURE_IDS: tuple[str, ...] | None = None
FIXTURE_LENGTH_OVERRIDE: int | None = 1000

USE_CAMPAIGN_GRID = False
PERIODS_OVERRIDE: tuple[int, ...] | None = (9, 11, 13)
COLUMNS_OVERRIDE_BY_PERIOD: dict[int, tuple[int, ...]] = {
    9: (1, 3, 5, 7),
    11: (1, 3, 5, 7, 9),
    13: (1, 3, 5, 7, 9),
}

RUN_MODE = "adaptive_fixture_v1"
NO_WLI_PROFILE_ID = "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
RUN_SEEDS = (111,)
TEXT_OFFSETS = (0,)
HEARTBEAT_SECONDS = 3600
SCORER_IMPL = "torch"
SCORER_STAGE3_IMPL_AVG_FULLTEXT = "torch"

# Acceptance-harness preset for Phase-3 target:
# - first N real fixtures from campaign config
# - fixed fixture length override
ENABLE_ACCEPTANCE_HARNESS_500X5 = False
ACCEPTANCE_HARNESS_FIXTURE_COUNT = 5
ACCEPTANCE_HARNESS_LENGTH = 500

SCORING_EXPERIMENT_PROFILES = ("c_min_late",)
ENABLE_SPAN_AB_PAIR = False
SPAN_AB_DECISION_ROLE = "prune"

SCHEDULE_COVERAGE_MODE = "explicit"
EXPLICIT_SCHEDULES: tuple[dict[str, str], ...] = (
    dict(
        early=str(SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT),
        middle=str(SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT),
        late=str(SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT),
    ),
)
REQUIRE_NO_WIN10_OBJECTIVES = True
REQUIRE_FULL_TEXT_EFFECTIVE = True

DISABLE_STAGE3_SPAN_BASIN_K_SWEEP = False
STAGE3_SPAN_BASIN_K_SWEEP_VALUES: tuple[int, ...] = (96,)
DRY_RUN_ONLY = False
STOP_ON_ERROR = True
MAX_JOBS: int | None = None
# Target roughly one-day campaign budget; runner checkpoints allow resume.
MAX_WALLCLOCK_SECONDS: float | None = 20.0 * 3600.0

RUN_STATE_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_latest.json"
)
RUN_EVENTS_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_latest.jsonl"
)
RESUME_SKIP_COMPLETED = True

PLAN_OUTPUT_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_latest.json"
)
WRITE_PLAN_JSON = True
