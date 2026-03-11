from __future__ import annotations

from pathlib import Path

from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
)


CAMPAIGN_CONFIG_PATH = Path("tools/benchmarks/community/examples/campaign_config_v1_1.json")
FIXTURE_IDS: tuple[str, ...] | None = None
FIXTURE_LENGTH_OVERRIDE: int | None = 1000

USE_CAMPAIGN_GRID = False
PERIODS_OVERRIDE: tuple[int, ...] | None = (9,)
COLUMNS_OVERRIDE_BY_PERIOD: dict[int, tuple[int, ...]] = {
    9: (3,),
}

RUN_MODE = "adaptive_fixture_v1"
NO_WLI_PROFILE_ID = "no_wli_a1_m12_b34_stage3avg_fulltext_v1"
# 7-8h target campaign:
# - prioritize known near-solve seed first
# - keep a small seed sweep for robustness
RUN_SEEDS = (511, 211, 311, 411, 611)
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

# Solve-biased long run: focus all budget on strongest merged profile.
SCORING_EXPERIMENT_PROFILES = ("c_min_late",)
ENABLE_SPAN_AB_PAIR = False
SPAN_AB_DECISION_ROLE = "prune"

SCHEDULE_COVERAGE_MODE = "explicit"
EXPLICIT_SCHEDULES: tuple[dict[str, str], ...] = (
    dict(
        early=str(SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT),
        middle=str(SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT),
        late=str(SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT),
    ),
)
REQUIRE_NO_WIN10_OBJECTIVES = True
REQUIRE_FULL_TEXT_EFFECTIVE = True

DISABLE_STAGE3_SPAN_BASIN_K_SWEEP = False
STAGE3_SPAN_BASIN_K_SWEEP_VALUES: tuple[int, ...] = (96,)

# Force two-phase Stage-3 for fixture-matrix tuning runs.
FORCE_STAGE3_TWO_PHASE = True
FORCE_STAGE3_PHASEA_CFG: dict[str, int] = {
    "steps": 900,
    "restarts": 1,
    "inner_batch": 96,
    "col_every": 0,
    "col_batch": 0,
    "slip_every": 0,
    "slip_swaps": 0,
    "stall_slip_limit": 0,
}
FORCE_STAGE3_PHASEB_CFG: dict[str, int] = {
    "steps": 5600,
    "inner_batch": 128,
    "col_every": 1,
    "col_batch": 128,
    "slip_every": 70,
    "stall_rounds": 280,
    "stall_slip_limit": 8,
    "slip_swaps": 28,
}
FORCE_STAGE3_PHASEB_TOP_N = 24
FORCE_STAGE3_PHASEB_GATE_DELTA_FLOOR = 0.006
FORCE_STAGE3_PHASEB_GATE_END_GAIN_FLOOR = 0.003

# Optional Stage-3 preset matrix for long-running p9/c3 solve proving.
# Each preset keeps this exact setup but tweaks Phase-A/Phase-B budget/width.
ENABLE_STAGE3_TUNING_PRESET_MATRIX = True
STAGE3_TUNING_PRESET_IDS: tuple[str, ...] = (
    "lexical_tie_break_deep",
    "lexical_tie_break",
    "phaseb_deep",
)
STAGE3_TUNING_PRESETS: dict[str, dict[str, object]] = {
    "base": {},
    "phaseb_deep": {
        "force_stage3_phaseb_cfg": {
            "steps": 8400,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 420,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
    },
    "phaseb_wide": {
        "force_stage3_phaseb_top_n": 36,
        "force_stage3_phaseb_cfg": {
            "steps": 7000,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 360,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "stage3_span_basin_k_sweep_values": (128,),
    },
    "phasea_deep": {
        "force_stage3_phasea_cfg": {
            "steps": 1400,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        },
        "force_stage3_phaseb_cfg": {
            "steps": 7000,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 360,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_top_n": 28,
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
    },
    "lexical_tie_break": {
        "force_word_ngram_decision_influence": True,
        "force_stage12_promote_top": 128,
        "force_stage3_initial_keys": 96,
        "force_stage3_initial_keys_by_columns": {3: 96},
        "force_stage3_span_basin_judge_tie_max_seeds": 96,
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 7600,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 360,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "stage3_span_basin_k_sweep_values": (128,),
    },
    "lexical_tie_break_deep": {
        "force_word_ngram_decision_influence": True,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 128,
        "force_stage3_initial_keys_by_columns": {3: 128},
        "force_stage3_span_basin_judge_tie_max_seeds": 128,
        "force_stage3_phasea_cfg": {
            "steps": 1500,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        },
        "force_stage3_phaseb_top_n": 40,
        "force_stage3_phaseb_cfg": {
            "steps": 9800,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 480,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "stage3_span_basin_k_sweep_values": (128,),
    },
}
DRY_RUN_ONLY = False
STOP_ON_ERROR = True
# With 1 fixture x 1 period x 1 columns x 5 seeds x 3 presets x 1 schedule = 15 jobs.
MAX_JOBS: int | None = 15
# Hard cap to keep this run in the requested ~7-8 hour range.
MAX_WALLCLOCK_SECONDS: float | None = 7.5 * 3600.0

RUN_STATE_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v5_p9c3_8h_target.json"
)
RUN_EVENTS_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v5_p9c3_8h_target.jsonl"
)
RESUME_SKIP_COMPLETED = True

PLAN_OUTPUT_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v5_p9c3_8h_target.json"
)
WRITE_PLAN_JSON = True
