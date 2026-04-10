from __future__ import annotations

from pathlib import Path

from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_models import (
    MatrixControlFiles,
)


CAMPAIGN_CONFIG_PATH = Path("tools/benchmarks/community/examples/campaign_config_v1_1.json")
FIXTURE_IDS: tuple[str, ...] | None = None
FIXTURE_LENGTH_OVERRIDE: int | None = 1000
FIXED_INSTANCE_EXECUTION_PROFILE = "off"
DEFAULT_GENERATED_COMPARE_MODE = "candidate_single_p5"
_FIXED_INSTANCE_ACTIVE_PROFILES = {
    "canary",
    "panel_v1_long",
    "panel_v1_jobs04_05",
    "panel_v1_jobs06_10",
    "panel_v1_jobs11_20",
}
INSTANCE_INPUT_MODE = (
    "fixed_ciphertext"
    if FIXED_INSTANCE_EXECUTION_PROFILE in _FIXED_INSTANCE_ACTIVE_PROFILES
    else "generated"
)
if FIXED_INSTANCE_EXECUTION_PROFILE == "canary":
    FIXED_INSTANCE_PANEL_PATH = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_canary_v1.json"
    )
elif FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_jobs04_05":
    FIXED_INSTANCE_PANEL_PATH = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs04_05.json"
    )
elif FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_jobs06_10":
    FIXED_INSTANCE_PANEL_PATH = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs06_10.json"
    )
elif FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_jobs11_20":
    FIXED_INSTANCE_PANEL_PATH = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs11_20.json"
    )
else:
    FIXED_INSTANCE_PANEL_PATH = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json"
    )
FIXED_INSTANCE_FIXTURE_DIR = Path(
    "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances"
)

USE_CAMPAIGN_GRID = False
PERIODS_OVERRIDE: tuple[int, ...] | None = (9,)
COLUMNS_OVERRIDE_BY_PERIOD: dict[int, tuple[int, ...]] = {
    9: (3,),
}

RUN_MODE = "adaptive_fixture_v1"
NO_WLI_PROFILE_ID = "no_wli_a1_m12_b34_stage3avg_fulltext_v1"
# Fresh replay-capture follow-up:
# - the default lane still targets the `seed411` widened-late case that produced
#   the clearest late-stage disagreement frontier
# - the small frozen-ladder mode below deliberately widens this to a compact
#   p5/p9 control slice without changing Stage 3.5 semantics
RUN_SEEDS = (411,)
TEXT_OFFSETS = (0,)
HEARTBEAT_SECONDS = 180
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
FORCE_STAGE3_SPAN_BASIN_JUDGE_TIE_EPS = 0.001

# Optional Stage-3 preset matrix for targeted p9/c3 work.
# Current Stage 3.5 baseline-selector lane:
# - keep the widened-late `seed411` frontier shape that produced the replay-ready
#   disagreement and continuation win
# - turn Stage 3.5 on
# - vary only which already-explored Phase-C row becomes the Stage 3.5 baseline
# - do not change upstream search, Phase-C start policy, or Stage 3.5 search
#   semantics
ENABLE_STAGE3_TUNING_PRESET_MATRIX = True
STAGE35_BASELINE_SELECTOR_COMPARE_MODE = (
    "fixed_instance_canary"
    if FIXED_INSTANCE_EXECUTION_PROFILE == "canary"
    else "fixed_instance_panel_v1_jobs04_05"
    if FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_jobs04_05"
    else "fixed_instance_panel_v1_jobs06_10"
    if FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_jobs06_10"
    else "fixed_instance_panel_v1_jobs11_20"
    if FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_jobs11_20"
    else "fixed_instance_panel_v1_long"
    if FIXED_INSTANCE_EXECUTION_PROFILE == "panel_v1_long"
    else str(DEFAULT_GENERATED_COMPARE_MODE)
)
STAGE35_BASELINE_SELECTOR_CANARY_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_legacy_canary_p9",
    "stage35_baseline_score_plus_novelty_canary_p9",
)
STAGE35_BASELINE_SELECTOR_OVERNIGHT_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_legacy_live_p9",
    "stage35_baseline_score_plus_novelty_live_p9",
)
STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_score_plus_novelty_live_bounded_p9",
)
STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_CANARY_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_score_plus_novelty_canary_p9",
)
STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_LONG_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_score_plus_novelty_live_bounded_p9",
)
STAGE35_BASELINE_SELECTOR_SINGLE_LEGACY_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_legacy_live_bounded_p9",
)
STAGE35_BASELINE_SELECTOR_LADDER_PRESET_IDS: tuple[str, ...] = (
    "stage35_baseline_score_plus_novelty_live_bounded_p9",
)
if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "canary":
    STAGE3_TUNING_PRESET_IDS: tuple[str, ...] = (
        STAGE35_BASELINE_SELECTOR_CANARY_PRESET_IDS
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "overnight":
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_OVERNIGHT_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single":
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed611":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (611,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed711":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (711,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed811":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (811,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed911":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (911,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed1011":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (1011,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_pair_p9_seed1111_1211":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (1111, 1211)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_triple_p9_seed1311_1411_1511":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (1311, 1411, 1511)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed611_legacy":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (611,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_LEGACY_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p5":
    PERIODS_OVERRIDE = (5,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        5: (1,),
    }
    RUN_SEEDS = (511,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p7":
    PERIODS_OVERRIDE = (7,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        7: (1,),
    }
    RUN_SEEDS = (411,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_SINGLE_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_ladder_small":
    PERIODS_OVERRIDE = (5, 9)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        5: (1,),
        9: (1, 3),
    }
    RUN_SEEDS = (611, 711)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_LADDER_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_family_overnight":
    PERIODS_OVERRIDE = (7, 9)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        7: (1,),
        9: (3,),
    }
    RUN_SEEDS = (411, 611)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_LADDER_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_canary":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (611,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_CANARY_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs04_05":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (611,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_LONG_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs06_10":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (1111,)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_LONG_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs11_20":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (1411, 1511)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_LONG_PRESET_IDS
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_long":
    PERIODS_OVERRIDE = (9,)
    COLUMNS_OVERRIDE_BY_PERIOD = {
        9: (3,),
    }
    RUN_SEEDS = (611, 1111, 1411, 1511)
    STAGE3_TUNING_PRESET_IDS = STAGE35_BASELINE_SELECTOR_FIXED_INSTANCE_LONG_PRESET_IDS
else:
    raise ValueError(
        "unsupported STAGE35_BASELINE_SELECTOR_COMPARE_MODE; "
        "expected 'canary', 'overnight', 'candidate_single', "
        "'candidate_single_p9_seed611', 'candidate_single_p9_seed711', "
        "'candidate_single_p9_seed811', 'candidate_single_p9_seed911', "
        "'candidate_single_p9_seed1011', "
        "'candidate_pair_p9_seed1111_1211', "
        "'candidate_triple_p9_seed1311_1411_1511', "
        "'candidate_single_p9_seed611_legacy', "
        "'candidate_single_p5', "
        "'candidate_single_p7', 'candidate_ladder_small', "
        "'candidate_family_overnight', 'fixed_instance_canary', "
        "'fixed_instance_panel_v1_jobs04_05', "
        "'fixed_instance_panel_v1_jobs06_10', "
        "'fixed_instance_panel_v1_jobs11_20', or "
        "'fixed_instance_panel_v1_long'"
    )
STAGE35_BASELINE_SELECTOR_SHARED_CFG: dict[str, int] = {
    "seed_keep": 4,
    "beam_width": 4,
    "archive_keep": 16,
    "rounds": 3,
    "mini_search_steps": 2,
    "mini_search_beam_width": 3,
    "mini_search_top_symbols": 10,
    "mini_search_final_keep": 2,
    "mini_search_keep_all_rows": 1,
    "accept_score_min_gain": 0,
    "accept_search_score_max_drop": 0,
}
STAGE35_BASELINE_SELECTOR_BOUNDED_LIVE_CFG: dict[str, int | float] = {
    "seed_keep": 2,
    "beam_width": 1,
    "archive_keep": 12,
    "rounds": 1,
    "mini_search_steps": 1,
    "mini_search_beam_width": 2,
    "mini_search_top_symbols": 10,
    "mini_search_final_keep": 2,
    "mini_search_keep_all_rows": 0,
    "accept_score_min_gain": 0,
    "accept_search_score_max_drop": 0,
    "max_runtime_seconds": 14400.0,
    "partial_dump_preview_rows": 3,
}
STAGE35_BASELINE_SELECTOR_CANARY_CFG: dict[str, int] = {
    "seed_keep": 2,
    "beam_width": 2,
    "archive_keep": 6,
    "rounds": 1,
    "mini_search_steps": 1,
    "mini_search_beam_width": 2,
    "mini_search_top_symbols": 6,
    "mini_search_final_keep": 1,
    "mini_search_keep_all_rows": 0,
    "accept_score_min_gain": 0,
    "accept_search_score_max_drop": 0,
}
STAGE3_TUNING_PRESETS: dict[str, dict[str, object]] = {
    "stage3_recovery_p9_8h": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_max_seeds": 64,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage3_preserve_tieband_probe_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage3_phasec_start_balanced_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_start_policy": "balanced_sources_v1",
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage3_phaseb_family_preserve_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phaseb_family_preservation_policy": "reserve_by_family_v1",
        "force_stage3_phaseb_family_view_id": "prefix_hamming_le_24",
        "force_stage3_phaseb_family_reserved_slots": 2,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage3_phaseb_width_probe_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage3_phasec_novel_challenger_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_start_policy": "novel_challenger_v1",
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage3_entry_const_local_depth_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_init_keys_cap": 288,
        "force_stage3_entry_allocation_policy": "constant_local_depth",
        "force_stage3_entry_mutations_per_promoted": 1,
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": False,
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "base": {},
    "lexical_phasec_diagcheck": {
        "force_stage1_seed_restarts": 24,
        "force_stage1_seed_total": 96,
        "force_stage1_scout_min_steps": 300,
        "force_stage12_archive_keep": 64,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 32,
        "force_stage3_initial_keys": 24,
        "force_stage3_initial_keys_by_columns": {3: 24},
        "force_stage3_span_basin_judge_tie_max_seeds": 24,
        "force_stage3_phasea_cfg": {
            "steps": 120,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 3,
        "force_stage3_phaseb_cfg": {
            "steps": 240,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 80,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 1,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 4,
            "proposals_per_step": 4,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.70,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 8,
        },
        "stage3_span_basin_k_sweep_values": (24,),
    },
    "lexical_phasec_proof_single": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 96,
        "force_stage3_initial_keys": 80,
        "force_stage3_initial_keys_by_columns": {3: 80},
        "force_stage3_span_basin_judge_tie_max_seeds": 80,
        "force_stage3_phasea_cfg": {
            "steps": 900,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 16,
        "force_stage3_phaseb_cfg": {
            "steps": 2800,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 280,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 64,
            "proposals_per_step": 12,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.70,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 96,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 6,
            "rescue_slip_swaps": 5,
            "rescue_anchor_enabled": False,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 4,
            "rescue_search_score_max_drop": 0.35,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 10,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 96,
        },
        "stage3_span_basin_k_sweep_values": (80,),
    },
    "lexical_phasec_proof_wide": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 128,
        "force_stage3_initial_keys": 96,
        "force_stage3_initial_keys_by_columns": {3: 96},
        "force_stage3_span_basin_judge_tie_max_seeds": 96,
        "force_stage3_phasea_cfg": {
            "steps": 1000,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 24,
        "force_stage3_phaseb_cfg": {
            "steps": 3200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 112,
            "slip_every": 70,
            "stall_rounds": 320,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 5,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 72,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.68,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 8,
            "rescue_slip_swaps": 6,
            "rescue_anchor_enabled": False,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 4,
            "rescue_search_score_max_drop": 0.35,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 10,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 96,
        },
        "stage3_span_basin_k_sweep_values": (96,),
    },
    "lexical_phasec_proof_wide_deep": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 144,
        "force_stage3_initial_keys": 112,
        "force_stage3_initial_keys_by_columns": {3: 112},
        "force_stage3_span_basin_judge_tie_max_seeds": 112,
        "force_stage3_phasea_cfg": {
            "steps": 1100,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 24,
        "force_stage3_phaseb_cfg": {
            "steps": 4200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 112,
            "slip_every": 70,
            "stall_rounds": 360,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 12,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 20,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.68,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 160,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 10,
            "rescue_slip_swaps": 8,
            "rescue_anchor_enabled": False,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 4,
            "rescue_search_score_max_drop": 0.35,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 10,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 144,
        },
        "stage3_span_basin_k_sweep_values": (112,),
    },
    "lexical_phasec_rescue_wide_long": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 128,
        "force_stage3_initial_keys_by_columns": {3: 128},
        "force_stage3_span_basin_judge_tie_max_seeds": 128,
        "force_stage3_phasea_cfg": {
            "steps": 1000,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 3200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 112,
            "slip_every": 70,
            "stall_rounds": 320,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 16,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 20,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.68,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 160,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 10,
            "rescue_slip_swaps": 8,
            "rescue_anchor_enabled": False,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 4,
            "rescue_search_score_max_drop": 0.35,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 10,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 144,
        },
        "stage3_span_basin_k_sweep_values": (128,),
    },
    "lexical_phasec_rescue_wide_finish": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 128,
        "force_stage3_initial_keys_by_columns": {3: 128},
        "force_stage3_span_basin_judge_tie_max_seeds": 128,
        "force_stage3_phasea_cfg": {
            "steps": 1000,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 3200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 112,
            "slip_every": 70,
            "stall_rounds": 320,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 8,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 20,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.68,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 160,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 10,
            "rescue_slip_swaps": 8,
            "rescue_anchor_enabled": False,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 4,
            "rescue_search_score_max_drop": 0.35,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 10,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 144,
        },
        "stage3_span_basin_k_sweep_values": (128,),
    },
    "stage35_proof_p9_8h": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_max_seeds": 64,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": True,
        "force_stage35_cfg": {
            "seed_keep": 4,
            "beam_width": 4,
            "archive_keep": 16,
            "rounds": 3,
            "mini_search_steps": 2,
            "mini_search_beam_width": 3,
            "mini_search_top_symbols": 10,
            "mini_search_final_keep": 2,
            "mini_search_keep_all_rows": 1,
            "accept_score_min_gain": 0,
            "accept_search_score_max_drop": 0,
        },
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage35_baseline_legacy_canary_p9": {
        "force_stage1_seed_restarts": 44,
        "force_stage1_seed_total": 112,
        "force_stage1_scout_min_steps": 425,
        "force_stage12_archive_keep": 96,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 96,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 200,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 16,
        "force_stage3_phaseb_cfg": {
            "steps": 400,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 80,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 4,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 24,
            "proposals_per_step": 8,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 48,
        },
        "force_stage35_enabled": True,
        "force_stage35_baseline_selector": "legacy",
        "force_stage35_cfg": dict(STAGE35_BASELINE_SELECTOR_CANARY_CFG),
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage35_baseline_score_plus_novelty_canary_p9": {
        "force_stage1_seed_restarts": 44,
        "force_stage1_seed_total": 112,
        "force_stage1_scout_min_steps": 425,
        "force_stage12_archive_keep": 96,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 96,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 200,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 16,
        "force_stage3_phaseb_cfg": {
            "steps": 400,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 80,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 4,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 24,
            "proposals_per_step": 8,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 48,
        },
        "force_stage35_enabled": True,
        "force_stage35_baseline_selector": "score_plus_novelty",
        "force_stage35_cfg": dict(STAGE35_BASELINE_SELECTOR_CANARY_CFG),
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage35_baseline_legacy_live_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": True,
        "force_stage35_baseline_selector": "legacy",
        "force_stage35_cfg": dict(STAGE35_BASELINE_SELECTOR_SHARED_CFG),
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage35_baseline_score_plus_novelty_live_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": True,
        "force_stage35_baseline_selector": "score_plus_novelty",
        "force_stage35_cfg": dict(STAGE35_BASELINE_SELECTOR_SHARED_CFG),
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage35_baseline_score_plus_novelty_live_bounded_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": True,
        "force_stage35_baseline_selector": "score_plus_novelty",
        "force_stage35_cfg": dict(STAGE35_BASELINE_SELECTOR_BOUNDED_LIVE_CFG),
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "stage35_baseline_legacy_live_bounded_p9": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 64,
        "force_stage3_initial_keys_by_columns": {3: 64},
        "force_stage3_span_basin_judge_tie_eps": 0.005,
        "force_stage3_span_basin_judge_tie_max_seeds": 16,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
            "progress_pct": 1,
            "print_progress": False,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 2200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 96,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
            "progress_pct": 1,
            "print_progress": True,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 6,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 96,
            "proposals_per_step": 16,
            "three_cycle_prob": 0.2,
            "lexical_min_match": 0.72,
            "lexical_match_tie_eps": 0.01,
            "lexical_score_tie_eps": 0.002,
            "lexical_max_calls": 128,
        },
        "force_stage35_enabled": True,
        "force_stage35_baseline_selector": "legacy",
        "force_stage35_cfg": dict(STAGE35_BASELINE_SELECTOR_BOUNDED_LIVE_CFG),
        "stage3_span_basin_k_sweep_values": (64,),
    },
    "lexical_tie_break_short": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 96,
        "force_stage3_initial_keys": 80,
        "force_stage3_initial_keys_by_columns": {3: 80},
        "force_stage3_span_basin_judge_tie_max_seeds": 96,
        "force_stage3_phasea_cfg": {
            "steps": 900,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        },
        "force_stage3_phaseb_top_n": 24,
        "force_stage3_phaseb_cfg": {
            "steps": 5200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 112,
            "slip_every": 70,
            "stall_rounds": 260,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 16,
        "force_stage3_phasec_cfg": {
            "steps": 48,
            "proposals_per_step": 24,
            "three_cycle_prob": 0.15,
        },
        "stage3_span_basin_k_sweep_values": (96,),
    },
    "phaseb_deep_short": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 96,
        "force_stage3_initial_keys": 80,
        "force_stage3_initial_keys_by_columns": {3: 80},
        "force_stage3_span_basin_judge_tie_max_seeds": 96,
        "force_stage3_phasea_cfg": {
            "steps": 800,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        },
        "force_stage3_phaseb_top_n": 28,
        "force_stage3_phaseb_cfg": {
            "steps": 6200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 112,
            "slip_every": 70,
            "stall_rounds": 320,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.004,
        "force_stage3_phaseb_gate_end_gain_floor": 0.002,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 20,
        "force_stage3_phasec_cfg": {
            "steps": 64,
            "proposals_per_step": 28,
            "three_cycle_prob": 0.15,
        },
        "stage3_span_basin_k_sweep_values": (96,),
    },
    "lexical_phasec_push": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 128,
        "force_stage3_initial_keys": 96,
        "force_stage3_initial_keys_by_columns": {3: 96},
        "force_stage3_span_basin_judge_tie_max_seeds": 128,
        "force_stage3_phasea_cfg": {
            "steps": 1000,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        },
        "force_stage3_phaseb_top_n": 32,
        "force_stage3_phaseb_cfg": {
            "steps": 7200,
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
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 24,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 80,
            "proposals_per_step": 32,
            "three_cycle_prob": 0.2,
        },
        "stage3_span_basin_k_sweep_values": (96,),
    },
    "lexical_phasec_push_deep": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 160,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 128,
        "force_stage3_initial_keys_by_columns": {3: 128},
        "force_stage3_span_basin_judge_tie_max_seeds": 128,
        "force_stage3_phasea_cfg": {
            "steps": 1200,
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
            "steps": 9000,
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
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 32,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 128,
            "proposals_per_step": 36,
            "three_cycle_prob": 0.2,
        },
        "stage3_span_basin_k_sweep_values": (128,),
    },
    "lexical_phasec_extreme": {
        "force_stage1_seed_restarts": 88,
        "force_stage1_seed_total": 224,
        "force_stage1_scout_min_steps": 850,
        "force_stage12_archive_keep": 192,
        "force_word_ngram_decision_influence": True,
        "force_word_ngram_report_min_positions": 6,
        "force_stage12_promote_top": 160,
        "force_stage3_initial_keys": 144,
        "force_stage3_initial_keys_by_columns": {3: 144},
        "force_stage3_span_basin_judge_tie_max_seeds": 160,
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
        "force_stage3_phaseb_top_n": 48,
        "force_stage3_phaseb_cfg": {
            "steps": 12000,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 560,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        },
        "force_stage3_phaseb_gate_delta_floor": 0.003,
        "force_stage3_phaseb_gate_end_gain_floor": 0.001,
        "force_stage3_phasec_enabled": True,
        "force_stage3_phasec_start_keys": 48,
        "force_stage3_phasec_word_ngram_tiebreak": True,
        "force_stage3_phasec_cfg": {
            "steps": 192,
            "proposals_per_step": 40,
            "three_cycle_prob": 0.2,
        },
        "stage3_span_basin_k_sweep_values": (128,),
    },
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
STOP_ON_ERROR = False
# `MAX_JOBS` is a total-job truncation, not just a parallelism control.
if STAGE35_BASELINE_SELECTOR_COMPARE_MODE in {
    "candidate_single",
    "candidate_single_p9_seed611",
    "candidate_single_p9_seed711",
    "candidate_single_p9_seed811",
    "candidate_single_p9_seed911",
    "candidate_single_p9_seed1011",
    "candidate_pair_p9_seed1111_1211",
    "candidate_triple_p9_seed1311_1411_1511",
    "candidate_single_p9_seed611_legacy",
    "candidate_single_p5",
    "candidate_single_p7",
    "fixed_instance_canary",
    "fixed_instance_panel_v1_jobs04_05",
    "fixed_instance_panel_v1_jobs06_10",
    "fixed_instance_panel_v1_jobs11_20",
    "fixed_instance_panel_v1_long",
}:
    MAX_JOBS: int | None = (
        20
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_long"
        else 10
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs11_20"
        else 5
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs06_10"
        else 2
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs04_05"
        else
        3
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE
        == "candidate_triple_p9_seed1311_1411_1511"
        else
        2
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE
        == "candidate_pair_p9_seed1111_1211"
        else 1
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_ladder_small":
    MAX_JOBS = 6
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_family_overnight":
    MAX_JOBS = 4
else:
    # With 1 fixture x 1 period x 1 columns x 1 seed x 2 presets x 1 schedule = 2 jobs.
    MAX_JOBS = 2
if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "canary":
    MAX_WALLCLOCK_SECONDS: float | None = 2.0 * 60.0 * 60.0
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE in {
    "candidate_single",
    "candidate_single_p9_seed611",
    "candidate_single_p9_seed711",
    "candidate_single_p9_seed811",
    "candidate_single_p9_seed911",
    "candidate_single_p9_seed1011",
    "candidate_pair_p9_seed1111_1211",
    "candidate_triple_p9_seed1311_1411_1511",
    "candidate_single_p9_seed611_legacy",
    "candidate_single_p5",
    "candidate_single_p7",
    "fixed_instance_canary",
    "fixed_instance_panel_v1_jobs04_05",
    "fixed_instance_panel_v1_jobs06_10",
    "fixed_instance_panel_v1_jobs11_20",
    "fixed_instance_panel_v1_long",
}:
    MAX_WALLCLOCK_SECONDS = (
        24.0 * 60.0 * 60.0
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_long"
        else 72.0 * 60.0 * 60.0
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs11_20"
        else 48.0 * 60.0 * 60.0
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs06_10"
        else 18.0 * 60.0 * 60.0
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs04_05"
        else
        2.0 * 60.0 * 60.0
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_canary"
        else
        12.0 * 60.0 * 60.0
        if STAGE35_BASELINE_SELECTOR_COMPARE_MODE
        == "candidate_triple_p9_seed1311_1411_1511"
        else 8.0 * 60.0 * 60.0
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_ladder_small":
    MAX_WALLCLOCK_SECONDS = 8.0 * 60.0 * 60.0
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_family_overnight":
    MAX_WALLCLOCK_SECONDS = 12.0 * 60.0 * 60.0
else:
    MAX_WALLCLOCK_SECONDS = 8.0 * 60.0 * 60.0

CONTROL_FILES_BASE_DIR = Path("output/tools/benchmarks/periodic_sub_trans/no_wli")
if STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "canary":
    EXPERIMENT_RUN_ID = "tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job"
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single":
    EXPERIMENT_RUN_ID = (
        "tune_v57_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed611":
    EXPERIMENT_RUN_ID = (
        "tune_v62_p9c3_seed611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed711":
    EXPERIMENT_RUN_ID = (
        "tune_v64_p9c3_seed711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed811":
    EXPERIMENT_RUN_ID = (
        "tune_v65_p9c3_seed811_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed911":
    EXPERIMENT_RUN_ID = (
        "tune_v66_p9c3_seed911_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed1011":
    EXPERIMENT_RUN_ID = (
        "tune_v67_p9c3_seed1011_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_pair_p9_seed1111_1211":
    EXPERIMENT_RUN_ID = (
        "tune_v68_p9c3_seed1111_1211_stage35_baseline_selector_candidate_live_bounded_space_map_v1_2job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_triple_p9_seed1311_1411_1511":
    EXPERIMENT_RUN_ID = (
        "tune_v69_p9c3_seed1311_1411_1511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_3job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p9_seed611_legacy":
    EXPERIMENT_RUN_ID = (
        "tune_v63_p9c3_seed611_stage35_baseline_selector_legacy_control_live_bounded_space_map_v1_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p5":
    EXPERIMENT_RUN_ID = (
        "tune_v60_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_shadow_stop_v2_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_single_p7":
    EXPERIMENT_RUN_ID = (
        "tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_ladder_small":
    EXPERIMENT_RUN_ID = (
        "tune_v59_ladder_small_seed611_711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_6job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "candidate_family_overnight":
    EXPERIMENT_RUN_ID = (
        "tune_v61_family_overnight_p7c1_p9c3_seed411_611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_4job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_canary":
    EXPERIMENT_RUN_ID = (
        "tune_v70_fixed_p9c3_fixture611_search7001_stage35_baseline_selector_score_plus_novelty_canary_1job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs04_05":
    EXPERIMENT_RUN_ID = (
        "tune_v72a_fixed_p9c3_jobs04_05_fixture611_search7004_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_2job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs06_10":
    EXPERIMENT_RUN_ID = (
        "tune_v72b_fixed_p9c3_jobs06_10_fixture1111_search7001_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_5job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_jobs11_20":
    EXPERIMENT_RUN_ID = (
        "tune_v73_fixed_p9c3_jobs11_20_fixture1411_1511_search7001_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_10job"
    )
elif STAGE35_BASELINE_SELECTOR_COMPARE_MODE == "fixed_instance_panel_v1_long":
    EXPERIMENT_RUN_ID = (
        "tune_v71_fixed_p9c3_panelv1_search7001_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_20job"
    )
else:
    EXPERIMENT_RUN_ID = (
        "tune_v48_p9c3_seed411_stage35_baseline_selector_live_compare_2job"
    )
MATRIX_CONTROL_FILES = MatrixControlFiles.for_experiment(
    experiment_run_id=EXPERIMENT_RUN_ID,
    base_dir=CONTROL_FILES_BASE_DIR,
)
RUN_STATE_PATH = MATRIX_CONTROL_FILES.run_state_path
RUN_EVENTS_PATH = MATRIX_CONTROL_FILES.run_events_path
RESUME_SKIP_COMPLETED = True

PLAN_OUTPUT_PATH = MATRIX_CONTROL_FILES.plan_output_path
WRITE_PLAN_JSON = True

